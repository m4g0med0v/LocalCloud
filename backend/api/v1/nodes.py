from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status

from api.dependencies import get_nodes_service_dependency
from schemas.common import PageResponse
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
from services import NodesService

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
    """Возвращает список узлов файловой системы."""

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
    """Возвращает дерево узлов от указанного корневого узла."""

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
    """Выполняет поиск по узлам файловой системы."""

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
    """Возвращает узел файловой системы по идентификатору."""

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
    """Обновляет узел файловой системы."""

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
    """Переименовывает узел файловой системы."""

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
    """Перемещает узел файловой системы."""

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
    """Выполняет soft delete узла файловой системы."""

    return await nodes_service.delete_node(
        node_id,
        actor_id=current_user.id,
        recursive=recursive,
    )


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
    """Возвращает хлебные крошки для узла."""

    return await nodes_service.get_breadcrumbs(
        node_id,
        user_id=current_user.id,
        allow_deleted=include_deleted,
    )


__all__ = ["router"]
