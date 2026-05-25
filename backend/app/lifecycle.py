from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI

from core.config import Settings, get_settings
from core.logging import (
    configure_root_exception_logging,
    get_logger,
    setup_logging,
    silence_noisy_loggers,
)
from database import (
    close_db_client,
    init_db_client,
    is_db_client_initialized,
    ping_database,
)
from services import get_health_service
from storage import StorageService, get_storage_service

logger = get_logger("app.lifecycle")


async def startup_backend(app: FastAPI) -> None:
    """Выполняет startup backend-приложения."""

    settings = get_settings()
    storage_service: StorageService | None = None

    setup_logging(settings.logging)
    silence_noisy_loggers()
    configure_root_exception_logging()

    try:
        app.state.settings = settings
        app.state.started_at = datetime.now(UTC)

        if not is_db_client_initialized():
            init_db_client(settings.database)
        await ping_database()

        storage_service = get_storage_service(settings=settings.storage)
        await storage_service.ensure_buckets_ready(create_missing=True)

        app.state.storage_service = storage_service
        app.state.health_service = get_health_service(
            settings=settings,
            storage_service=storage_service,
        )

        logger.info(
            "Backend успешно запущен.",
            extra={
                "app_name": settings.app.app_name,
                "app_version": settings.app.app_version,
                "debug": settings.app.debug,
            },
        )
    except Exception:
        await _safe_shutdown_resources(storage_service)
        raise


async def shutdown_backend(app: FastAPI) -> None:
    """Выполняет корректное завершение backend-приложения."""

    storage_service = _get_state_value(app, "storage_service")
    await _safe_shutdown_resources(storage_service)

    app.state.storage_service = None
    app.state.health_service = None

    logger.info("Backend корректно остановлен.")


def get_app_settings(app: FastAPI) -> Settings:
    """Возвращает settings, сохранённые в state приложения."""

    state_settings = _get_state_value(app, "settings")
    if isinstance(state_settings, Settings):
        return state_settings
    return get_settings()


async def _safe_shutdown_resources(storage_service: StorageService | None) -> None:
    if storage_service is not None:
        try:
            await storage_service.client.close()
        except Exception as exc:
            logger.warning(
                "Не удалось корректно закрыть storage client.",
                extra={"reason": str(exc), "error_type": exc.__class__.__name__},
            )

    if is_db_client_initialized():
        try:
            await close_db_client()
        except Exception as exc:
            logger.warning(
                "Не удалось корректно закрыть клиент базы данных.",
                extra={"reason": str(exc), "error_type": exc.__class__.__name__},
            )


def _get_state_value(app: FastAPI, name: str) -> Any | None:
    return getattr(app.state, name, None)


__all__ = [
    "startup_backend",
    "shutdown_backend",
    "get_app_settings",
]
