from __future__ import annotations

from typing import Final


class WorkerConstants:
    """Базовые константы worker-процесса."""

    WORKER_NAME_PREFIX: Final[str] = "localcloud-worker"
    WORKER_POLL_INTERVAL_SECONDS: Final[int] = 5
    WORKER_IDLE_SLEEP_SECONDS: Final[int] = 2
    WORKER_BATCH_SIZE: Final[int] = 10
    WORKER_MAX_CONCURRENT_TASKS: Final[int] = 4
    WORKER_SHUTDOWN_TIMEOUT_SECONDS: Final[int] = 30


class WorkerTaskConstants:
    """Константы обработки задач и повторных попыток."""

    WORKER_RETRY_DELAY_SECONDS: Final[int] = 60
    WORKER_MAX_RETRY_DELAY_SECONDS: Final[int] = 3600


class WorkerSchedulerConstants:
    """Интервалы периодических задач scheduler."""

    CLEAN_TRASH_INTERVAL_SECONDS: Final[int] = 3600
    CLEAN_EXPIRED_UPLOADS_INTERVAL_SECONDS: Final[int] = 1800
    CLEAN_EXPIRED_PUBLIC_LINKS_INTERVAL_SECONDS: Final[int] = 3600
    RECALCULATE_QUOTAS_INTERVAL_SECONDS: Final[int] = 86400
    CHECK_STORAGE_INTEGRITY_INTERVAL_SECONDS: Final[int] = 86400


class WorkerLockConstants:
    """Константы блокировок задач."""

    WORKER_TASK_LOCK_TTL_SECONDS: Final[int] = 300
    WORKER_STALE_TASK_LOCK_SECONDS: Final[int] = 900


class WorkerArchiveConstants:
    """Константы архивирования."""

    ARCHIVE_TEMP_PREFIX: Final[str] = "localcloud-archive-"
    ARCHIVE_EXTENSION: Final[str] = "zip"


class WorkerCleanupConstants:
    """Размеры batch-обработки для задач очистки и пересчётов."""

    CLEANUP_BATCH_SIZE: Final[int] = 100
    INTEGRITY_BATCH_SIZE: Final[int] = 100
    QUOTA_BATCH_SIZE: Final[int] = 100


__all__ = [
    "WorkerConstants",
    "WorkerTaskConstants",
    "WorkerSchedulerConstants",
    "WorkerLockConstants",
    "WorkerArchiveConstants",
    "WorkerCleanupConstants",
]
