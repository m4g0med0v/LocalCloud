from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from api.dependencies import get_health_service_from_request_dependency
from database.models.enums import HealthStatus
from schemas.health import (
    DatabaseHealthRead,
    HealthCheckResponse,
    LivenessResponse,
    ReadinessResponse,
    StorageHealthRead,
)
from security import CurrentAdminUserDependency
from services import HealthService

router = APIRouter(prefix="/health", tags=["health"])


def _is_ok(status_value: HealthStatus | str) -> bool:
    return str(status_value).strip().lower() == HealthStatus.OK.value


@router.get(
    "/live",
    response_model=LivenessResponse,
    status_code=status.HTTP_200_OK,
)
async def get_liveness(
    health_service: HealthService = Depends(get_health_service_from_request_dependency),
) -> LivenessResponse:
    """Проверка жизнеспособности приложения."""

    return await health_service.get_liveness()


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
)
async def get_readiness(
    response: Response,
    health_service: HealthService = Depends(get_health_service_from_request_dependency),
) -> ReadinessResponse:
    """Проверка готовности приложения к приёму запросов."""

    readiness = await health_service.get_readiness(check_storage_read_write=True)
    if not readiness.ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return readiness


@router.get(
    "/",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
)
async def get_health_check(
    response: Response,
    health_service: HealthService = Depends(get_health_service_from_request_dependency),
) -> HealthCheckResponse:
    """Общая проверка состояния приложения."""

    health = await health_service.get_health_check()
    if not _is_ok(health.status):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return health


@router.get(
    "/database",
    response_model=DatabaseHealthRead,
    status_code=status.HTTP_200_OK,
)
async def get_database_health(
    response: Response,
    _: CurrentAdminUserDependency,
    health_service: HealthService = Depends(get_health_service_from_request_dependency),
) -> DatabaseHealthRead:
    """Проверка состояния базы данных (только для администратора)."""

    health = await health_service.get_health_check(
        check_database=True,
        check_storage=False,
        check_storage_read_write=False,
    )
    database = health.database
    if database is None:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return DatabaseHealthRead(
            component="database",
            status=HealthStatus.UNAVAILABLE,
            connection=False,
            message="Проверка базы данных недоступна.",
        )
    if not _is_ok(database.status):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return database


@router.get(
    "/storage",
    response_model=StorageHealthRead,
    status_code=status.HTTP_200_OK,
)
async def get_storage_health(
    response: Response,
    _: CurrentAdminUserDependency,
    health_service: HealthService = Depends(get_health_service_from_request_dependency),
) -> StorageHealthRead:
    """Проверка состояния объектного хранилища (только для администратора)."""

    health = await health_service.get_health_check(
        check_database=False,
        check_storage=True,
        check_storage_read_write=True,
    )
    storage = health.storage
    if storage is None:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return StorageHealthRead(
            component="storage",
            status=HealthStatus.UNAVAILABLE,
            connection_ok=False,
            details={"reason": "Проверка хранилища недоступна."},
        )
    if not _is_ok(storage.status):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return storage


__all__ = ["router"]
