from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from database import get_database_health_report
from workers.context import WorkerContext

WorkerComponentStatus = Literal["ok", "degraded", "unavailable"]


@dataclass(frozen=True, slots=True)
class WorkerHealthStatus:
    """Сводный статус внутренней проверки worker-процесса."""

    worker_id: str
    status: WorkerComponentStatus
    checked_at: datetime
    database_ok: bool
    storage_ok: bool
    scheduler_enabled: bool
    details: dict[str, Any] = field(default_factory=dict)


class WorkerHealthChecker:
    """Внутренняя проверка health-состояния worker-процесса."""

    def __init__(self, context: WorkerContext) -> None:
        self.context = context

    async def check(self) -> WorkerHealthStatus:
        """Возвращает агрегированный статус worker-процесса."""

        checked_at = datetime.now(UTC)
        details: dict[str, Any] = {
            "worker_id": self.context.worker_id,
            "scheduler_enabled": self.context.worker_settings.worker_scheduler_enabled,
        }

        database_ok = False
        storage_ok = False

        # Предпочитаем готовую бизнес-логику health-сервиса.
        try:
            readiness = await self.context.services.health.get_readiness(
                check_database=True,
                check_storage=True,
                check_storage_read_write=False,
            )
            database_ok = bool(
                readiness.database is not None
                and str(readiness.database.status).lower() == "ok"
            )
            storage_ok = bool(
                readiness.storage is not None
                and str(readiness.storage.status).lower() == "ok"
            )
            details["source"] = "services.health.get_readiness"
            details["readiness_status"] = str(readiness.status)
        except Exception as exc:
            details["source"] = "direct_checks_fallback"
            details["readiness_error"] = {
                "message": str(exc),
                "error_type": exc.__class__.__name__,
            }
            database_ok = await self.check_database()
            storage_ok = await self.check_storage()

        dispatcher_ok = await self.check_dispatcher()
        details["dispatcher_ok"] = dispatcher_ok

        if database_ok and storage_ok:
            status: WorkerComponentStatus = "ok"
        elif database_ok or storage_ok:
            status = "degraded"
        else:
            status = "unavailable"

        return WorkerHealthStatus(
            worker_id=self.context.worker_id,
            status=status,
            checked_at=checked_at,
            database_ok=database_ok,
            storage_ok=storage_ok,
            scheduler_enabled=self.context.worker_settings.worker_scheduler_enabled,
            details=details,
        )

    async def check_database(self) -> bool:
        """Проверяет доступность базы данных для worker-процесса."""

        try:
            report = await get_database_health_report(raise_on_error=False)
            return str(report.status).lower() in {"healthy", "ok"}
        except Exception:
            return False

    async def check_storage(self) -> bool:
        """Проверяет доступность object storage для worker-процесса."""

        try:
            report = await self.context.storage_service.health.check_storage_health(
                bucket=self.context.storage_service.default_files_bucket,
                check_read_write=False,
            )
            return str(report.state).lower() == "healthy"
        except Exception:
            return False

    async def check_dispatcher(self) -> bool:
        """Проверяет работоспособность зависимостей dispatcher-слоя."""

        try:
            async with self.context.uow_factory() as uow:
                await uow.tasks.find_pending_tasks(limit=1)
            return True
        except Exception:
            return False


__all__ = ["WorkerHealthStatus", "WorkerHealthChecker"]
