from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, TypeAlias
from uuid import UUID

from core.config import Settings
from database import UnitOfWorkFactory
from database.models.enums import BackgroundTaskStatus, BackgroundTaskType
from storage import StorageService
from workers.config import WorkerSettings


class WorkerState(StrEnum):
    """Состояние worker-процесса."""

    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


class WorkerRunMode(StrEnum):
    """Режим запуска worker-процесса."""

    ONCE = "once"
    LOOP = "loop"
    SCHEDULER = "scheduler"


@dataclass(frozen=True, slots=True)
class WorkerIdentity:
    """Идентификационные данные worker-процесса."""

    worker_id: str
    worker_name: str
    run_mode: WorkerRunMode


@dataclass(frozen=True, slots=True)
class WorkerTaskExecutionContext:
    """Контекст выполнения фоновой задачи."""

    task_id: UUID
    task_type: BackgroundTaskType
    payload: Mapping[str, Any]
    worker_id: str
    settings: Settings
    worker_settings: WorkerSettings
    uow_factory: UnitOfWorkFactory
    storage_service: StorageService
    services: Any


@dataclass(frozen=True, slots=True)
class WorkerTaskExecutionResult:
    """Результат выполнения фоновой задачи."""

    success: bool
    progress_percent: int = 100
    result_data: dict[str, Any] | None = None
    error_message: str | None = None
    error_code: str | None = None
    retry: bool = False


@dataclass(frozen=True, slots=True)
class WorkerScheduleDefinition:
    """Определение периодической задачи планировщика."""

    schedule_name: str
    task_type: BackgroundTaskType
    interval_seconds: int
    payload: Mapping[str, Any] = field(default_factory=dict)
    enabled: bool = True
    initial_status: BackgroundTaskStatus = BackgroundTaskStatus.PENDING


@dataclass(slots=True)
class WorkerRuntimeStats:
    """Статистика выполнения задач worker-процесса."""

    fetched_count: int = 0
    started_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    retried_count: int = 0
    skipped_count: int = 0
    created_scheduled_count: int = 0


WorkerTaskHandler: TypeAlias = Callable[
    [WorkerTaskExecutionContext],
    Awaitable[WorkerTaskExecutionResult],
]


__all__ = [
    "WorkerState",
    "WorkerRunMode",
    "WorkerIdentity",
    "WorkerTaskExecutionContext",
    "WorkerTaskExecutionResult",
    "WorkerScheduleDefinition",
    "WorkerRuntimeStats",
    "WorkerTaskHandler",
]
