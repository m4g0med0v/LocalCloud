from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from core.logging import get_logger
from database.models.enums import (
    BackgroundTaskStatus,
    BackgroundTaskType,
    TaskPriority,
)
from workers.context import WorkerContext
from workers.tasks import jsonable

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class _ScheduleSpec:
    task_type: BackgroundTaskType
    interval_seconds: int
    key_prefix: str
    priority: TaskPriority
    payload: dict[str, Any]
    key_format: str


class WorkerScheduler:
    """Периодически создаёт системные фоновые задачи."""

    def __init__(self, context: WorkerContext) -> None:
        self.context = context

    async def run_due_schedules(self) -> int:
        """Создаёт задачи по всем активным расписаниям."""

        if not self.context.worker_settings.worker_scheduler_enabled:
            return 0

        created_count = 0
        created_count += await self.schedule_clean_trash()
        created_count += await self.schedule_clean_expired_uploads()
        created_count += await self.schedule_clean_expired_public_links()
        created_count += await self.schedule_recalculate_user_quotas()
        created_count += await self.schedule_storage_integrity_check()
        return created_count

    async def schedule_clean_trash(self) -> int:
        """Планирует системную задачу очистки корзины."""

        spec = _ScheduleSpec(
            task_type=BackgroundTaskType.CLEAN_TRASH,
            interval_seconds=self.context.worker_settings.worker_clean_trash_interval_seconds,
            key_prefix="system:clean_trash",
            priority=TaskPriority.NORMAL,
            payload={},
            key_format="%Y-%m-%dT%H",
        )
        return await self._create_scheduled_task(spec)

    async def schedule_clean_expired_uploads(self) -> int:
        """Планирует системную задачу очистки просроченных upload-сессий."""

        spec = _ScheduleSpec(
            task_type=BackgroundTaskType.CLEAN_EXPIRED_UPLOADS,
            interval_seconds=(
                self.context.worker_settings.worker_clean_expired_uploads_interval_seconds
            ),
            key_prefix="system:clean_expired_uploads",
            priority=TaskPriority.NORMAL,
            payload={},
            key_format="%Y-%m-%dT%H:%M",
        )
        return await self._create_scheduled_task(spec)

    async def schedule_clean_expired_public_links(self) -> int:
        """Планирует системную задачу деактивации просроченных публичных ссылок."""

        spec = _ScheduleSpec(
            task_type=BackgroundTaskType.CLEAN_EXPIRED_PUBLIC_LINKS,
            interval_seconds=(
                self.context.worker_settings.worker_clean_expired_public_links_interval_seconds
            ),
            key_prefix="system:clean_expired_public_links",
            priority=TaskPriority.NORMAL,
            payload={},
            key_format="%Y-%m-%dT%H",
        )
        return await self._create_scheduled_task(spec)

    async def schedule_recalculate_user_quotas(self) -> int:
        """Планирует системную задачу пересчёта пользовательских квот."""

        spec = _ScheduleSpec(
            task_type=BackgroundTaskType.RECALCULATE_USER_QUOTA,
            interval_seconds=(
                self.context.worker_settings.worker_recalculate_quotas_interval_seconds
            ),
            key_prefix="system:recalculate_user_quota",
            priority=TaskPriority.LOW,
            payload={"limit": self.context.worker_settings.worker_quota_batch_size},
            key_format="%Y-%m-%d",
        )
        return await self._create_scheduled_task(spec)

    async def schedule_storage_integrity_check(self) -> int:
        """Планирует системную задачу проверки целостности storage-объектов."""

        spec = _ScheduleSpec(
            task_type=BackgroundTaskType.CHECK_STORAGE_INTEGRITY,
            interval_seconds=(
                self.context.worker_settings.worker_storage_integrity_interval_seconds
            ),
            key_prefix="system:check_storage_integrity",
            priority=TaskPriority.LOW,
            payload={"limit": self.context.worker_settings.worker_integrity_batch_size},
            key_format="%Y-%m-%d",
        )
        return await self._create_scheduled_task(spec)

    async def _create_scheduled_task(self, spec: _ScheduleSpec) -> int:
        now = datetime.now(UTC)
        scheduled_at = _floor_to_interval(now, spec.interval_seconds)
        idempotency_key = f"{spec.key_prefix}:{scheduled_at.strftime(spec.key_format)}"

        payload: dict[str, Any] = {
            "scheduled_for": scheduled_at.isoformat(),
            **spec.payload,
        }

        async with self.context.uow_factory() as uow:
            existing = await uow.tasks.get_by_idempotency_key(idempotency_key)
            if existing is not None:
                return 0

            task = await uow.tasks.create_task(
                task_type=spec.task_type,
                created_by=None,
                related_entity_type="system",
                related_entity_id=None,
                status=BackgroundTaskStatus.PENDING,
                progress_percent=0,
                result_data=None,
                error_message=None,
                started_at=None,
                finished_at=None,
                flush=False,
                refresh=False,
            )
            task.priority = spec.priority
            task.payload = jsonable(payload)
            task.error_code = None
            task.attempts_count = 0
            task.max_attempts = 3
            task.idempotency_key = idempotency_key
            task.scheduled_at = scheduled_at
            task.locked_by = None
            task.locked_until = None

            await uow.flush()
            await uow.commit()

        logger.info(
            "Создана системная фоновая задача scheduler",
            extra={
                "task_type": spec.task_type.value,
                "idempotency_key": idempotency_key,
                "scheduled_at": scheduled_at.isoformat(),
                "worker_id": self.context.worker_id,
            },
        )
        return 1


def _floor_to_interval(moment: datetime, interval_seconds: int) -> datetime:
    if interval_seconds <= 0:
        return moment

    epoch = int(moment.timestamp())
    floored_epoch = epoch - (epoch % interval_seconds)
    return datetime.fromtimestamp(floored_epoch, tz=UTC)


__all__ = ["WorkerScheduler"]
