from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status

from api.dependencies import get_quotas_service_dependency
from schemas.quotas import (
    QuotaCheckRequest,
    QuotaCheckResponse,
    QuotaRecalculateRequest,
    QuotaUsageRead,
    UserQuotaCreate,
    UserQuotaRead,
    UserQuotaUpdate,
)
from security import CurrentActiveUserDependency, CurrentAdminUserDependency
from services import QuotasService

router = APIRouter(prefix="/quotas", tags=["quotas"])


@router.get(
    "/me",
    response_model=QuotaUsageRead,
    status_code=status.HTTP_200_OK,
)
async def get_my_quota_usage(
    current_user: CurrentActiveUserDependency,
    quotas_service: QuotasService = Depends(get_quotas_service_dependency),
) -> QuotaUsageRead:
    """Возвращает квоту и текущее использование ресурсов пользователя."""

    return await quotas_service.get_usage(current_user.id)


@router.get(
    "/users/{user_id}",
    response_model=QuotaUsageRead,
    status_code=status.HTTP_200_OK,
)
async def get_user_quota_usage(
    _: CurrentAdminUserDependency,
    user_id: UUID = Path(...),
    quotas_service: QuotasService = Depends(get_quotas_service_dependency),
) -> QuotaUsageRead:
    """Возвращает квоту и использование ресурсов указанного пользователя."""

    return await quotas_service.get_usage(user_id)


@router.put(
    "/users/{user_id}",
    response_model=UserQuotaRead,
    status_code=status.HTTP_200_OK,
)
async def upsert_user_quota(
    data: UserQuotaUpdate | UserQuotaCreate,
    admin_user: CurrentAdminUserDependency,
    user_id: UUID = Path(...),
    quotas_service: QuotasService = Depends(get_quotas_service_dependency),
) -> UserQuotaRead:
    """Создаёт или обновляет квоту пользователя."""

    if isinstance(data, UserQuotaCreate):
        if data.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id в пути и в теле запроса должны совпадать.",
            )
        return await quotas_service.create_quota(data, actor_id=admin_user.id)

    return await quotas_service.update_quota(
        user_id,
        data,
        actor_id=admin_user.id,
    )


@router.post(
    "/check",
    response_model=QuotaCheckResponse,
    status_code=status.HTTP_200_OK,
)
async def check_quota(
    data: QuotaCheckRequest,
    current_user: CurrentActiveUserDependency,
    quotas_service: QuotasService = Depends(get_quotas_service_dependency),
) -> QuotaCheckResponse:
    """Проверяет возможность расходования квоты для текущего пользователя."""

    request_data = data.model_copy(update={"user_id": current_user.id})
    return await quotas_service.check_quota(request_data)


@router.post(
    "/recalculate",
    response_model=UserQuotaRead,
    status_code=status.HTTP_200_OK,
)
async def recalculate_quota(
    data: QuotaRecalculateRequest,
    admin_user: CurrentAdminUserDependency,
    quotas_service: QuotasService = Depends(get_quotas_service_dependency),
) -> UserQuotaRead:
    """Запускает пересчёт квоты через сервисный слой."""

    return await quotas_service.recalculate_quota(
        data,
        actor_id=admin_user.id,
    )


__all__ = ["router"]
