from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path, status

from api.dependencies import get_registration_service_dependency
from schemas.common import PageResponse
from schemas.registration import (
    RegistrationApproveRequest,
    RegistrationCancelRequest,
    RegistrationDecisionResponse,
    RegistrationQueryParams,
    RegistrationRejectRequest,
    RegistrationRequestCreate,
    RegistrationRequestListItem,
    RegistrationRequestRead,
)
from security import CurrentAdminUserDependency, OptionalCurrentUserDependency
from services import RegistrationService

router = APIRouter(prefix="/registration", tags=["registration"])


@router.post(
    "/requests",
    response_model=RegistrationRequestRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_registration_request(
    data: RegistrationRequestCreate,
    registration_service: RegistrationService = Depends(get_registration_service_dependency),
) -> RegistrationRequestRead:
    """Создаёт новую заявку на регистрацию."""

    return await registration_service.submit_request(data)


@router.get(
    "/requests",
    response_model=PageResponse[RegistrationRequestListItem],
    status_code=status.HTTP_200_OK,
)
async def list_registration_requests(
    _: CurrentAdminUserDependency,
    params: RegistrationQueryParams = Depends(),
    registration_service: RegistrationService = Depends(get_registration_service_dependency),
) -> PageResponse[RegistrationRequestListItem]:
    """Возвращает список заявок на регистрацию для администратора."""

    return await registration_service.list_requests(params)


@router.get(
    "/requests/{request_id}",
    response_model=RegistrationRequestRead,
    status_code=status.HTTP_200_OK,
)
async def get_registration_request(
    _: CurrentAdminUserDependency,
    request_id: UUID = Path(...),
    registration_service: RegistrationService = Depends(get_registration_service_dependency),
) -> RegistrationRequestRead:
    """Возвращает заявку на регистрацию по идентификатору."""

    return await registration_service.get_request(request_id)


@router.post(
    "/requests/{request_id}/approve",
    response_model=RegistrationDecisionResponse,
    status_code=status.HTTP_200_OK,
)
async def approve_registration_request(
    data: RegistrationApproveRequest,
    admin_user: CurrentAdminUserDependency,
    request_id: UUID = Path(...),
    registration_service: RegistrationService = Depends(get_registration_service_dependency),
) -> RegistrationDecisionResponse:
    """Одобряет заявку на регистрацию."""

    return await registration_service.approve_request(
        request_id,
        data,
        reviewed_by=admin_user.id,
    )


@router.post(
    "/requests/{request_id}/reject",
    response_model=RegistrationDecisionResponse,
    status_code=status.HTTP_200_OK,
)
async def reject_registration_request(
    data: RegistrationRejectRequest,
    admin_user: CurrentAdminUserDependency,
    request_id: UUID = Path(...),
    registration_service: RegistrationService = Depends(get_registration_service_dependency),
) -> RegistrationDecisionResponse:
    """Отклоняет заявку на регистрацию."""

    return await registration_service.reject_request(
        request_id,
        data,
        reviewed_by=admin_user.id,
    )


@router.post(
    "/requests/{request_id}/cancel",
    response_model=RegistrationDecisionResponse,
    status_code=status.HTTP_200_OK,
)
async def cancel_registration_request(
    data: RegistrationCancelRequest,
    request_id: UUID = Path(...),
    current_user: OptionalCurrentUserDependency = None,
    registration_service: RegistrationService = Depends(get_registration_service_dependency),
) -> RegistrationDecisionResponse:
    """Отменяет заявку на регистрацию."""

    _ = current_user
    return await registration_service.cancel_request(request_id, data)


__all__ = ["router"]
