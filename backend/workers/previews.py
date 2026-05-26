from __future__ import annotations

import io
from typing import Any
from uuid import UUID

from database.exceptions import DatabaseConnectionError
from database.models.enums import FilePreviewStatus
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

_TEXT_PREVIEW_MAX_BYTES = 4096

_PREVIEW_SUPPORTED_MIME_PREFIXES: tuple[str, ...] = (
    "image/",
    "text/",
)
_PREVIEW_SUPPORTED_MIME_TYPES: tuple[str, ...] = (
    "application/pdf",
    "application/json",
)

_TEXT_MIME_PREFIXES: tuple[str, ...] = ("text/",)
_TEXT_MIME_TYPES: tuple[str, ...] = ("application/json",)


async def generate_file_preview_handler(
    context: WorkerTaskExecutionContext,
) -> WorkerTaskExecutionResult:
    """Обрабатывает задачу генерации preview для файла.

    Для текстовых файлов и JSON создаёт текстовый сниппет и сохраняет его
    в объектное хранилище. Для изображений и PDF помечает статус как
    NOT_REQUIRED — фронтенд использует оригинальный presigned URL напрямую.
    """

    file_row: Any | None = None
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
                    "preview_storage_key": getattr(
                        updated,  # pyright: ignore[reportPossiblyUnboundVariable]
                        "preview_storage_key",
                        None,
                    ),
                },
                progress_percent=100,
            )

        # Изображения и PDF не требуют отдельного preview-файла:
        # фронтенд использует presigned URL оригинального файла напрямую.
        if _mime_is_image_or_pdf(mime_type):
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
                    "preview_storage_key": getattr(
                        updated,  # pyright: ignore[reportPossiblyUnboundVariable]
                        "preview_storage_key",
                        None,
                    ),
                },
                progress_percent=100,
            )

        # Текстовые файлы и JSON: читаем первые N байт и сохраняем как preview.
        owner_id = _resolve_owner_id(file_row)
        preview_key = context.storage_service.build_preview_key(
            user_id=owner_id,
            file_id=file_row.id,
            extension="txt",
        )

        downloaded = await context.storage_service.objects.get_object_bytes(
            bucket=file_row.storage_bucket,
            object_key=file_row.storage_key,
        )
        preview_bytes = downloaded.data[:_TEXT_PREVIEW_MAX_BYTES]

        await context.storage_service.objects.put_object(
            bucket=context.storage_service.default_files_bucket,
            object_key=preview_key,
            data=io.BytesIO(preview_bytes),
            length=len(preview_bytes),
            content_type="text/plain; charset=utf-8",
        )

        async with context.uow_factory() as uow:
            updated = await uow.files.update_preview(
                file_id=file_row.id,
                preview_status=FilePreviewStatus.READY,
                preview_storage_key=preview_key,
                flush=True,
                refresh=True,
            )
            await uow.commit()

        return success_result(
            result_data={
                "file_id": str(file_row.id),
                "preview_status": FilePreviewStatus.READY.value,
                "preview_storage_key": preview_key,
            },
            progress_percent=100,
        )

    except (DatabaseConnectionError, StorageConnectionError) as exc:
        return retry_result(
            error_message="Временная ошибка подключения при генерации preview.",
            error_code="temporary_unavailable",
            result_data={"reason": str(exc), "error_type": exc.__class__.__name__},
        )
    except StorageError as exc:
        return failure_result(
            error_message="Ошибка хранилища при генерации preview файла.",
            error_code="storage_error",
            result_data={"reason": str(exc), "error_type": exc.__class__.__name__},
            retry=False,
            progress_percent=0,
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


def _mime_is_image_or_pdf(mime_type: str) -> bool:
    return mime_type.startswith("image/") or mime_type == "application/pdf"


def _mime_is_text(mime_type: str) -> bool:
    if mime_type in _TEXT_MIME_TYPES:
        return True
    return any(mime_type.startswith(prefix) for prefix in _TEXT_MIME_PREFIXES)


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
