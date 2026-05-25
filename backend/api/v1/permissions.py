from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status

from api.dependencies import get_permissions_service_dependency
from schemas.common import PageResponse
from schemas.permissions import (
    EffectivePermissionRead,
    NodePermissionListItem,
    NodePermissionRead,
    NodePermissionUpdate,
    PermissionCheckRequest,
    PermissionCheckResponse,
    PermissionGrantRequest,
    PermissionRevokeRequest,
    PermissionUpdateRequest,
)
from security import CurrentActiveUserDependency, RequireShareNodeDependency
from services import PermissionsService

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get(
    "/nodes/{node_id}",
    response_model=PageResponse[NodePermissionListItem],
    status_code=status.HTTP_200_OK,
)
async def list_node_permissions(
    current_user: CurrentActiveUserDependency,
    _: None = RequireShareNodeDependency,
    node_id: UUID = Path(...),
    active_only: bool = Query(default=False),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    permissions_service: PermissionsService = Depends(get_permissions_service_dependency),
) -> PageResponse[NodePermissionListItem]:
    """Возвращает список прав доступа для узла."""

    return await permissions_service.list_node_permissions(
        node_id=node_id,
        actor_id=current_user.id,
        active_only=active_only,
        offset=offset,
        limit=limit,
    )


@router.post(
    "/grant",
    response_model=NodePermissionRead,
    status_code=status.HTTP_201_CREATED,
)
async def grant_permission(
    data: PermissionGrantRequest,
    current_user: CurrentActiveUserDependency,
    permissions_service: PermissionsService = Depends(get_permissions_service_dependency),
) -> NodePermissionRead:
    """Выдаёт право доступа к узлу."""

    return await permissions_service.grant_permission(data, actor_id=current_user.id)


@router.patch(
    "/{permission_id}",
    response_model=NodePermissionRead,
    status_code=status.HTTP_200_OK,
)
async def update_permission(
    data: PermissionUpdateRequest | NodePermissionUpdate,
    current_user: CurrentActiveUserDependency,
    permission_id: UUID = Path(...),
    permissions_service: PermissionsService = Depends(get_permissions_service_dependency),
) -> NodePermissionRead:
    """Обновляет выданное право доступа."""

    request_data = PermissionUpdateRequest(
        permission_id=permission_id,
        permission_level=data.permission_level,
        can_read=data.can_read,
        can_download=data.can_download,
        can_write=data.can_write,
        can_delete=data.can_delete,
        can_share=data.can_share,
        expires_at=data.expires_at,
    )
    return await permissions_service.update_permission(
        request_data,
        actor_id=current_user.id,
    )


@router.post(
    "/revoke",
    response_model=NodePermissionRead,
    status_code=status.HTTP_200_OK,
)
async def revoke_permission(
    data: PermissionRevokeRequest,
    current_user: CurrentActiveUserDependency,
    permissions_service: PermissionsService = Depends(get_permissions_service_dependency),
) -> NodePermissionRead:
    """Отзывает ранее выданное право доступа."""

    return await permissions_service.revoke_permission(data, actor_id=current_user.id)


@router.post(
    "/check",
    response_model=PermissionCheckResponse,
    status_code=status.HTTP_200_OK,
)
async def check_permission(
    data: PermissionCheckRequest,
    permissions_service: PermissionsService = Depends(get_permissions_service_dependency),
) -> PermissionCheckResponse:
    """Проверяет, разрешено ли действие над узлом."""

    return await permissions_service.check_permission(data)


@router.get(
    "/nodes/{node_id}/effective",
    response_model=EffectivePermissionRead,
    status_code=status.HTTP_200_OK,
)
async def get_effective_permissions(
    current_user: CurrentActiveUserDependency,
    node_id: UUID = Path(...),
    allow_deleted: bool = Query(default=False),
    allow_public: bool = Query(default=True),
    permissions_service: PermissionsService = Depends(get_permissions_service_dependency),
) -> EffectivePermissionRead:
    """Возвращает эффективные права текущего пользователя на узел."""

    return await permissions_service.get_effective_permissions(
        node_id=node_id,
        user_id=current_user.id,
        allow_deleted=allow_deleted,
        allow_public=allow_public,
    )


__all__ = ["router"]
