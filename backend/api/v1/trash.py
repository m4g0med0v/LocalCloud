from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path, status

from api.dependencies import get_trash_service_dependency
from schemas.common import PageResponse
from schemas.trash import (
    TrashCleanupRequest,
    TrashEmptyRequest,
    TrashItemListItem,
    TrashPurgeRequest,
    TrashPurgeResponse,
    TrashQueryParams,
    TrashRestoreRequest,
    TrashRestoreResponse,
)
from security import CurrentActiveUserDependency, CurrentAdminUserDependency
from services import TrashService

router = APIRouter(prefix="/trash", tags=["trash"])


@router.get(
    "/",
    response_model=PageResponse[TrashItemListItem],
    status_code=status.HTTP_200_OK,
)
async def list_trash_items(
    current_user: CurrentActiveUserDependency,
    params: TrashQueryParams = Depends(),
    trash_service: TrashService = Depends(get_trash_service_dependency),
) -> PageResponse[TrashItemListItem]:
    """Возвращает список элементов корзины."""

    return await trash_service.list_trash(params, actor_id=current_user.id)


@router.post(
    "/{trash_item_id}/restore",
    response_model=TrashRestoreResponse,
    status_code=status.HTTP_200_OK,
)
async def restore_trash_item(
    data: TrashRestoreRequest,
    current_user: CurrentActiveUserDependency,
    trash_item_id: UUID = Path(...),
    trash_service: TrashService = Depends(get_trash_service_dependency),
) -> TrashRestoreResponse:
    """Восстанавливает элемент из корзины."""

    request_data = data.model_copy(update={"trash_item_id": trash_item_id})
    return await trash_service.restore(request_data, actor_id=current_user.id)


@router.post(
    "/{trash_item_id}/purge",
    response_model=TrashPurgeResponse,
    status_code=status.HTTP_200_OK,
)
async def purge_trash_item(
    data: TrashPurgeRequest,
    current_user: CurrentActiveUserDependency,
    trash_item_id: UUID = Path(...),
    trash_service: TrashService = Depends(get_trash_service_dependency),
) -> TrashPurgeResponse:
    """Окончательно удаляет элемент из корзины."""

    request_data = data.model_copy(
        update={"trash_item_ids": [trash_item_id], "node_ids": None}
    )
    return await trash_service.purge(request_data, actor_id=current_user.id)


@router.post(
    "/empty",
    response_model=TrashPurgeResponse,
    status_code=status.HTTP_200_OK,
)
async def empty_trash(
    data: TrashEmptyRequest,
    current_user: CurrentActiveUserDependency,
    trash_service: TrashService = Depends(get_trash_service_dependency),
) -> TrashPurgeResponse:
    """Очищает корзину пользователя."""

    return await trash_service.empty_trash(data, actor_id=current_user.id)


@router.post(
    "/cleanup",
    response_model=TrashPurgeResponse,
    status_code=status.HTTP_200_OK,
)
async def cleanup_trash(
    data: TrashCleanupRequest,
    current_admin: CurrentAdminUserDependency,
    trash_service: TrashService = Depends(get_trash_service_dependency),
) -> TrashPurgeResponse:
    """Запускает очистку устаревших элементов корзины."""

    return await trash_service.cleanup_expired(data, actor_id=current_admin.id)


__all__ = ["router"]
