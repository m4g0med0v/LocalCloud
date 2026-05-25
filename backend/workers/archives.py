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
from workers.tasks import (
    failure_result,
    optional_payload_value,
    payload_uuid,
    retry_result,
    success_result,
)
from workers.types import WorkerTaskExecutionContext, WorkerTaskExecutionResult


async def create_folder_archive_handler(
    context: WorkerTaskExecutionContext,
) -> WorkerTaskExecutionResult:
    """Создаёт ZIP-архив папки в фоновом режиме."""

    temp_zip_path: str | None = None
    folder_node: Any | None = None
    descendants: list[Any] = []
    files: list[Any] = []
    try:
        payload = context.payload
        folder_node_id = payload_uuid(payload, "folder_node_id")
        requested_by = payload_uuid(payload, "requested_by")
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

        if folder_node is None:
            return failure_result(
                error_message="Указанная папка не найдена.",
                error_code="folder_not_found",
                result_data={"folder_node_id": str(folder_node_id)},
                retry=False,
                progress_percent=0,
            )

        if folder_node.node_type != NodeType.FOLDER:
            return failure_result(
                error_message="Указанный узел не является папкой.",
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
                error_message="Недостаточно прав для архивации папки.",
                error_code="permission_denied",
                result_data={
                    "folder_node_id": str(folder_node_id),
                    "requested_by": str(requested_by),
                },
                retry=False,
                progress_percent=0,
            )

        async with context.uow_factory() as uow:
            descendants = await uow.nodes.get_descendants(
                node_id=folder_node_id,
                include_self=False,
                include_deleted=False,
            )

        file_nodes = [node for node in descendants if node.node_type == NodeType.FILE]
        file_node_ids = [node.id for node in file_nodes]
        nodes_by_id = {node.id: node for node in file_nodes}

        async with context.uow_factory() as uow:
            files = await uow.files.list_by_node_ids(
                file_node_ids,
                include_deleted_nodes=False,
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
        folder_root_path = str(getattr(folder_node, "path", "") or "")
        with zipfile.ZipFile(
            temp_zip_path, mode="w", compression=zipfile.ZIP_DEFLATED
        ) as zip_handle:
            for file_row in files:
                if file_row.storage_status != StorageObjectStatus.AVAILABLE:
                    continue
                if not file_row.storage_bucket or not file_row.storage_key:
                    continue

                file_node = nodes_by_id.get(file_row.node_id)
                if file_node is None:
                    continue

                archive_member_path = _safe_archive_member_path(
                    folder_root_path=folder_root_path,
                    file_node_path=str(file_node.path or ""),
                    fallback_name=str(file_node.name or file_row.id),
                )

                downloaded = await context.storage_service.objects.get_object_bytes(
                    bucket=file_row.storage_bucket,
                    object_key=file_row.storage_key,
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
            error_message="Временная ошибка при создании архива папки.",
            error_code="temporary_unavailable",
            result_data={"reason": str(exc), "error_type": exc.__class__.__name__},
        )
    except (ServiceError, StorageError) as exc:
        return failure_result(
            error_message="Ошибка создания архива папки.",
            error_code="create_folder_archive_failed",
            result_data={"reason": str(exc), "error_type": exc.__class__.__name__},
            retry=False,
            progress_percent=0,
        )
    except Exception as exc:
        return failure_result(
            error_message="Непредвиденная ошибка создания архива папки.",
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
    """Формирует безопасный относительный путь файла внутри ZIP."""

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
            "Обнаружена попытка path traversal при формировании ZIP-архива."
        )

    if PurePosixPath(normalized).is_absolute():
        raise ValueError("Путь внутри ZIP должен быть относительным.")

    return normalized


def _normalize_fs_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip()
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    return normalized.rstrip("/")


__all__ = [
    "create_folder_archive_handler",
]
