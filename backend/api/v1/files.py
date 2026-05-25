from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path, status

from api.dependencies import (
    get_downloads_service_dependency,
    get_files_service_dependency,
)
from schemas.common import PageResponse
from schemas.files import (
    FileDownloadRequest,
    FileDownloadResponse,
    FileListItem,
    FileMoveRequest,
    FilePreviewRead,
    FileRead,
    FileRenameRequest,
    FileSearchQuery,
    FileUpdateRequest,
    FileVersionListItem,
    FileVersionRead,
    FileVersionRestoreRequest,
)
from security import CurrentActiveUserDependency
from services import DownloadsService, FilesService

router = APIRouter(prefix="/files", tags=["files"])


@router.get(
    "/",
    response_model=PageResponse[FileListItem],
    status_code=status.HTTP_200_OK,
)
async def list_files(
    current_user: CurrentActiveUserDependency,
    files_service: FilesService = Depends(get_files_service_dependency),
) -> PageResponse[FileListItem]:
    """Возвращает список файлов текущего пользователя."""

    params = FileSearchQuery(owner_id=current_user.id)
    return await files_service.search_files(params, user_id=current_user.id)


@router.get(
    "/search",
    response_model=PageResponse[FileListItem],
    status_code=status.HTTP_200_OK,
)
async def search_files(
    current_user: CurrentActiveUserDependency,
    params: FileSearchQuery = Depends(),
    files_service: FilesService = Depends(get_files_service_dependency),
) -> PageResponse[FileListItem]:
    """Выполняет поиск файлов."""

    return await files_service.search_files(params, user_id=current_user.id)


@router.get(
    "/{file_id}",
    response_model=FileRead,
    status_code=status.HTTP_200_OK,
)
async def get_file(
    current_user: CurrentActiveUserDependency,
    file_id: UUID = Path(...),
    files_service: FilesService = Depends(get_files_service_dependency),
) -> FileRead:
    """Возвращает файл по идентификатору."""

    return await files_service.get_file_by_id(file_id, user_id=current_user.id)


@router.patch(
    "/{file_id}",
    response_model=FileRead,
    status_code=status.HTTP_200_OK,
)
async def update_file(
    data: FileUpdateRequest,
    current_user: CurrentActiveUserDependency,
    file_id: UUID = Path(...),
    files_service: FilesService = Depends(get_files_service_dependency),
) -> FileRead:
    """Обновляет метаданные файла."""

    file_read = await files_service.get_file_by_id(file_id, user_id=current_user.id)
    return await files_service.update_file(
        file_read.node_id,
        data,
        actor_id=current_user.id,
    )


@router.post(
    "/{file_id}/rename",
    response_model=FileRead,
    status_code=status.HTTP_200_OK,
)
async def rename_file(
    data: FileRenameRequest,
    current_user: CurrentActiveUserDependency,
    file_id: UUID = Path(...),
    files_service: FilesService = Depends(get_files_service_dependency),
) -> FileRead:
    """Переименовывает файл."""

    file_read = await files_service.get_file_by_id(file_id, user_id=current_user.id)
    return await files_service.rename_file(
        file_read.node_id,
        data,
        actor_id=current_user.id,
    )


@router.post(
    "/{file_id}/move",
    response_model=FileRead,
    status_code=status.HTTP_200_OK,
)
async def move_file(
    data: FileMoveRequest,
    current_user: CurrentActiveUserDependency,
    file_id: UUID = Path(...),
    files_service: FilesService = Depends(get_files_service_dependency),
) -> FileRead:
    """Перемещает файл."""

    file_read = await files_service.get_file_by_id(file_id, user_id=current_user.id)
    return await files_service.move_file(
        file_read.node_id,
        data,
        actor_id=current_user.id,
    )


@router.post(
    "/{file_id}/download",
    response_model=FileDownloadResponse,
    status_code=status.HTTP_200_OK,
)
async def download_file(
    data: FileDownloadRequest,
    current_user: CurrentActiveUserDependency,
    file_id: UUID = Path(...),
    downloads_service: DownloadsService = Depends(get_downloads_service_dependency),
) -> FileDownloadResponse:
    """Возвращает ссылку для скачивания файла."""

    request_data = data.model_copy(update={"file_id": file_id})
    return await downloads_service.create_file_download_url(
        request_data,
        user_id=current_user.id,
    )


@router.get(
    "/{file_id}/preview",
    response_model=FilePreviewRead,
    status_code=status.HTTP_200_OK,
)
async def get_file_preview(
    current_user: CurrentActiveUserDependency,
    file_id: UUID = Path(...),
    files_service: FilesService = Depends(get_files_service_dependency),
) -> FilePreviewRead:
    """Возвращает состояние предпросмотра файла."""

    file_read = await files_service.get_file_by_id(file_id, user_id=current_user.id)
    return await files_service.get_preview(file_read.node_id, user_id=current_user.id)


@router.get(
    "/{file_id}/versions",
    response_model=PageResponse[FileVersionListItem],
    status_code=status.HTTP_200_OK,
)
async def list_file_versions(
    current_user: CurrentActiveUserDependency,
    file_id: UUID = Path(...),
    files_service: FilesService = Depends(get_files_service_dependency),
) -> PageResponse[FileVersionListItem]:
    """Возвращает список версий файла."""

    file_read = await files_service.get_file_by_id(file_id, user_id=current_user.id)
    return await files_service.list_versions(file_read.node_id, user_id=current_user.id)


@router.post(
    "/{file_id}/versions/{version_id}/restore",
    response_model=FileRead,
    status_code=status.HTTP_200_OK,
)
async def restore_file_version(
    data: FileVersionRestoreRequest,
    current_user: CurrentActiveUserDependency,
    file_id: UUID = Path(...),
    version_id: UUID = Path(...),
    files_service: FilesService = Depends(get_files_service_dependency),
) -> FileVersionRead | FileRead:
    """Восстанавливает выбранную версию файла."""

    file_read = await files_service.get_file_by_id(file_id, user_id=current_user.id)
    request_data = data.model_copy(update={"version_id": version_id})
    return await files_service.restore_version(
        file_read.node_id,
        request_data,
        actor_id=current_user.id,
    )


__all__ = ["router"]
