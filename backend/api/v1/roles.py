from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status

from api.dependencies import get_roles_service_dependency
from schemas.common import MessageResponse, PageResponse
from schemas.roles import (
    RoleAssignRequest,
    RoleCreate,
    RoleListItem,
    RoleRead,
    RoleRemoveRequest,
    RoleUpdate,
    UserRoleRead,
)
from security import CurrentAdminUserDependency
from services import RolesService

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get(
    "/",
    response_model=PageResponse[RoleListItem],
    status_code=status.HTTP_200_OK,
)
async def list_roles(
    _: CurrentAdminUserDependency,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    only_active: bool | None = Query(default=None),
    only_system: bool | None = Query(default=None),
    search: str | None = Query(default=None),
    roles_service: RolesService = Depends(get_roles_service_dependency),
) -> PageResponse[RoleListItem]:
    """Возвращает список ролей."""

    return await roles_service.list_roles(
        offset=offset,
        limit=limit,
        only_active=only_active,
        only_system=only_system,
        search=search,
        order_by_name=True,
    )


@router.post(
    "/",
    response_model=RoleRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_role(
    data: RoleCreate,
    admin_user: CurrentAdminUserDependency,
    roles_service: RolesService = Depends(get_roles_service_dependency),
) -> RoleRead:
    """Создаёт новую роль."""

    return await roles_service.create_role(data, actor_id=admin_user.id)


@router.get(
    "/{role_id}",
    response_model=RoleRead,
    status_code=status.HTTP_200_OK,
)
async def get_role(
    _: CurrentAdminUserDependency,
    role_id: UUID = Path(...),
    roles_service: RolesService = Depends(get_roles_service_dependency),
) -> RoleRead:
    """Возвращает роль по идентификатору."""

    return await roles_service.get_role(role_id)


@router.patch(
    "/{role_id}",
    response_model=RoleRead,
    status_code=status.HTTP_200_OK,
)
async def update_role(
    data: RoleUpdate,
    admin_user: CurrentAdminUserDependency,
    role_id: UUID = Path(...),
    roles_service: RolesService = Depends(get_roles_service_dependency),
) -> RoleRead:
    """Обновляет роль."""

    return await roles_service.update_role(
        role_id,
        data,
        actor_id=admin_user.id,
    )


@router.delete(
    "/{role_id}",
    response_model=RoleRead,
    status_code=status.HTTP_200_OK,
)
async def delete_role(
    admin_user: CurrentAdminUserDependency,
    role_id: UUID = Path(...),
    roles_service: RolesService = Depends(get_roles_service_dependency),
) -> RoleRead:
    """Деактивирует роль."""

    return await roles_service.deactivate_role(
        role_id,
        actor_id=admin_user.id,
    )


@router.post(
    "/assign",
    response_model=UserRoleRead,
    status_code=status.HTTP_200_OK,
)
async def assign_role(
    data: RoleAssignRequest,
    admin_user: CurrentAdminUserDependency,
    roles_service: RolesService = Depends(get_roles_service_dependency),
) -> UserRoleRead:
    """Назначает роль пользователю."""

    return await roles_service.assign_role(data, actor_id=admin_user.id)


@router.post(
    "/remove",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def remove_role(
    data: RoleRemoveRequest,
    admin_user: CurrentAdminUserDependency,
    roles_service: RolesService = Depends(get_roles_service_dependency),
) -> MessageResponse:
    """Снимает роль с пользователя."""

    removed = await roles_service.remove_role(data, actor_id=admin_user.id)
    if removed:
        message = "Роль снята с пользователя."
    else:
        message = "Назначение роли не найдено."
    return MessageResponse(message=message)


@router.get(
    "/users/{user_id}",
    response_model=list[UserRoleRead],
    status_code=status.HTTP_200_OK,
)
async def get_user_roles(
    _: CurrentAdminUserDependency,
    user_id: UUID = Path(...),
    roles_service: RolesService = Depends(get_roles_service_dependency),
) -> list[UserRoleRead]:
    """Возвращает назначения ролей пользователя."""

    return await roles_service.get_user_role_assignments(user_id)


__all__ = ["router"]
