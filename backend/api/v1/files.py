"""Эндпоинты для работы с файлами пользователя.

Модуль содержит маршрутизатор FastAPI для получения, поиска, обновления,
переименования, перемещения и скачивания файлов текущего пользователя.
Также предоставляет эндпоинты для получения состояния предпросмотра файла,
просмотра списка версий и восстановления выбранной версии файла.

Все маршруты модуля требуют текущего активного пользователя и выполняют
операции в контексте его прав доступа.

Attributes:
    router: Маршрутизатор FastAPI с префиксом `/files` и тегом `files`.
"""


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

# Маршрутизатор эндпоинтов для работы с файлами.
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
    """Возвращает список файлов текущего пользователя.

    Создаёт поисковый запрос с ограничением по владельцу и возвращает страницу
    файлов, принадлежащих текущему пользователю.

    Args:
        current_user: Текущий активный пользователь, для которого нужно
            получить список файлов.
        files_service: Сервис файлов, выполняющий поиск и проверку доступа.

    Returns:
        Страница файлов текущего пользователя с метаданными пагинации.

    Raises:
        HTTPException: Если пользователь не аутентифицирован, неактивен
            или доступ к ресурсу запрещён.
    """

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
    """Выполняет поиск файлов для текущего пользователя.

    Ищет файлы по переданным параметрам фильтрации, сортировки и пагинации
    с учётом прав доступа текущего пользователя.

    Args:
        current_user: Текущий активный пользователь, от имени которого
            выполняется поиск.
        params: Параметры поиска файлов.
        files_service: Сервис файлов, выполняющий поиск и проверку доступа.

    Returns:
        Страница найденных файлов с метаданными пагинации.

    Raises:
        HTTPException: Если пользователь не аутентифицирован, неактивен,
            параметры поиска некорректны или доступ запрещён.
    """

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
    """Возвращает файл по идентификатору.

    Получает подробные данные файла, если текущий пользователь имеет доступ
    к указанному файлу.

    Args:
        current_user: Текущий активный пользователь, запрашивающий файл.
        file_id: Уникальный идентификатор файла.
        files_service: Сервис файлов, выполняющий получение файла и проверку
            доступа.

    Returns:
        Подробные данные файла.

    Raises:
        HTTPException: Если пользователь не аутентифицирован, файл не найден
            или доступ к нему запрещён.
    """

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
    """Обновляет метаданные файла.

    Сначала получает файл по публичному идентификатору с проверкой доступа,
    затем обновляет его метаданные по внутреннему идентификатору узла.

    Args:
        data: Новые значения метаданных файла.
        current_user: Текущий активный пользователь, выполняющий обновление.
        file_id: Уникальный идентификатор файла.
        files_service: Сервис файлов, выполняющий получение и обновление файла.

    Returns:
        Обновлённые данные файла.

    Raises:
        HTTPException: Если пользователь не аутентифицирован, файл не найден,
            доступ запрещён или переданные метаданные некорректны.
    """

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
    """Переименовывает файл.

    Сначала получает файл по публичному идентификатору с проверкой доступа,
    затем изменяет имя файла по внутреннему идентификатору узла.

    Args:
        data: Данные для переименования файла.
        current_user: Текущий активный пользователь, выполняющий переименование.
        file_id: Уникальный идентификатор файла.
        files_service: Сервис файлов, выполняющий получение и переименование
            файла.

    Returns:
        Данные файла после переименования.

    Raises:
        HTTPException: Если пользователь не аутентифицирован, файл не найден,
            доступ запрещён или новое имя файла некорректно.
    """

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
    """Перемещает файл.

    Сначала получает файл по публичному идентификатору с проверкой доступа,
    затем переносит его в указанное место по внутреннему идентификатору узла.

    Args:
        data: Данные для перемещения файла, включая целевое расположение.
        current_user: Текущий активный пользователь, выполняющий перемещение.
        file_id: Уникальный идентификатор файла.
        files_service: Сервис файлов, выполняющий получение и перемещение файла.

    Returns:
        Данные файла после перемещения.

    Raises:
        HTTPException: Если пользователь не аутентифицирован, файл или целевое
            расположение не найдены, доступ запрещён либо перемещение невозможно.
    """

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
    """Создаёт ссылку для скачивания файла.

    Дополняет данные запроса идентификатором файла из URL и создаёт временную
    или подписанную ссылку для скачивания с учётом прав текущего пользователя.

    Args:
        data: Параметры создания ссылки для скачивания.
        current_user: Текущий активный пользователь, запрашивающий скачивание.
        file_id: Уникальный идентификатор файла.
        downloads_service: Сервис скачиваний, создающий ссылку на файл.

    Returns:
        Данные ссылки для скачивания файла.

    Raises:
        HTTPException: Если пользователь не аутентифицирован, файл не найден,
            доступ запрещён или ссылка для скачивания не может быть создана.
    """

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
    """Возвращает состояние предпросмотра файла.

    Получает файл по публичному идентификатору с проверкой доступа, затем
    возвращает информацию о доступности и состоянии предпросмотра по внутреннему
    идентификатору узла.

    Args:
        current_user: Текущий активный пользователь, запрашивающий предпросмотр.
        file_id: Уникальный идентификатор файла.
        files_service: Сервис файлов, выполняющий получение файла и данных
            предпросмотра.

    Returns:
        Данные состояния предпросмотра файла.

    Raises:
        HTTPException: Если пользователь не аутентифицирован, файл не найден,
            доступ запрещён или предпросмотр недоступен.
    """

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
    """Возвращает список версий файла.

    Получает файл по публичному идентификатору с проверкой доступа, затем
    возвращает страницу версий файла по внутреннему идентификатору узла.

    Args:
        current_user: Текущий активный пользователь, запрашивающий версии.
        file_id: Уникальный идентификатор файла.
        files_service: Сервис файлов, выполняющий получение файла и списка
            версий.

    Returns:
        Страница версий файла с метаданными пагинации.

    Raises:
        HTTPException: Если пользователь не аутентифицирован, файл не найден
            или доступ к версиям файла запрещён.
    """

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
    """Восстанавливает выбранную версию файла.

    Получает файл по публичному идентификатору с проверкой доступа, дополняет
    данные запроса идентификатором версии из URL и восстанавливает указанную
    версию файла по внутреннему идентификатору узла.

    Args:
        data: Параметры восстановления версии файла.
        current_user: Текущий активный пользователь, выполняющий восстановление.
        file_id: Уникальный идентификатор файла.
        version_id: Уникальный идентификатор версии, которую нужно восстановить.
        files_service: Сервис файлов, выполняющий получение файла и
            восстановление версии.

    Returns:
        Данные восстановленной версии или данные файла после восстановления.

    Raises:
        HTTPException: Если пользователь не аутентифицирован, файл или версия
            не найдены, доступ запрещён либо восстановление версии невозможно.
    """

    file_read = await files_service.get_file_by_id(file_id, user_id=current_user.id)
    request_data = data.model_copy(update={"version_id": version_id})
    return await files_service.restore_version(
        file_read.node_id,
        request_data,
        actor_id=current_user.id,
    )


__all__ = ["router"]
