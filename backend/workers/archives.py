from __future__ import annotations

import os
import posixpath
import tempfile
import zipfile
from inspect import isawaitable
from pathlib import PurePosixPath
from typing import Any
from uuid import UUID

from database.exceptions import DatabaseConnectionError
from database.models.enums import NodeType, StorageObjectStatus
from services.exceptions import ServiceError
from storage.exceptions import StorageConnectionError, StorageError
from workers.exceptions import WorkerTaskHandlerError
from workers.tasks import (
    failure_result,
    optional_payload_value,
    retry_result,
    success_result,
)
from workers.types import WorkerTaskExecutionContext, WorkerTaskExecutionResult


async def create_folder_archive_handler(
    context: WorkerTaskExecutionContext,
) -> WorkerTaskExecutionResult:
    """РЎРѕР·РґР°С‘С‚ ZIP-Р°СЂС…РёРІ РїР°РїРєРё РІ С„РѕРЅРѕРІРѕРј СЂРµР¶РёРјРµ."""

    temp_zip_path: str | None = None
    folder_node_snapshot: dict[str, Any] | None = None
    file_nodes_by_id: dict[UUID, dict[str, Any]] = {}
    file_rows: list[dict[str, Any]] = []
    task_meta: dict[str, Any] | None = None
    try:
        payload = context.payload
        async with context.uow_factory() as uow:
            task_row = await uow.tasks.get_required_by_id(context.task_id)
            task_meta = {
                "id": getattr(task_row, "id", None),
                "related_entity_id": getattr(task_row, "related_entity_id", None),
                "created_by": getattr(task_row, "created_by", None),
            }

        folder_node_id = _resolve_folder_node_id(payload, task_meta=task_meta)
        requested_by = _resolve_requested_by(payload, task_meta=task_meta)
        archive_name = optional_payload_value(
            payload,
            "archive_name",
            expected_type=str,
            default=None,
        )

        ready_result = await _try_service_archive(
            context, folder_node_id, requested_by, archive_name
        )
        if ready_result is not None:
            return ready_result

        async with context.uow_factory() as uow:
            folder_node = await uow.nodes.get_required_by_id(folder_node_id)
            descendants = await uow.nodes.get_descendants(
                node_id=folder_node_id,
                include_self=False,
                include_deleted=False,
            )
            file_nodes = [
                node for node in descendants if node.node_type == NodeType.FILE
            ]
            file_node_ids = [node.id for node in file_nodes]
            files = await uow.files.list_by_node_ids(
                file_node_ids,
                include_deleted_nodes=False,
            )
            folder_node_snapshot = {
                "id": getattr(folder_node, "id", None),
                "node_type": getattr(folder_node, "node_type", None),
                "path": str(getattr(folder_node, "path", "") or ""),
            }
            file_nodes_by_id = {
                node.id: {
                    "id": getattr(node, "id", None),
                    "path": str(getattr(node, "path", "") or ""),
                    "name": str(getattr(node, "name", "") or ""),
                }
                for node in file_nodes
            }
            file_rows = [
                {
                    "id": getattr(file_row, "id", None),
                    "node_id": getattr(file_row, "node_id", None),
                    "storage_status": getattr(file_row, "storage_status", None),
                    "storage_bucket": getattr(file_row, "storage_bucket", None),
                    "storage_key": getattr(file_row, "storage_key", None),
                }
                for file_row in files
            ]

        if folder_node_snapshot is None:
            return failure_result(
                error_message="РЈРєР°Р·Р°РЅРЅР°СЏ РїР°РїРєР° РЅРµ РЅР°Р№РґРµРЅР°.",
                error_code="folder_not_found",
                result_data={"folder_node_id": str(folder_node_id)},
                retry=False,
                progress_percent=0,
            )

        if folder_node_snapshot.get("node_type") != NodeType.FOLDER:
            return failure_result(
                error_message="РЈРєР°Р·Р°РЅРЅС‹Р№ СѓР·РµР» РЅРµ СЏРІР»СЏРµС‚СЃСЏ РїР°РїРєРѕР№.",
                error_code="node_is_not_folder",
                result_data={"folder_node_id": str(folder_node_id)},
                retry=False,
                progress_percent=0,
            )

        can_read = await context.services.access.can_read_node(
            node_id=folder_node_id,
            user_id=requested_by,
        )
        can_download = await context.services.access.can_download_node(
            node_id=folder_node_id,
            user_id=requested_by,
        )
        if not (can_read and can_download):
            return failure_result(
                error_message="РќРµРґРѕСЃС‚Р°С‚РѕС‡РЅРѕ РїСЂР°РІ РґР»СЏ Р°СЂС…РёРІР°С†РёРё РїР°РїРєРё.",
                error_code="permission_denied",
                result_data={
                    "folder_node_id": str(folder_node_id),
                    "requested_by": str(requested_by),
                },
                retry=False,
                progress_percent=0,
            )

        archive_bucket = context.storage_service.default_archives_bucket
        archive_key = context.storage_service.build_archive_key(
            user_id=requested_by,
            task_id=context.task_id,
            extension="zip",
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
            temp_zip_path = tmp_file.name

        files_count = 0
        folder_root_path = str(folder_node_snapshot.get("path", "") or "")
        with zipfile.ZipFile(
            temp_zip_path, mode="w", compression=zipfile.ZIP_DEFLATED
        ) as zip_handle:
            for file_row in file_rows:
                if file_row.get("storage_status") != StorageObjectStatus.AVAILABLE:
                    continue
                if not file_row.get("storage_bucket") or not file_row.get("storage_key"):
                    continue

                node_id = file_row.get("node_id")
                if not isinstance(node_id, UUID):
                    continue
                file_node = file_nodes_by_id.get(node_id)
                if file_node is None:
                    continue

                archive_member_path = _safe_archive_member_path(
                    folder_root_path=folder_root_path,
                    file_node_path=str(file_node.get("path", "") or ""),
                    fallback_name=str(file_node.get("name", "") or file_row.get("id")),
                )

                downloaded = await context.storage_service.objects.get_object_bytes(
                    bucket=str(file_row["storage_bucket"]),
                    object_key=str(file_row["storage_key"]),
                )
                zip_handle.writestr(archive_member_path, downloaded.data)
                files_count += 1

        archive_size_bytes = os.path.getsize(temp_zip_path)
        with open(temp_zip_path, "rb") as archive_stream:
            await context.storage_service.objects.put_object(
                bucket=archive_bucket,
                object_key=archive_key,
                data=archive_stream,
                length=archive_size_bytes,
                content_type="application/zip",
                metadata={
                    "task_id": str(context.task_id),
                    "folder_node_id": str(folder_node_id),
                    "requested_by": str(requested_by),
                    "archive_name": str(archive_name).strip()
                    if isinstance(archive_name, str)
                    else "",
                },
            )

        return success_result(
            result_data={
                "archive_bucket": archive_bucket,
                "archive_key": archive_key,
                "archive_size_bytes": int(archive_size_bytes),
                "files_count": int(files_count),
                "folder_node_id": str(folder_node_id),
            },
            progress_percent=100,
        )

    except (StorageConnectionError, DatabaseConnectionError) as exc:
        return retry_result(
            error_message="Р’СЂРµРјРµРЅРЅР°СЏ РѕС€РёР±РєР° РїСЂРё СЃРѕР·РґР°РЅРёРё Р°СЂС…РёРІР° РїР°РїРєРё.",
            error_code="temporary_unavailable",
            result_data={"reason": str(exc), "error_type": exc.__class__.__name__},
        )
    except (ServiceError, StorageError) as exc:
        return failure_result(
            error_message="РћС€РёР±РєР° СЃРѕР·РґР°РЅРёСЏ Р°СЂС…РёРІР° РїР°РїРєРё.",
            error_code="create_folder_archive_failed",
            result_data={"reason": str(exc), "error_type": exc.__class__.__name__},
            retry=False,
            progress_percent=0,
        )
    except Exception as exc:
        return failure_result(
            error_message="РќРµРїСЂРµРґРІРёРґРµРЅРЅР°СЏ РѕС€РёР±РєР° СЃРѕР·РґР°РЅРёСЏ Р°СЂС…РёРІР° РїР°РїРєРё.",
            error_code="unexpected_create_folder_archive_error",
            result_data={"reason": str(exc), "error_type": exc.__class__.__name__},
            retry=False,
            progress_percent=0,
        )
    finally:
        if temp_zip_path and os.path.exists(temp_zip_path):
            try:
                os.remove(temp_zip_path)
            except OSError:
                pass


async def _try_service_archive(
    context: WorkerTaskExecutionContext,
    folder_node_id: UUID,
    requested_by: UUID,
    archive_name: str | None,
) -> WorkerTaskExecutionResult | None:
    downloads_service = getattr(context.services, "downloads", None)
    if downloads_service is None:
        return None

    candidate_methods = (
        "create_folder_archive",
        "build_folder_archive",
        "generate_folder_archive",
    )
    for method_name in candidate_methods:
        method = getattr(downloads_service, method_name, None)
        if not callable(method):
            continue
        try:
            maybe_result = method(
                folder_node_id=folder_node_id,
                requested_by=requested_by,
                task_id=context.task_id,
                archive_name=archive_name,
            )
            result = await maybe_result if isawaitable(maybe_result) else maybe_result
            if isinstance(result, dict):
                return success_result(
                    result_data={
                        "archive_bucket": result.get("archive_bucket"),
                        "archive_key": result.get("archive_key"),
                        "archive_size_bytes": result.get("archive_size_bytes"),
                        "files_count": result.get("files_count"),
                        "folder_node_id": str(folder_node_id),
                    },
                    progress_percent=100,
                )
        except TypeError:
            continue
    return None


def _safe_archive_member_path(
    *,
    folder_root_path: str,
    file_node_path: str,
    fallback_name: str,
) -> str:
    """Р¤РѕСЂРјРёСЂСѓРµС‚ Р±РµР·РѕРїР°СЃРЅС‹Р№ РѕС‚РЅРѕСЃРёС‚РµР»СЊРЅС‹Р№ РїСѓС‚СЊ С„Р°Р№Р»Р° РІРЅСѓС‚СЂРё ZIP."""

    root = _normalize_fs_path(folder_root_path)
    file_path = _normalize_fs_path(file_node_path)

    if root and file_path.startswith(f"{root}/"):
        relative = file_path[len(root) + 1 :]
    elif file_path == root:
        relative = fallback_name
    else:
        relative = file_path.rsplit("/", maxsplit=1)[-1] or fallback_name

    normalized = posixpath.normpath(relative.replace("\\", "/").strip("/"))
    if (
        normalized in {"", ".", ".."}
        or normalized.startswith("../")
        or "/../" in normalized
    ):
        raise ValueError(
            "РћР±РЅР°СЂСѓР¶РµРЅР° РїРѕРїС‹С‚РєР° path traversal РїСЂРё С„РѕСЂРјРёСЂРѕРІР°РЅРёРё ZIP-Р°СЂС…РёРІР°."
        )

    if PurePosixPath(normalized).is_absolute():
        raise ValueError("РџСѓС‚СЊ РІРЅСѓС‚СЂРё ZIP РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ РѕС‚РЅРѕСЃРёС‚РµР»СЊРЅС‹Рј.")

    return normalized


def _normalize_fs_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip()
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    return normalized.rstrip("/")


def _payload_uuid_alias(payload: Any, *keys: str) -> UUID:
    """РР·РІР»РµРєР°РµС‚ UUID РёР· РїРµСЂРІРѕРіРѕ РЅР°Р№РґРµРЅРЅРѕРіРѕ РєР»СЋС‡Р° payload."""

    if not hasattr(payload, "get"):
        raise WorkerTaskHandlerError(
            "Payload Р·Р°РґР°С‡Рё РґРѕР»Р¶РµРЅ РїРѕРґРґРµСЂР¶РёРІР°С‚СЊ РґРѕСЃС‚СѓРї РїРѕ РєР»СЋС‡Сѓ.",
            operation="require_payload_value",
        )

    for key in keys:
        value = payload.get(key)
        if isinstance(value, UUID):
            return value
        if isinstance(value, str) and value.strip():
            try:
                return UUID(value.strip())
            except ValueError as exc:
                raise WorkerTaskHandlerError(
                    "Payload СЃРѕРґРµСЂР¶РёС‚ РЅРµРєРѕСЂСЂРµРєС‚РЅС‹Р№ UUID.",
                    operation="require_payload_value",
                    details={"key": key, "value": value},
                    cause=exc,
                ) from exc

    raise WorkerTaskHandlerError(
        "Р’ payload РѕС‚СЃСѓС‚СЃС‚РІСѓРµС‚ РѕР±СЏР·Р°С‚РµР»СЊРЅС‹Р№ UUID.",
        operation="require_payload_value",
        details={"keys": list(keys)},
    )


def _resolve_folder_node_id(payload: Any, *, task_meta: dict[str, Any] | None) -> UUID:
    """РћРїСЂРµРґРµР»СЏРµС‚ UUID РїР°РїРєРё РёР· payload РёР»Рё СЃРІСЏР·Рё Р·Р°РґР°С‡Рё."""

    try:
        return _payload_uuid_alias(payload, "folder_node_id", "folder_id")
    except WorkerTaskHandlerError:
        related_entity_id = None if task_meta is None else task_meta.get("related_entity_id")
        if isinstance(related_entity_id, UUID):
            return related_entity_id
        raise


def _resolve_requested_by(payload: Any, *, task_meta: dict[str, Any] | None) -> UUID:
    """РћРїСЂРµРґРµР»СЏРµС‚ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ, Р·Р°РїСЂРѕСЃРёРІС€РµРіРѕ СЃРѕР·РґР°РЅРёРµ Р°СЂС…РёРІР°."""

    if hasattr(payload, "get"):
        raw_value = payload.get("requested_by") or payload.get("user_id")
        if isinstance(raw_value, UUID):
            return raw_value
        if isinstance(raw_value, str) and raw_value.strip():
            try:
                return UUID(raw_value.strip())
            except ValueError as exc:
                raise WorkerTaskHandlerError(
                    "Payload СЃРѕРґРµСЂР¶РёС‚ РЅРµРєРѕСЂСЂРµРєС‚РЅС‹Р№ РёРґРµРЅС‚РёС„РёРєР°С‚РѕСЂ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ.",
                    operation="require_payload_value",
                    details={"key": "requested_by", "value": raw_value},
                    cause=exc,
                ) from exc

    created_by = None if task_meta is None else task_meta.get("created_by")
    if isinstance(created_by, UUID):
        return created_by

    raise WorkerTaskHandlerError(
        "РќРµ СѓРґР°Р»РѕСЃСЊ РѕРїСЂРµРґРµР»РёС‚СЊ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ, Р·Р°РїСЂРѕСЃРёРІС€РµРіРѕ Р°СЂС…РёРІ.",
        operation="require_payload_value",
        details={"task_id": str("" if task_meta is None else task_meta.get("id", ""))},
    )


__all__ = [
    "create_folder_archive_handler",
]

