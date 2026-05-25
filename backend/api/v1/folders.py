from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path, status

from api.dependencies import get_folders_service_dependency
from schemas.folders import (
    FolderArchiveRequest,
    FolderArchiveResponse,
    FolderContentRead,
    FolderCreateRequest,
    FolderRead,
    FolderUpdateRequest,
)
from security import CurrentActiveUserDependency
from services import FoldersService

router = APIRouter(prefix="/folders", tags=["folders"])


@router.post(
    "/",
    response_model=FolderRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_folder(
    data: FolderCreateRequest,
    current_user: CurrentActiveUserDependency,
    folders_service: FoldersService = Depends(get_folders_service_dependency),
) -> FolderRead:
    """Создаёт новую папку."""

    return await folders_service.create_folder(
        data,
        owner_id=current_user.id,
        actor_id=current_user.id,
    )


@router.get(
    "/{folder_id}",
    response_model=FolderRead,
    status_code=status.HTTP_200_OK,
)
async def get_folder(
    current_user: CurrentActiveUserDependency,
    folder_id: UUID = Path(...),
    folders_service: FoldersService = Depends(get_folders_service_dependency),
) -> FolderRead:
    """Возвращает папку по идентификатору."""

    return await folders_service.get_folder(
        folder_id,
        user_id=current_user.id,
    )


@router.patch(
    "/{folder_id}",
    response_model=FolderRead,
    status_code=status.HTTP_200_OK,
)
async def update_folder(
    data: FolderUpdateRequest,
    current_user: CurrentActiveUserDependency,
    folder_id: UUID = Path(...),
    folders_service: FoldersService = Depends(get_folders_service_dependency),
) -> FolderRead:
    """Обновляет метаданные папки."""

    return await folders_service.update_folder(
        folder_id,
        data,
        actor_id=current_user.id,
    )


@router.get(
    "/{folder_id}/content",
    response_model=FolderContentRead,
    status_code=status.HTTP_200_OK,
)
async def get_folder_content(
    current_user: CurrentActiveUserDependency,
    folder_id: UUID = Path(...),
    folders_service: FoldersService = Depends(get_folders_service_dependency),
) -> FolderContentRead:
    """Возвращает содержимое папки."""

    return await folders_service.get_folder_content(
        folder_id,
        user_id=current_user.id,
    )


@router.post(
    "/{folder_id}/archive",
    response_model=FolderArchiveResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_folder_archive(
    data: FolderArchiveRequest,
    current_user: CurrentActiveUserDependency,
    folder_id: UUID = Path(...),
    folders_service: FoldersService = Depends(get_folders_service_dependency),
) -> FolderArchiveResponse:
    """Создаёт фоновую задачу на архивацию папки."""

    request_data = data.model_copy(update={"folder_id": folder_id})
    return await folders_service.request_folder_archive(
        request_data,
        actor_id=current_user.id,
    )


__all__ = ["router"]
