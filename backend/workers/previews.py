from __future__ import annotations

from typing import Any
from uuid import UUID

from database.exceptions import DatabaseConnectionError
from database.models.enums import FilePreviewStatus
from services.exceptions import ServiceError
from workers.tasks import (
    failure_result,
    optional_payload_value,
    payload_uuid,
    retry_result,
    success_result,
)
from workers.types import WorkerTaskExecutionContext, WorkerTaskExecutionResult

_PREVIEW_SUPPORTED_MIME_PREFIXES: tuple[str, ...] = (
    "image/",
    "text/",
)
_PREVIEW_SUPPORTED_MIME_TYPES: tuple[str, ...] = (
    "application/pdf",
    "application/json",
)


async def generate_file_preview_handler(
    context: WorkerTaskExecutionContext,
) -> WorkerTaskExecutionResult:
    """Обрабатывает задачу генерации preview для файла."""

    file_row: Any | None = None
    updated: Any | None = None
    try:
        payload = context.payload
        file_id = payload_uuid(payload, "file_id")
        force = bool(
            optional_payload_value(payload, "force", expected_type=bool, default=False)
        )

        async with context.uow_factory() as uow:
            file_row = await uow.files.get_by_id(file_id)

        if file_row is None:
            return failure_result(
                error_message="Файл для генерации preview не найден.",
                error_code="file_not_found",
                result_data={
                    "file_id": str(file_id),
                    "preview_status": None,
                    "preview_storage_key": None,
                },
                retry=False,
                progress_percent=0,
            )

        if not force and file_row.preview_status == FilePreviewStatus.READY:
            return success_result(
                result_data={
                    "file_id": str(file_row.id),
                    "preview_status": file_row.preview_status.value,
                    "preview_storage_key": file_row.preview_storage_key,
                },
                progress_percent=100,
            )

        mime_type = (file_row.mime_type or "").strip().lower()
        if not _mime_requires_preview(mime_type):
            async with context.uow_factory() as uow:
                updated = await uow.files.mark_preview_not_required(
                    file_id=file_row.id,
                    flush=True,
                    refresh=True,
                )
                await uow.commit()

            return success_result(
                result_data={
                    "file_id": str(file_row.id),
                    "preview_status": FilePreviewStatus.NOT_REQUIRED.value,
                    "preview_storage_key": getattr(updated, "preview_storage_key", None),
                },
                progress_percent=100,
            )

        owner_id = _resolve_owner_id(file_row)
        extension = _preview_extension_for_mime(mime_type)
        preview_storage_key = context.storage_service.build_preview_key(
            user_id=owner_id,
            file_id=file_row.id,
            extension=extension,
        )

        async with context.uow_factory() as uow:
            updated = await uow.files.update_preview(
                file_id=file_row.id,
                preview_status=FilePreviewStatus.FAILED,
                preview_storage_key=preview_storage_key,
                flush=True,
                refresh=True,
            )
            await uow.commit()

        return failure_result(
            error_message="Генератор предпросмотров ещё не реализован.",
            error_code="preview_generator_not_implemented",
            result_data={
                "file_id": str(file_row.id),
                "preview_status": FilePreviewStatus.FAILED.value,
                "preview_storage_key": preview_storage_key,
            },
            retry=False,
            progress_percent=0,
        )

    except (DatabaseConnectionError,) as exc:
        return retry_result(
            error_message="Временная ошибка подключения при генерации preview.",
            error_code="temporary_unavailable",
            result_data={"reason": str(exc), "error_type": exc.__class__.__name__},
        )
    except ServiceError as exc:
        return failure_result(
            error_message="Ошибка обработки preview файла.",
            error_code="preview_processing_failed",
            result_data={"reason": str(exc), "error_type": exc.__class__.__name__},
            retry=False,
            progress_percent=0,
        )
    except Exception as exc:
        return failure_result(
            error_message="Непредвиденная ошибка обработки preview файла.",
            error_code="unexpected_preview_processing_error",
            result_data={"reason": str(exc), "error_type": exc.__class__.__name__},
            retry=False,
            progress_percent=0,
        )


def _mime_requires_preview(mime_type: str) -> bool:
    if not mime_type:
        return False
    if mime_type in _PREVIEW_SUPPORTED_MIME_TYPES:
        return True
    return any(
        mime_type.startswith(prefix) for prefix in _PREVIEW_SUPPORTED_MIME_PREFIXES
    )


def _preview_extension_for_mime(mime_type: str) -> str | None:
    if mime_type == "application/pdf":
        return "jpg"
    if mime_type.startswith("image/"):
        return "jpg"
    if mime_type.startswith("text/") or mime_type == "application/json":
        return "txt"
    return None


def _resolve_owner_id(file_row: Any) -> UUID:
    node = getattr(file_row, "node", None)
    owner_id = getattr(node, "owner_id", None)
    if isinstance(owner_id, UUID):
        return owner_id
    raise ValueError(
        "Не удалось определить owner_id для файла при формировании preview key."
    )


__all__ = [
    "generate_file_preview_handler",
]
