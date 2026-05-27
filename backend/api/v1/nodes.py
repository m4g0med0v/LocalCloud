"""Эндпоинты для работы с узлами файловой системы.

Модуль содержит маршрутизатор FastAPI для просмотра, поиска, обновления,
переименования, перемещения и удаления узлов файловой системы. Также
предоставляет эндпоинты для получения дерева узлов и хлебных крошек
для выбранного узла.

Под узлом может подразумеваться файл, папка или другой элемент файловой
структуры приложения. Все маршруты требуют текущего активного пользователя,
а операции чтения, записи и удаления дополнительно используют зависимости
проверки прав доступа к конкретному узлу.

Attributes:
    router: Маршрутизатор FastAPI с префиксом `/nodes` и тегом `nodes`.
"""


from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status

from api.dependencies import (
    get_downloads_service_dependency,
    get_files_service_dependency,
    get_folders_service_dependency,
    get_nodes_service_dependency,
)
from schemas.common import PageResponse
from schemas.files import FileDownloadRequest, FileDownloadResponse
from schemas.folders import FolderContentRead
from schemas.nodes import (
    NodeBreadcrumbItem,
    NodeListItem,
    NodeMoveRequest,
    NodeOperationResponse,
    NodeQueryParams,
    NodeRead,
    NodeRenameRequest,
    NodeSearchQuery,
    NodeTreeItem,
    NodeUpdate,
)
from security import (
    CurrentActiveUserDependency,
    RequireDeleteNodeDependency,
    RequireReadNodeDependency,
    RequireWriteNodeDependency,
)
from services import DownloadsService, FilesService, FoldersService, NodesService

# Маршрутизатор эндпоинтов для работы с узлами файловой системы.
router = APIRouter(prefix="/nodes", tags=["nodes"])


@router.get(
    "/",
    response_model=PageResponse[NodeListItem],
    status_code=status.HTTP_200_OK,
)
async def list_nodes(
    current_user: CurrentActiveUserDependency,
    params: NodeQueryParams = Depends(),
    nodes_service: NodesService = Depends(get_nodes_service_dependency),
) -> PageResponse[NodeListItem]:
    """Возвращает список узлов файловой системы.

    Получает страницу узлов с учётом параметров фильтрации, сортировки
    и пагинации. Результат ограничивается правами доступа текущего пользователя.

    Args:
        current_user: Текущий активный пользователь, запрашивающий список узлов.
        params: Параметры запроса для фильтрации, сортировки и пагинации узлов.
        nodes_service: Сервис узлов, выполняющий получение списка и проверку
            доступа.

    Returns:
        Страница узлов файловой системы с метаданными пагинации.

    Raises:
        HTTPException: Если пользователь не аутентифицирован, неактивен,
            параметры запроса некорректны или доступ запрещён.
    """

    return await nodes_service.list_nodes(params, user_id=current_user.id)


@router.get(
    "/tree",
    response_model=NodeTreeItem,
    status_code=status.HTTP_200_OK,
)
async def get_nodes_tree(
    current_user: CurrentActiveUserDependency,
    root_node_id: UUID = Query(...),
    include_deleted: bool = Query(default=False),
    nodes_service: NodesService = Depends(get_nodes_service_dependency),
) -> NodeTreeItem:
    """Возвращает дерево узлов от указанного корневого узла.

    Строит дерево файловой системы, начиная с переданного корневого узла.
    При необходимости может включать удалённые узлы, если это поддерживается
    сервисным слоем и разрешено правами пользователя.

    Args:
        current_user: Текущий активный пользователь, запрашивающий дерево.
        root_node_id: Уникальный идентификатор корневого узла дерева.
        include_deleted: Нужно ли включать soft-deleted узлы в результат.
        nodes_service: Сервис узлов, выполняющий построение дерева и проверку
            доступа.

    Returns:
        Дерево узлов файловой системы от указанного корневого узла.

    Raises:
        HTTPException: Если пользователь не аутентифицирован, корневой узел
            не найден, параметры запроса некорректны или доступ запрещён.
    """

    return await nodes_service.get_tree(
        root_node_id,
        user_id=current_user.id,
        include_deleted=include_deleted,
    )


@router.get(
    "/search",
    response_model=PageResponse[NodeListItem],
    status_code=status.HTTP_200_OK,
)
async def search_nodes(
    current_user: CurrentActiveUserDependency,
    params: NodeSearchQuery = Depends(),
    nodes_service: NodesService = Depends(get_nodes_service_dependency),
) -> PageResponse[NodeListItem]:
    """Выполняет поиск по узлам файловой системы.

    Ищет узлы по переданным параметрам поиска и возвращает страницу результатов.
    Поиск выполняется в контексте текущего пользователя и учитывает его права
    доступа к найденным узлам.

    Args:
        current_user: Текущий активный пользователь, выполняющий поиск.
        params: Параметры поиска узлов.
        nodes_service: Сервис узлов, выполняющий поиск и проверку доступа.

    Returns:
        Страница найденных узлов с метаданными пагинации.

    Raises:
        HTTPException: Если пользователь не аутентифицирован, неактивен,
            параметры поиска некорректны или доступ запрещён.
    """

    return await nodes_service.search_nodes(params, user_id=current_user.id)


@router.get(
    "/{node_id}",
    response_model=NodeRead,
    status_code=status.HTTP_200_OK,
)
async def get_node(
    current_user: CurrentActiveUserDependency,
    _: None = RequireReadNodeDependency,
    node_id: UUID = Path(...),
    nodes_service: NodesService = Depends(get_nodes_service_dependency),
) -> NodeRead:
    """Возвращает узел файловой системы по идентификатору.

    Получает подробные данные узла, если текущий пользователь имеет право
    на чтение этого узла.

    Args:
        current_user: Текущий активный пользователь, запрашивающий узел.
        _: Зависимость проверки права чтения узла. Используется только для
            авторизации и не применяется внутри функции напрямую.
        node_id: Уникальный идентификатор узла.
        nodes_service: Сервис узлов, выполняющий получение данных узла.

    Returns:
        Подробные данные узла файловой системы.

    Raises:
        HTTPException: Если пользователь не аутентифицирован, узел не найден
            или у пользователя нет права на чтение узла.
    """

    return await nodes_service.get_node(node_id, user_id=current_user.id)


@router.patch(
    "/{node_id}",
    response_model=NodeOperationResponse,
    status_code=status.HTTP_200_OK,
)
async def update_node(
    data: NodeUpdate,
    current_user: CurrentActiveUserDependency,
    _: None = RequireWriteNodeDependency,
    node_id: UUID = Path(...),
    recursive_visibility: bool = Query(default=False),
    nodes_service: NodesService = Depends(get_nodes_service_dependency),
) -> NodeOperationResponse:
    """Обновляет узел файловой системы.

    Изменяет данные узла от имени текущего пользователя. При включённом
    параметре `recursive_visibility` изменение видимости может быть применено
    рекурсивно к дочерним узлам, если это поддерживается сервисным слоем.

    Args:
        data: Данные для обновления узла.
        current_user: Текущий активный пользователь, выполняющий обновление.
        _: Зависимость проверки права записи в узел. Используется только для
            авторизации и не применяется внутри функции напрямую.
        node_id: Уникальный идентификатор обновляемого узла.
        recursive_visibility: Нужно ли рекурсивно применить изменение видимости
            к дочерним узлам.
        nodes_service: Сервис узлов, выполняющий обновление узла.

    Returns:
        Результат операции обновления узла.

    Raises:
        HTTPException: Если пользователь не аутентифицирован, узел не найден,
            у пользователя нет права записи или данные обновления некорректны.
    """

    return await nodes_service.update_node(
        node_id,
        data,
        actor_id=current_user.id,
        recursive_visibility=recursive_visibility,
    )


@router.post(
    "/{node_id}/rename",
    response_model=NodeOperationResponse,
    status_code=status.HTTP_200_OK,
)
async def rename_node(
    data: NodeRenameRequest,
    current_user: CurrentActiveUserDependency,
    _: None = RequireWriteNodeDependency,
    node_id: UUID = Path(...),
    nodes_service: NodesService = Depends(get_nodes_service_dependency),
) -> NodeOperationResponse:
    """Переименовывает узел файловой системы.

    Изменяет имя указанного узла от имени текущего пользователя после проверки
    права записи.

    Args:
        data: Данные для переименования узла.
        current_user: Текущий активный пользователь, выполняющий переименование.
        _: Зависимость проверки права записи в узел. Используется только для
            авторизации и не применяется внутри функции напрямую.
        node_id: Уникальный идентификатор переименовываемого узла.
        nodes_service: Сервис узлов, выполняющий переименование узла.

    Returns:
        Результат операции переименования узла.

    Raises:
        HTTPException: Если пользователь не аутентифицирован, узел не найден,
            у пользователя нет права записи или новое имя узла некорректно.
    """

    return await nodes_service.rename_node(
        node_id,
        data,
        actor_id=current_user.id,
    )


@router.post(
    "/{node_id}/move",
    response_model=NodeOperationResponse,
    status_code=status.HTTP_200_OK,
)
async def move_node(
    data: NodeMoveRequest,
    current_user: CurrentActiveUserDependency,
    _: None = RequireWriteNodeDependency,
    node_id: UUID = Path(...),
    nodes_service: NodesService = Depends(get_nodes_service_dependency),
) -> NodeOperationResponse:
    """Перемещает узел файловой системы.

    Переносит указанный узел в новое расположение от имени текущего пользователя
    после проверки права записи.

    Args:
        data: Данные для перемещения узла, включая целевое расположение.
        current_user: Текущий активный пользователь, выполняющий перемещение.
        _: Зависимость проверки права записи в узел. Используется только для
            авторизации и не применяется внутри функции напрямую.
        node_id: Уникальный идентификатор перемещаемого узла.
        nodes_service: Сервис узлов, выполняющий перемещение узла.

    Returns:
        Результат операции перемещения узла.

    Raises:
        HTTPException: Если пользователь не аутентифицирован, узел или целевое
            расположение не найдены, у пользователя нет права записи либо
            перемещение невозможно.
    """

    return await nodes_service.move_node(
        node_id,
        data,
        actor_id=current_user.id,
    )


@router.delete(
    "/{node_id}",
    response_model=NodeOperationResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_node(
    current_user: CurrentActiveUserDependency,
    _: None = RequireDeleteNodeDependency,
    node_id: UUID = Path(...),
    recursive: bool = Query(default=True),
    nodes_service: NodesService = Depends(get_nodes_service_dependency),
) -> NodeOperationResponse:
    """Выполняет soft delete узла файловой системы.

    Помечает узел как удалённый без физического удаления данных. При включённом
    параметре `recursive` удаление может быть применено к дочерним узлам.

    Args:
        current_user: Текущий активный пользователь, выполняющий удаление.
        _: Зависимость проверки права удаления узла. Используется только для
            авторизации и не применяется внутри функции напрямую.
        node_id: Уникальный идентификатор удаляемого узла.
        recursive: Нужно ли рекурсивно удалить дочерние узлы.
        nodes_service: Сервис узлов, выполняющий soft delete узла.

    Returns:
        Результат операции удаления узла.

    Raises:
        HTTPException: Если пользователь не аутентифицирован, узел не найден,
            у пользователя нет права удаления или удаление невозможно.
    """

    return await nodes_service.delete_node(
        node_id,
        actor_id=current_user.id,
        recursive=recursive,
    )


@router.post(
    "/{node_id}/download",
    response_model=FileDownloadResponse,
    status_code=status.HTTP_200_OK,
)
async def download_node(
    current_user: CurrentActiveUserDependency,
    _: None = RequireReadNodeDependency,
    node_id: UUID = Path(...),
    force_download: bool = Query(default=True),
    files_service: FilesService = Depends(get_files_service_dependency),
    downloads_service: DownloadsService = Depends(get_downloads_service_dependency),
) -> FileDownloadResponse:
    """Создаёт ссылку для скачивания файла по идентификатору узла."""

    file_read = await files_service.get_file(node_id, user_id=current_user.id)
    request_data = FileDownloadRequest(file_id=file_read.id, force_download=force_download)
    return await downloads_service.create_file_download_url(request_data, user_id=current_user.id)


@router.get(
    "/{node_id}/breadcrumbs",
    response_model=list[NodeBreadcrumbItem],
    status_code=status.HTTP_200_OK,
)
async def get_node_breadcrumbs(
    current_user: CurrentActiveUserDependency,
    _: None = RequireReadNodeDependency,
    node_id: UUID = Path(...),
    include_deleted: bool = Query(default=False),
    nodes_service: NodesService = Depends(get_nodes_service_dependency),
) -> list[NodeBreadcrumbItem]:
    """Возвращает хлебные крошки для узла.

    Формирует путь от корневого узла до указанного узла. При необходимости
    может включать удалённые элементы пути, если это разрешено параметрами
    запроса и поддерживается сервисным слоем.

    Args:
        current_user: Текущий активный пользователь, запрашивающий путь к узлу.
        _: Зависимость проверки права чтения узла. Используется только для
            авторизации и не применяется внутри функции напрямую.
        node_id: Уникальный идентификатор узла.
        include_deleted: Нужно ли разрешить удалённые узлы в хлебных крошках.
        nodes_service: Сервис узлов, выполняющий построение хлебных крошек.

    Returns:
        Список элементов хлебных крошек от корня до указанного узла.

    Raises:
        HTTPException: Если пользователь не аутентифицирован, узел не найден
            или у пользователя нет права на чтение узла.
    """

    return await nodes_service.get_breadcrumbs(
        node_id,
        user_id=current_user.id,
        allow_deleted=include_deleted,
    )


@router.get(
    "/{node_id}/content",
    response_model=FolderContentRead,
    status_code=status.HTTP_200_OK,
)
async def get_folder_content_by_node(
    current_user: CurrentActiveUserDependency,
    _: None = RequireReadNodeDependency,
    node_id: UUID = Path(...),
    folders_service: FoldersService = Depends(get_folders_service_dependency),
) -> FolderContentRead:
    """Возвращает содержимое папки по идентификатору узла.

    Позволяет получить содержимое папки, используя идентификатор узла
    файловой системы вместо идентификатора папки.

    Args:
        current_user: Текущий активный пользователь, запрашивающий содержимое.
        _: Зависимость проверки права чтения узла.
        node_id: Уникальный идентификатор узла папки.
        folders_service: Сервис папок, выполняющий получение содержимого.

    Returns:
        Содержимое указанной папки.

    Raises:
        HTTPException: Если пользователь не аутентифицирован, узел не найден,
            узел не является папкой или доступ к содержимому запрещён.
    """

    return await folders_service.get_folder_content(
        node_id,
        user_id=current_user.id,
    )


__all__ = ["router"]
