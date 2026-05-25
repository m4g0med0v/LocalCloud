from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path, status

from api.dependencies import get_users_service_dependency
from schemas.common import PageResponse
from schemas.users import (
    CurrentUserRead,
    UserAdminUpdate,
    UserApproveRequest,
    UserBlockRequest,
    UserListItem,
    UserQueryParams,
    UserRead,
    UserRejectRequest,
    UserUpdate,
    UserWithRolesRead,
)
from security import CurrentActiveUserDependency, CurrentAdminUserDependency
from services import UsersService

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=CurrentUserRead,
    status_code=status.HTTP_200_OK,
)
async def get_me(
    current_user: CurrentActiveUserDependency,
    users_service: UsersService = Depends(get_users_service_dependency),
) -> CurrentUserRead:
    """Возвращает профиль текущего активного пользователя."""

    return await users_service.get_current_user_read(current_user.id)


@router.patch(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
)
async def update_me(
    data: UserUpdate,
    current_user: CurrentActiveUserDependency,
    users_service: UsersService = Depends(get_users_service_dependency),
) -> UserRead:
    """Обновляет данные текущего активного пользователя."""

    return await users_service.update_user(
        current_user.id,
        data,
        actor_id=current_user.id,
    )


@router.get(
    "/",
    response_model=PageResponse[UserListItem],
    status_code=status.HTTP_200_OK,
)
async def list_users(
    _: CurrentAdminUserDependency,
    params: UserQueryParams = Depends(),
    users_service: UsersService = Depends(get_users_service_dependency),
) -> PageResponse[UserListItem]:
    """Возвращает список пользователей для администратора."""

    return await users_service.list_users(params)


@router.get(
    "/{user_id}",
    response_model=UserWithRolesRead,
    status_code=status.HTTP_200_OK,
)
async def get_user(
    _: CurrentAdminUserDependency,
    user_id: UUID = Path(...),
    users_service: UsersService = Depends(get_users_service_dependency),
) -> UserWithRolesRead:
    """Возвращает пользователя с ролями для администратора."""

    return await users_service.get_user_with_roles(user_id)


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
)
async def admin_update_user(
    data: UserAdminUpdate,
    admin_user: CurrentAdminUserDependency,
    user_id: UUID = Path(...),
    users_service: UsersService = Depends(get_users_service_dependency),
) -> UserRead:
    """Административно обновляет пользователя."""

    return await users_service.admin_update_user(
        user_id,
        data,
        actor_id=admin_user.id,
    )


@router.post(
    "/{user_id}/block",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
)
async def block_user(
    data: UserBlockRequest,
    admin_user: CurrentAdminUserDependency,
    user_id: UUID = Path(...),
    users_service: UsersService = Depends(get_users_service_dependency),
) -> UserRead:
    """Блокирует пользователя."""

    return await users_service.block_user(
        user_id,
        data,
        actor_id=admin_user.id,
    )


@router.post(
    "/{user_id}/unblock",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
)
async def unblock_user(
    admin_user: CurrentAdminUserDependency,
    user_id: UUID = Path(...),
    users_service: UsersService = Depends(get_users_service_dependency),
) -> UserRead:
    """Разблокирует пользователя."""

    return await users_service.unblock_user(
        user_id,
        actor_id=admin_user.id,
    )


@router.post(
    "/{user_id}/approve",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
)
async def approve_user(
    data: UserApproveRequest,
    admin_user: CurrentAdminUserDependency,
    user_id: UUID = Path(...),
    users_service: UsersService = Depends(get_users_service_dependency),
) -> UserRead:
    """Одобряет пользователя."""

    return await users_service.approve_user(
        user_id,
        actor_id=admin_user.id,
        is_email_verified=data.is_email_verified,
    )


@router.post(
    "/{user_id}/reject",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
)
async def reject_user(
    data: UserRejectRequest,
    admin_user: CurrentAdminUserDependency,
    user_id: UUID = Path(...),
    users_service: UsersService = Depends(get_users_service_dependency),
) -> UserRead:
    """Отклоняет пользователя."""

    return await users_service.reject_user(
        user_id,
        data,
        actor_id=admin_user.id,
    )


@router.delete(
    "/{user_id}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
)
async def delete_user(
    admin_user: CurrentAdminUserDependency,
    user_id: UUID = Path(...),
    users_service: UsersService = Depends(get_users_service_dependency),
) -> UserRead:
    """Выполняет soft-delete пользователя."""

    return await users_service.delete_user(
        user_id,
        actor_id=admin_user.id,
    )


__all__ = ["router"]
