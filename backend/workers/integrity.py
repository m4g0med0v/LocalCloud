from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from database.exceptions import DatabaseConnectionError
from database.models.enums import StorageObjectStatus as DbStorageObjectStatus
from storage.exceptions import StorageConnectionError, StorageError
from storage.types import StorageIntegrityProblemType
from workers.tasks import (
    failure_result,
    jsonable,
    optional_payload_value,
    payload_int,
    retry_result,
    success_result,
)
from workers.types import WorkerTaskExecutionContext, WorkerTaskExecutionResult


async def check_storage_integrity_handler(
    context: WorkerTaskExecutionContext,
) -> WorkerTaskExecutionResult:
    """Проверяет целостность файлов между PostgreSQL и MinIO/S3."""

    try:
        payload = context.payload
        user_id = _optional_payload_uuid(payload, "user_id")
        file_id = _optional_payload_uuid(payload, "file_id")
        limit = payload_int(
            payload,
            "limit",
            default=context.worker_settings.worker_integrity_batch_size,
            min_value=1,
            max_value=5000,
        )
        if limit is None:
            limit = context.worker_settings.worker_integrity_batch_size

        files = await _load_files_for_check(
            context=context,
            user_id=user_id,
            file_id=file_id,
            limit=limit,
        )

        checked_count = 0
        missing_count = 0
        corrupted_count = 0
        failed_count = 0
        problems: list[dict[str, Any]] = []

        for file_row in files:
            checked_count += 1
            try:
                report = await context.storage_service.verify_file_object(
                    bucket=file_row.storage_bucket,
                    object_key=file_row.storage_key,
                    expected_size_bytes=int(file_row.size_bytes),
                    expected_checksum=_expected_checksum(file_row),
                    expected_checksum_algorithm=_expected_checksum_algorithm(file_row),
                )

                if report.object_exists is False:
                    await _mark_missing(context, file_row.id)
                    missing_count += 1
                    problems.append(
                        _problem_payload(
                            file_id=file_row.id,
                            bucket=file_row.storage_bucket,
                            object_key=file_row.storage_key,
                            problem_type=StorageIntegrityProblemType.OBJECT_NOT_FOUND,
                            message="Объект отсутствует в объектном хранилище.",
                        )
                    )
                    continue

                if _has_corruption_problem(report):
                    await _mark_corrupted(context, file_row.id)
                    corrupted_count += 1
                    problems.append(
                        _problem_payload(
                            file_id=file_row.id,
                            bucket=file_row.storage_bucket,
                            object_key=file_row.storage_key,
                            problem_type=_first_corruption_type(report),
                            message="Найдены несоответствия размера или контрольной суммы.",
                        )
                    )
            except Exception as exc:
                failed_count += 1
                problems.append(
                    _problem_payload(
                        file_id=file_row.id,
                        bucket=file_row.storage_bucket,
                        object_key=file_row.storage_key,
                        problem_type=None,
                        message="Ошибка проверки целостности файла.",
                        details={
                            "reason": str(exc),
                            "error_type": exc.__class__.__name__,
                        },
                    )
                )

        problems_count = missing_count + corrupted_count + failed_count
        return success_result(
            result_data={
                "checked_count": checked_count,
                "problems_count": problems_count,
                "missing_count": missing_count,
                "corrupted_count": corrupted_count,
                "problems": [jsonable(item) for item in problems],
            },
            progress_percent=100,
        )

    except (StorageConnectionError, DatabaseConnectionError) as exc:
        return retry_result(
            error_message="Временная ошибка подключения при проверке целостности файлов.",
            error_code="temporary_unavailable",
            result_data={"reason": str(exc), "error_type": exc.__class__.__name__},
        )
    except StorageError as exc:
        return failure_result(
            error_message="Ошибка проверки целостности файлов.",
            error_code="integrity_check_failed",
            result_data={"reason": str(exc), "error_type": exc.__class__.__name__},
            retry=False,
            progress_percent=0,
        )
    except Exception as exc:
        return failure_result(
            error_message="Непредвиденная ошибка проверки целостности файлов.",
            error_code="unexpected_integrity_check_error",
            result_data={"reason": str(exc), "error_type": exc.__class__.__name__},
            retry=False,
            progress_percent=0,
        )


async def _load_files_for_check(
    *,
    context: WorkerTaskExecutionContext,
    user_id: UUID | None,
    file_id: UUID | None,
    limit: int,
) -> list[Any]:
    files: list[Any] = []
    file_row: Any | None = None
    if file_id is not None:
        async with context.uow_factory() as uow:
            file_row = await uow.files.get_by_id(file_id)
        files = [] if file_row is None else [file_row]
        return files

    if user_id is not None:
        async with context.uow_factory() as uow:
            files = await uow.files.search_user_files(
                owner_id=user_id,
                include_deleted_nodes=False,
                storage_status=DbStorageObjectStatus.AVAILABLE,
                offset=0,
                limit=limit,
            )
        return files

    async with context.uow_factory() as uow:
        files = await uow.files.list_by_storage_status(
            storage_status=DbStorageObjectStatus.AVAILABLE,
            owner_id=None,
            include_deleted_nodes=False,
            offset=0,
            limit=limit,
        )
    return files


async def _mark_missing(context: WorkerTaskExecutionContext, file_id: UUID) -> None:
    async with context.uow_factory() as uow:
        await uow.files.mark_storage_missing(
            file_id=file_id,
            flush=True,
            refresh=False,
        )
        await uow.commit()


async def _mark_corrupted(context: WorkerTaskExecutionContext, file_id: UUID) -> None:
    async with context.uow_factory() as uow:
        await uow.files.mark_storage_corrupted(
            file_id=file_id,
            flush=True,
            refresh=False,
        )
        await uow.commit()


def _has_corruption_problem(report: Any) -> bool:
    for status in getattr(report, "problems", []):
        problem_type = getattr(status, "problem_type", None)
        if problem_type in {
            StorageIntegrityProblemType.SIZE_MISMATCH,
            StorageIntegrityProblemType.CHECKSUM_MISMATCH,
        }:
            return True
    return False


def _first_corruption_type(report: Any) -> StorageIntegrityProblemType:
    for status in getattr(report, "problems", []):
        problem_type = getattr(status, "problem_type", None)
        if isinstance(problem_type, StorageIntegrityProblemType) and problem_type in {
            StorageIntegrityProblemType.SIZE_MISMATCH,
            StorageIntegrityProblemType.CHECKSUM_MISMATCH,
        }:
            return problem_type
    return StorageIntegrityProblemType.CHECKSUM_MISMATCH


def _expected_checksum(file_row: Any) -> str | None:
    checksum = getattr(file_row, "checksum", None)
    if not isinstance(checksum, str):
        return None
    normalized = checksum.strip()
    return normalized or None


def _expected_checksum_algorithm(file_row: Any) -> str | None:
    algorithm = getattr(file_row, "checksum_algorithm", None)
    if algorithm is None:
        return None
    if hasattr(algorithm, "value"):
        return str(algorithm.value)
    if isinstance(algorithm, str):
        normalized = algorithm.strip().lower()
        return normalized or None
    return None


def _problem_payload(
    *,
    file_id: UUID,
    bucket: str,
    object_key: str,
    problem_type: StorageIntegrityProblemType | None,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "file_id": str(file_id),
        "bucket": bucket,
        "object_key": object_key,
        "problem_type": problem_type.value if problem_type is not None else None,
        "message": message,
    }
    if details:
        payload["details"] = details
    return payload


def _optional_payload_uuid(payload: Mapping[str, Any], key: str) -> UUID | None:
    value = optional_payload_value(payload, key, default=None)
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        return UUID(value)
    raise ValueError(f"Поле payload '{key}' должно быть UUID или строкой UUID.")


__all__ = [
    "check_storage_integrity_handler",
]
