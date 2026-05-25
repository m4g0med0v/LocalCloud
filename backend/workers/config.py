from __future__ import annotations

from functools import lru_cache
from typing import cast

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from workers.constants import (
    WorkerArchiveConstants,
    WorkerCleanupConstants,
    WorkerConstants,
    WorkerLockConstants,
    WorkerSchedulerConstants,
    WorkerTaskConstants,
)


class WorkerSettings(BaseSettings):
    """Настройки worker-процесса LocalCloud."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    worker_enabled: bool = Field(default=True, alias="WORKER_ENABLED")
    worker_name: str | None = Field(default=None, alias="WORKER_NAME")
    worker_poll_interval_seconds: int = Field(
        default=WorkerConstants.WORKER_POLL_INTERVAL_SECONDS,
        alias="WORKER_POLL_INTERVAL_SECONDS",
    )
    worker_idle_sleep_seconds: int = Field(
        default=WorkerConstants.WORKER_IDLE_SLEEP_SECONDS,
        alias="WORKER_IDLE_SLEEP_SECONDS",
    )
    worker_batch_size: int = Field(
        default=WorkerConstants.WORKER_BATCH_SIZE,
        alias="WORKER_BATCH_SIZE",
    )
    worker_max_concurrent_tasks: int = Field(
        default=WorkerConstants.WORKER_MAX_CONCURRENT_TASKS,
        alias="WORKER_MAX_CONCURRENT_TASKS",
    )
    worker_shutdown_timeout_seconds: int = Field(
        default=WorkerConstants.WORKER_SHUTDOWN_TIMEOUT_SECONDS,
        alias="WORKER_SHUTDOWN_TIMEOUT_SECONDS",
    )
    worker_task_lock_ttl_seconds: int = Field(
        default=WorkerLockConstants.WORKER_TASK_LOCK_TTL_SECONDS,
        alias="WORKER_TASK_LOCK_TTL_SECONDS",
    )
    worker_stale_task_lock_seconds: int = Field(
        default=WorkerLockConstants.WORKER_STALE_TASK_LOCK_SECONDS,
        alias="WORKER_STALE_TASK_LOCK_SECONDS",
    )
    worker_retry_delay_seconds: int = Field(
        default=WorkerTaskConstants.WORKER_RETRY_DELAY_SECONDS,
        alias="WORKER_RETRY_DELAY_SECONDS",
    )
    worker_max_retry_delay_seconds: int = Field(
        default=WorkerTaskConstants.WORKER_MAX_RETRY_DELAY_SECONDS,
        alias="WORKER_MAX_RETRY_DELAY_SECONDS",
    )
    worker_scheduler_enabled: bool = Field(
        default=True, alias="WORKER_SCHEDULER_ENABLED"
    )
    worker_clean_trash_interval_seconds: int = Field(
        default=WorkerSchedulerConstants.CLEAN_TRASH_INTERVAL_SECONDS,
        alias="WORKER_CLEAN_TRASH_INTERVAL_SECONDS",
    )
    worker_clean_expired_uploads_interval_seconds: int = Field(
        default=WorkerSchedulerConstants.CLEAN_EXPIRED_UPLOADS_INTERVAL_SECONDS,
        alias="WORKER_CLEAN_EXPIRED_UPLOADS_INTERVAL_SECONDS",
    )
    worker_clean_expired_public_links_interval_seconds: int = Field(
        default=WorkerSchedulerConstants.CLEAN_EXPIRED_PUBLIC_LINKS_INTERVAL_SECONDS,
        alias="WORKER_CLEAN_EXPIRED_PUBLIC_LINKS_INTERVAL_SECONDS",
    )
    worker_recalculate_quotas_interval_seconds: int = Field(
        default=WorkerSchedulerConstants.RECALCULATE_QUOTAS_INTERVAL_SECONDS,
        alias="WORKER_RECALCULATE_QUOTAS_INTERVAL_SECONDS",
    )
    worker_storage_integrity_interval_seconds: int = Field(
        default=WorkerSchedulerConstants.CHECK_STORAGE_INTEGRITY_INTERVAL_SECONDS,
        alias="WORKER_STORAGE_INTEGRITY_INTERVAL_SECONDS",
    )
    worker_cleanup_batch_size: int = Field(
        default=WorkerCleanupConstants.CLEANUP_BATCH_SIZE,
        alias="WORKER_CLEANUP_BATCH_SIZE",
    )
    worker_integrity_batch_size: int = Field(
        default=WorkerCleanupConstants.INTEGRITY_BATCH_SIZE,
        alias="WORKER_INTEGRITY_BATCH_SIZE",
    )
    worker_quota_batch_size: int = Field(
        default=WorkerCleanupConstants.QUOTA_BATCH_SIZE,
        alias="WORKER_QUOTA_BATCH_SIZE",
    )

    @field_validator(
        "worker_poll_interval_seconds",
        "worker_idle_sleep_seconds",
        "worker_shutdown_timeout_seconds",
        "worker_clean_trash_interval_seconds",
        "worker_clean_expired_uploads_interval_seconds",
        "worker_clean_expired_public_links_interval_seconds",
        "worker_recalculate_quotas_interval_seconds",
        "worker_storage_integrity_interval_seconds",
        mode="after",
    )
    @classmethod
    def validate_positive_intervals(cls, value: int) -> int:
        """Проверяет, что интервалы больше нуля."""
        if value <= 0:
            raise ValueError("Значение интервала должно быть больше нуля.")
        return value

    @field_validator(
        "worker_batch_size",
        "worker_cleanup_batch_size",
        "worker_integrity_batch_size",
        "worker_quota_batch_size",
        mode="after",
    )
    @classmethod
    def validate_batch_size(cls, value: int) -> int:
        """Проверяет размер batch в диапазоне от 1 до 100."""
        if value < 1 or value > 100:
            raise ValueError("Размер batch должен быть в диапазоне от 1 до 100.")
        return value

    @field_validator("worker_max_concurrent_tasks", mode="after")
    @classmethod
    def validate_max_concurrent_tasks(cls, value: int) -> int:
        """Проверяет число параллельных задач."""
        if value < 1 or value > 32:
            raise ValueError(
                "Количество параллельных задач должно быть в диапазоне от 1 до 32."
            )
        return value

    @field_validator("worker_task_lock_ttl_seconds", mode="after")
    @classmethod
    def validate_lock_ttl(cls, value: int) -> int:
        """Проверяет TTL блокировки задач."""
        if value < 30:
            raise ValueError("TTL блокировки задачи должен быть не меньше 30 секунд.")
        return value

    @field_validator("worker_retry_delay_seconds", mode="after")
    @classmethod
    def validate_retry_delay(cls, value: int) -> int:
        """Проверяет базовую задержку повторной попытки."""
        if value <= 0:
            raise ValueError("Задержка повторной попытки должна быть больше нуля.")
        return value

    @model_validator(mode="after")
    def validate_cross_fields(self) -> WorkerSettings:
        """Проверяет согласованность взаимосвязанных полей."""
        if self.worker_stale_task_lock_seconds < self.worker_task_lock_ttl_seconds:
            raise ValueError(
                "Время stale-блокировки должно быть не меньше TTL блокировки задачи."
            )
        if self.worker_max_retry_delay_seconds < self.worker_retry_delay_seconds:
            raise ValueError(
                "Максимальная задержка retry должна быть не меньше базовой задержки retry."
            )
        return self


@lru_cache(maxsize=1)
def get_worker_settings() -> WorkerSettings:
    """Возвращает кэшированный экземпляр настроек worker-процесса."""
    return WorkerSettings()


class _WorkerSettingsProxy:
    """Ленивый proxy для безопасного импорта настроек worker."""

    def __getattr__(self, name: str) -> object:
        return getattr(get_worker_settings(), name)

    def __repr__(self) -> str:
        return repr(get_worker_settings())


worker_settings = cast(WorkerSettings, _WorkerSettingsProxy())


__all__ = [
    "WorkerSettings",
    "get_worker_settings",
    "worker_settings",
    "WorkerConstants",
    "WorkerTaskConstants",
    "WorkerSchedulerConstants",
    "WorkerLockConstants",
    "WorkerArchiveConstants",
    "WorkerCleanupConstants",
]
