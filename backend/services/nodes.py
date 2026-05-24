from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from enum import Enum
from typing import Any, cast
from uuid import UUID

from core.logging import get_logger
from database import DatabaseError, UnitOfWorkFactory, create_unit_of_work_factory
from database.models.enums import (
    AuditAction,
    AuditResourceType,
    AuditResult,
    NodeType,
    NodeVisibility,
)
from database.models.filesystem import FileSystemNode
from database.repositories.nodes import NodeSortDirection, NodeSortField
from schemas.common import PageMeta, PageResponse
from schemas.nodes import (
    NodeBreadcrumbItem,
    NodeCreate,
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
from security.permissions import PermissionAction
from services.access import AccessService, get_access_service
from services.audit import AuditService, get_audit_service
from services.exceptions import (
    PermissionServiceError,
    ServiceError,
    ValidationServiceError,
    service_error_from_database,
    service_error_from_exception,
)

logger = get_logger("services.nodes")

SERVICE_NAME = "nodes"
REPOSITORY_PAGE_LIMIT = 1000
ALLOWED_SORT_FIELDS: set[str] = {
    "name",
    "created_at",
    "updated_at",
    "deleted_at",
    "depth",
    "node_type",
}


class NodesService:
    """Business service for common filesystem hierarchy operations."""

    def __init__(
        self,
        *,
        uow_factory: UnitOfWorkFactory | None = None,
        access_service: AccessService | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self.uow_factory = uow_factory or create_unit_of_work_factory()
        self.access_service = access_service or get_access_service(
            uow_factory=self.uow_factory
        )
        self.audit_service = audit_service or get_audit_service(
            uow_factory=self.uow_factory
        )

    async def create_node(
        self,
        data: NodeCreate,
        *,
        owner_id: UUID,
        actor_id: UUID | None = None,
    ) -> NodeOperationResponse:
        operation = "create_node"
        created_snapshot: dict[str, Any] | None = None
        resolved_actor_id = actor_id or owner_id

        try:
            async with self.uow_factory() as uow:
                if data.parent_id is not None:
                    parent = await self.access_service.get_accessible_node(
                        node_id=data.parent_id,
                        user_id=resolved_actor_id,
                        action=PermissionAction.WRITE,
                        uow=uow,
                    )
                    if parent.owner_id != owner_id:
                        raise ValidationServiceError(
                            "Parent node belongs to another owner.",
                            field="parent_id",
                            value=data.parent_id,
                            reason="owner_mismatch",
                            details={"service": SERVICE_NAME, "operation": operation},
                        )
                elif resolved_actor_id != owner_id:
                    raise PermissionServiceError(
                        "Only the owner can create root-level nodes.",
                        user_id=resolved_actor_id,
                        resource_type="filesystem_root",
                        resource_id=owner_id,
                        action=PermissionAction.WRITE,
                        reason="not_owner",
                        details={"service": SERVICE_NAME, "operation": operation},
                    )

                node = await uow.nodes.create_node(
                    owner_id=owner_id,
                    name=data.name,
                    node_type=data.node_type,
                    parent_id=data.parent_id,
                    visibility=data.visibility,
                    created_by=resolved_actor_id,
                    updated_by=resolved_actor_id,
                    check_owner_exists=True,
                    check_conflict=True,
                    flush=True,
                    refresh=True,
                )
                created_snapshot = _node_snapshot(node)
                await uow.commit()

            if created_snapshot is None:
                raise _empty_result_error(operation)

            await self._safe_log_node_event(
                user_id=resolved_actor_id,
                action=AuditAction.NODE_CREATED,
                snapshot=created_snapshot,
                message="Filesystem node created.",
            )
            return _operation_response(created_snapshot, "Filesystem node created.")

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to create filesystem node."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to create filesystem node."
            ) from exc

    async def get_node(
        self,
        node_id: UUID,
        *,
        user_id: UUID | None,
        allow_deleted: bool = False,
        allow_public: bool = True,
    ) -> NodeRead:
        operation = "get_node"
        snapshot: dict[str, Any] | None = None

        try:
            async with self.uow_factory() as uow:
                node = await self.access_service.get_accessible_node(
                    node_id=node_id,
                    user_id=user_id,
                    action=PermissionAction.READ,
                    allow_deleted=allow_deleted,
                    allow_public=allow_public,
                    uow=uow,
                )
                snapshot = _node_snapshot(node)

            if snapshot is None:
                raise _empty_result_error(operation)
            return NodeRead.model_validate(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to load filesystem node."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to load filesystem node."
            ) from exc

    async def list_nodes(
        self,
        params: NodeQueryParams,
        *,
        user_id: UUID | None,
    ) -> PageResponse[NodeListItem]:
        operation = "list_nodes"
        page: PageResponse[NodeListItem] | None = None

        try:
            async with self.uow_factory() as uow:
                owner_id = params.owner_id or user_id
                parent_id = params.parent_id

                if parent_id is not None:
                    parent = await self.access_service.get_accessible_node(
                        node_id=parent_id,
                        user_id=user_id,
                        action=PermissionAction.READ,
                        allow_deleted=params.is_deleted is not False,
                        uow=uow,
                    )
                    if owner_id is None:
                        owner_id = parent.owner_id
                    elif owner_id != parent.owner_id:
                        raise ValidationServiceError(
                            "Owner filter does not match parent owner.",
                            field="owner_id",
                            value=owner_id,
                            reason="owner_parent_mismatch",
                            details={"service": SERVICE_NAME, "operation": operation},
                        )
                elif owner_id is None:
                    raise PermissionServiceError(
                        "Root-level listing requires an authenticated owner.",
                        action=PermissionAction.READ,
                        reason="anonymous_user",
                        details={"service": SERVICE_NAME, "operation": operation},
                    )
                elif user_id != owner_id:
                    raise PermissionServiceError(
                        "Root-level listing is available only to the owner.",
                        user_id=user_id,
                        resource_type="filesystem_root",
                        resource_id=owner_id,
                        action=PermissionAction.READ,
                        reason="not_owner",
                        details={"service": SERVICE_NAME, "operation": operation},
                    )

                nodes = await self._load_list_nodes(
                    uow=uow, params=params, owner_id=owner_id
                )
                filtered_nodes = _filter_query_nodes(nodes, params)
                page = _nodes_page(
                    filtered_nodes,
                    limit=params.limit,
                    offset=params.offset,
                )

            if page is None:
                raise _empty_result_error(operation)
            return page

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to list filesystem nodes."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to list filesystem nodes."
            ) from exc

    async def search_nodes(
        self,
        params: NodeSearchQuery,
        *,
        user_id: UUID | None,
    ) -> PageResponse[NodeListItem]:
        operation = "search_nodes"
        page: PageResponse[NodeListItem] | None = None

        try:
            async with self.uow_factory() as uow:
                owner_id = params.owner_id or user_id

                if params.parent_id is not None:
                    parent = await self.access_service.get_accessible_node(
                        node_id=params.parent_id,
                        user_id=user_id,
                        action=PermissionAction.READ,
                        allow_deleted=params.include_deleted,
                        uow=uow,
                    )
                    if owner_id is None:
                        owner_id = parent.owner_id
                    elif owner_id != parent.owner_id:
                        raise ValidationServiceError(
                            "Owner filter does not match parent owner.",
                            field="owner_id",
                            value=owner_id,
                            reason="owner_parent_mismatch",
                            details={"service": SERVICE_NAME, "operation": operation},
                        )
                elif owner_id is None:
                    raise PermissionServiceError(
                        "Search requires an authenticated owner or parent node.",
                        action=PermissionAction.READ,
                        reason="anonymous_user",
                        details={"service": SERVICE_NAME, "operation": operation},
                    )
                elif user_id != owner_id:
                    raise PermissionServiceError(
                        "User can search only own root hierarchy without a parent node.",
                        user_id=user_id,
                        resource_type="filesystem_root",
                        resource_id=owner_id,
                        action=PermissionAction.READ,
                        reason="not_owner",
                        details={"service": SERVICE_NAME, "operation": operation},
                    )

                nodes = await self._load_search_nodes(
                    uow=uow,
                    params=params,
                    owner_id=owner_id,
                )
                filtered_nodes = _filter_search_nodes(nodes, params)
                page = _nodes_page(
                    filtered_nodes,
                    limit=params.limit,
                    offset=params.offset,
                )

            if page is None:
                raise _empty_result_error(operation)
            return page

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to search filesystem nodes."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to search filesystem nodes."
            ) from exc

    async def update_node(
        self,
        node_id: UUID,
        data: NodeUpdate,
        *,
        actor_id: UUID,
        recursive_visibility: bool = False,
    ) -> NodeOperationResponse:
        operation = "update_node"
        snapshot: dict[str, Any] | None = None
        audit_action = AuditAction.NODE_MOVED

        try:
            async with self.uow_factory() as uow:
                await self.access_service.require_access(
                    node_id=node_id,
                    user_id=actor_id,
                    action=PermissionAction.WRITE,
                    uow=uow,
                )

                node = await uow.nodes.get_required_by_id(node_id)
                if data.name is not None:
                    node = await uow.nodes.rename_node(
                        node_id=node.id,
                        new_name=data.name,
                        updated_by=actor_id,
                        flush=True,
                        refresh=False,
                    )
                    audit_action = AuditAction.NODE_RENAMED

                if "parent_id" in data.model_fields_set:
                    if data.parent_id is not None:
                        await self.access_service.require_access(
                            node_id=data.parent_id,
                            user_id=actor_id,
                            action=PermissionAction.WRITE,
                            uow=uow,
                        )
                    node = await uow.nodes.move_node(
                        node_id=node.id,
                        new_parent_id=data.parent_id,
                        updated_by=actor_id,
                        flush=True,
                        refresh=False,
                    )
                    audit_action = AuditAction.NODE_MOVED

                if data.visibility is not None:
                    await self.access_service.require_access(
                        node_id=node.id,
                        user_id=actor_id,
                        action=PermissionAction.SHARE,
                        uow=uow,
                    )
                    node = await uow.nodes.update_visibility(
                        node_id=node.id,
                        visibility=data.visibility,
                        recursive=recursive_visibility,
                        updated_by=actor_id,
                        flush=True,
                        refresh=False,
                    )

                await uow.refresh(node)
                snapshot = _node_snapshot(node)
                await uow.commit()

            if snapshot is None:
                raise _empty_result_error(operation)

            await self._safe_log_node_event(
                user_id=actor_id,
                action=audit_action,
                snapshot=snapshot,
                message="Filesystem node updated.",
            )
            return _operation_response(snapshot, "Filesystem node updated.")

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to update filesystem node."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to update filesystem node."
            ) from exc

    async def rename_node(
        self,
        node_id: UUID,
        data: NodeRenameRequest,
        *,
        actor_id: UUID,
    ) -> NodeOperationResponse:
        return await self._mutate_node(
            node_id=node_id,
            actor_id=actor_id,
            access_action=PermissionAction.WRITE,
            audit_action=AuditAction.NODE_RENAMED,
            message="Filesystem node renamed.",
            mutate=lambda uow: uow.nodes.rename_node(
                node_id=node_id,
                new_name=data.name,
                updated_by=actor_id,
                flush=True,
                refresh=True,
            ),
            operation="rename_node",
        )

    async def move_node(
        self,
        node_id: UUID,
        data: NodeMoveRequest,
        *,
        actor_id: UUID,
    ) -> NodeOperationResponse:
        operation = "move_node"
        snapshot: dict[str, Any] | None = None

        try:
            async with self.uow_factory() as uow:
                await self.access_service.require_access(
                    node_id=node_id,
                    user_id=actor_id,
                    action=PermissionAction.WRITE,
                    uow=uow,
                )
                if data.target_parent_id is not None:
                    await self.access_service.require_access(
                        node_id=data.target_parent_id,
                        user_id=actor_id,
                        action=PermissionAction.WRITE,
                        uow=uow,
                    )

                node = await uow.nodes.move_node(
                    node_id=node_id,
                    new_parent_id=data.target_parent_id,
                    updated_by=actor_id,
                    flush=True,
                    refresh=True,
                )
                snapshot = _node_snapshot(node)
                await uow.commit()

            if snapshot is None:
                raise _empty_result_error(operation)

            await self._safe_log_node_event(
                user_id=actor_id,
                action=AuditAction.NODE_MOVED,
                snapshot=snapshot,
                message="Filesystem node moved.",
            )
            return _operation_response(snapshot, "Filesystem node moved.")

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to move filesystem node."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to move filesystem node."
            ) from exc

    async def update_visibility(
        self,
        node_id: UUID,
        visibility: NodeVisibility,
        *,
        actor_id: UUID,
        recursive: bool = False,
    ) -> NodeOperationResponse:
        return await self._mutate_node(
            node_id=node_id,
            actor_id=actor_id,
            access_action=PermissionAction.SHARE,
            audit_action=AuditAction.NODE_MOVED,
            message="Filesystem node visibility updated.",
            mutate=lambda uow: uow.nodes.update_visibility(
                node_id=node_id,
                visibility=visibility,
                recursive=recursive,
                updated_by=actor_id,
                flush=True,
                refresh=True,
            ),
            operation="update_visibility",
        )

    async def delete_node(
        self,
        node_id: UUID,
        *,
        actor_id: UUID,
        recursive: bool = True,
    ) -> NodeOperationResponse:
        return await self._mutate_node(
            node_id=node_id,
            actor_id=actor_id,
            access_action=PermissionAction.DELETE,
            audit_action=AuditAction.NODE_DELETED,
            message="Filesystem node moved to trash.",
            mutate=lambda uow: uow.nodes.soft_delete_node(
                node_id=node_id,
                deleted_by=actor_id,
                recursive=recursive,
                flush=True,
                refresh=True,
            ),
            operation="delete_node",
        )

    async def restore_node(
        self,
        node_id: UUID,
        *,
        actor_id: UUID,
        recursive: bool = True,
    ) -> NodeOperationResponse:
        return await self._mutate_node(
            node_id=node_id,
            actor_id=actor_id,
            access_action=PermissionAction.DELETE,
            audit_action=AuditAction.NODE_RESTORED,
            message="Filesystem node restored.",
            allow_deleted=True,
            mutate=lambda uow: uow.nodes.restore_node(
                node_id=node_id,
                updated_by=actor_id,
                recursive=recursive,
                flush=True,
                refresh=True,
            ),
            operation="restore_node",
        )

    async def purge_node(
        self, node_id: UUID, *, actor_id: UUID
    ) -> NodeOperationResponse:
        operation = "purge_node"
        snapshot: dict[str, Any] | None = None

        try:
            async with self.uow_factory() as uow:
                await self.access_service.require_access(
                    node_id=node_id,
                    user_id=actor_id,
                    action=PermissionAction.MANAGE,
                    allow_deleted=True,
                    uow=uow,
                )
                node = await uow.nodes.get_required_by_id(node_id)
                snapshot = _node_snapshot(node)
                await uow.nodes.mark_purged(node_id=node_id, flush=True)
                await uow.commit()

            if snapshot is None:
                raise _empty_result_error(operation)

            await self._safe_log_node_event(
                user_id=actor_id,
                action=AuditAction.NODE_PURGED,
                snapshot=snapshot,
                message="Filesystem node permanently deleted.",
            )
            return NodeOperationResponse(
                success=True,
                node=None,
                message="Filesystem node permanently deleted.",
            )

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to purge filesystem node."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to purge filesystem node."
            ) from exc

    async def get_breadcrumbs(
        self,
        node_id: UUID,
        *,
        user_id: UUID | None,
        allow_deleted: bool = False,
    ) -> list[NodeBreadcrumbItem]:
        operation = "get_breadcrumbs"
        breadcrumbs: list[NodeBreadcrumbItem] | None = None

        try:
            async with self.uow_factory() as uow:
                await self.access_service.require_access(
                    node_id=node_id,
                    user_id=user_id,
                    action=PermissionAction.READ,
                    allow_deleted=allow_deleted,
                    uow=uow,
                )
                nodes = await uow.nodes.get_breadcrumbs(
                    node_id=node_id,
                    include_self=True,
                    include_deleted=allow_deleted,
                )
                breadcrumbs = [
                    NodeBreadcrumbItem.model_validate(_breadcrumb_snapshot(node))
                    for node in nodes
                ]

            if breadcrumbs is None:
                raise _empty_result_error(operation)
            return breadcrumbs

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to build breadcrumbs."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to build breadcrumbs."
            ) from exc

    async def get_tree(
        self,
        root_node_id: UUID,
        *,
        user_id: UUID | None,
        include_deleted: bool = False,
    ) -> NodeTreeItem:
        operation = "get_tree"
        tree: NodeTreeItem | None = None

        try:
            async with self.uow_factory() as uow:
                await self.access_service.require_access(
                    node_id=root_node_id,
                    user_id=user_id,
                    action=PermissionAction.READ,
                    allow_deleted=include_deleted,
                    uow=uow,
                )
                nodes = await uow.nodes.get_descendants(
                    node_id=root_node_id,
                    include_self=True,
                    include_deleted=include_deleted,
                    order_by_depth=True,
                )
                tree = _build_tree(nodes, root_node_id=root_node_id)

            if tree is None:
                raise _empty_result_error(operation)
            return tree

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to build filesystem tree."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to build filesystem tree."
            ) from exc

    async def count_user_nodes(
        self,
        *,
        owner_id: UUID,
        user_id: UUID,
        include_deleted: bool = False,
    ) -> dict[NodeType | str, int]:
        operation = "count_user_nodes"
        counts: dict[NodeType | str, int] | None = None

        try:
            if owner_id != user_id:
                raise PermissionServiceError(
                    "User can count only own filesystem nodes.",
                    user_id=user_id,
                    resource_type="filesystem_root",
                    resource_id=owner_id,
                    action=PermissionAction.READ,
                    reason="not_owner",
                    details={"service": SERVICE_NAME, "operation": operation},
                )

            async with self.uow_factory() as uow:
                counts = {
                    "total": await uow.nodes.count_user_nodes(
                        owner_id=owner_id,
                        include_deleted=include_deleted,
                    ),
                    NodeType.FILE: await uow.nodes.count_user_files(
                        owner_id=owner_id,
                        include_deleted=include_deleted,
                    ),
                    NodeType.FOLDER: await uow.nodes.count_user_folders(
                        owner_id=owner_id,
                        include_deleted=include_deleted,
                    ),
                }

            if counts is None:
                raise _empty_result_error(operation)
            return counts

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to count filesystem nodes."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to count filesystem nodes."
            ) from exc

    async def _mutate_node(
        self,
        *,
        node_id: UUID,
        actor_id: UUID,
        access_action: PermissionAction,
        audit_action: AuditAction,
        message: str,
        mutate: Any,
        operation: str,
        allow_deleted: bool = False,
    ) -> NodeOperationResponse:
        snapshot: dict[str, Any] | None = None

        try:
            async with self.uow_factory() as uow:
                await self.access_service.require_access(
                    node_id=node_id,
                    user_id=actor_id,
                    action=access_action,
                    allow_deleted=allow_deleted,
                    uow=uow,
                )
                node = await mutate(uow)
                snapshot = _node_snapshot(node)
                await uow.commit()

            if snapshot is None:
                raise _empty_result_error(operation)

            await self._safe_log_node_event(
                user_id=actor_id,
                action=audit_action,
                snapshot=snapshot,
                message=message,
            )
            return _operation_response(snapshot, message)

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message=message
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message=message
            ) from exc

    async def _load_list_nodes(
        self,
        *,
        uow: Any,
        params: NodeQueryParams,
        owner_id: UUID,
    ) -> list[FileSystemNode]:
        sort_by = _normalize_sort_by(params.sort_by)
        sort_direction = _sort_direction(params.sort_desc)
        include_deleted = params.is_deleted is not False
        nodes: list[FileSystemNode] = []
        offset = 0

        while True:
            if params.parent_id is None:
                chunk = await uow.nodes.get_root_nodes(
                    owner_id=owner_id,
                    include_deleted=include_deleted,
                    node_type=params.node_type,
                    offset=offset,
                    limit=REPOSITORY_PAGE_LIMIT,
                    sort_by=sort_by,
                    sort_direction=sort_direction,
                )
            else:
                chunk = await uow.nodes.get_children(
                    parent_id=params.parent_id,
                    include_deleted=include_deleted,
                    node_type=params.node_type,
                    offset=offset,
                    limit=REPOSITORY_PAGE_LIMIT,
                    sort_by=sort_by,
                    sort_direction=sort_direction,
                )

            nodes.extend(chunk)
            if len(chunk) < REPOSITORY_PAGE_LIMIT:
                return nodes
            offset += REPOSITORY_PAGE_LIMIT

    async def _load_search_nodes(
        self,
        *,
        uow: Any,
        params: NodeSearchQuery,
        owner_id: UUID,
    ) -> list[FileSystemNode]:
        sort_by = _normalize_sort_by(params.sort_by)
        sort_direction = _sort_direction(params.sort_desc)
        nodes: list[FileSystemNode] = []
        offset = 0

        while True:
            chunk = await uow.nodes.search_nodes(
                owner_id=owner_id,
                query=params.query,
                parent_id=params.parent_id,
                node_type=params.node_type,
                include_deleted=params.include_deleted,
                offset=offset,
                limit=REPOSITORY_PAGE_LIMIT,
                sort_by=sort_by,
                sort_direction=sort_direction,
            )
            nodes.extend(chunk)
            if len(chunk) < REPOSITORY_PAGE_LIMIT:
                return nodes
            offset += REPOSITORY_PAGE_LIMIT

    async def _safe_log_node_event(
        self,
        *,
        user_id: UUID,
        action: AuditAction,
        snapshot: dict[str, Any],
        message: str,
    ) -> None:
        try:
            await self.audit_service.log_user_event(
                user_id=user_id,
                action=action,
                result=AuditResult.SUCCESS,
                entity_type="filesystem_node",
                entity_id=cast(UUID, snapshot["id"]),
                resource_type=AuditResourceType.NODE,
                message=message,
                metadata=_audit_metadata(snapshot),
            )
        except Exception as exc:
            logger.warning(
                "Failed to write node audit event",
                extra={
                    "action": action.value,
                    "node_id": str(snapshot.get("id")),
                    "error_type": exc.__class__.__name__,
                },
            )

    @staticmethod
    def _database_error(
        exc: DatabaseError,
        *,
        operation: str,
        message: str,
    ) -> ServiceError:
        return service_error_from_database(
            exc,
            operation=operation,
            message=message,
            service=SERVICE_NAME,
        )

    @staticmethod
    def _unexpected_error(
        exc: Exception,
        *,
        operation: str,
        message: str,
    ) -> ServiceError:
        logger.exception(
            message,
            extra={"operation": operation, "error_type": exc.__class__.__name__},
        )
        return service_error_from_exception(
            exc,
            operation=operation,
            message=message,
            service=SERVICE_NAME,
        )


def _node_snapshot(node: FileSystemNode) -> dict[str, Any]:
    return {
        "id": node.id,
        "owner_id": node.owner_id,
        "parent_id": node.parent_id,
        "name": node.name,
        "node_type": node.node_type,
        "visibility": node.visibility,
        "path": node.path,
        "depth": node.depth,
        "created_by": node.created_by,
        "updated_by": node.updated_by,
        "deleted_by": node.deleted_by,
        "created_at": node.created_at,
        "updated_at": node.updated_at,
        "is_deleted": bool(node.is_deleted),
        "deleted_at": node.deleted_at,
    }


def _breadcrumb_snapshot(node: FileSystemNode) -> dict[str, Any]:
    return {
        "id": node.id,
        "name": node.name,
        "node_type": node.node_type,
        "path": node.path,
        "depth": node.depth,
    }


def _tree_snapshot(
    node: FileSystemNode,
    *,
    children: Iterable[NodeTreeItem] = (),
) -> dict[str, Any]:
    return {
        "id": node.id,
        "parent_id": node.parent_id,
        "name": node.name,
        "node_type": node.node_type,
        "visibility": node.visibility,
        "path": node.path,
        "depth": node.depth,
        "children": list(children),
    }


def _operation_response(
    snapshot: dict[str, Any], message: str
) -> NodeOperationResponse:
    return NodeOperationResponse(
        success=True,
        node=NodeRead.model_validate(snapshot),
        message=message,
    )


def _nodes_page(
    nodes: list[FileSystemNode],
    *,
    limit: int,
    offset: int,
) -> PageResponse[NodeListItem]:
    page_nodes = nodes[offset : offset + limit]
    items = [NodeListItem.model_validate(_node_snapshot(node)) for node in page_nodes]
    return PageResponse(
        items=items,
        meta=PageMeta(
            limit=limit,
            offset=offset,
            total=len(nodes),
            count=len(items),
        ),
    )


def _filter_query_nodes(
    nodes: list[FileSystemNode],
    params: NodeQueryParams,
) -> list[FileSystemNode]:
    return [
        node
        for node in nodes
        if _matches_deleted(node, params.is_deleted)
        and _matches_visibility(node, params.visibility)
        and _matches_range(node.created_at, params.created_from, params.created_to)
        and _matches_range(node.updated_at, params.updated_from, params.updated_to)
    ]


def _filter_search_nodes(
    nodes: list[FileSystemNode],
    params: NodeSearchQuery,
) -> list[FileSystemNode]:
    return [
        node
        for node in nodes
        if _matches_visibility(node, params.visibility)
        and (params.include_deleted or not bool(node.is_deleted))
    ]


def _matches_deleted(node: FileSystemNode, is_deleted: bool | None) -> bool:
    if is_deleted is None:
        return True
    return bool(node.is_deleted) is is_deleted


def _matches_visibility(
    node: FileSystemNode,
    visibility: NodeVisibility | None,
) -> bool:
    if visibility is None:
        return True
    return node.visibility == visibility


def _matches_range(
    value: datetime | None,
    start: datetime | None,
    end: datetime | None,
) -> bool:
    if value is None:
        return start is None and end is None
    normalized_value = _normalize_datetime(value)
    if start is not None and normalized_value < _normalize_datetime(start):
        return False
    if end is not None and normalized_value > _normalize_datetime(end):
        return False
    return True


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _normalize_sort_by(sort_by: str) -> NodeSortField:
    normalized = sort_by.strip().lower()
    if normalized not in ALLOWED_SORT_FIELDS:
        raise ValidationServiceError(
            "Unsupported node sort field.",
            field="sort_by",
            value=sort_by,
            reason="unsupported_sort_field",
            details={
                "service": SERVICE_NAME,
                "allowed_values": sorted(ALLOWED_SORT_FIELDS),
            },
        )
    return cast(NodeSortField, normalized)


def _sort_direction(sort_desc: bool) -> NodeSortDirection:
    return "desc" if sort_desc else "asc"


def _build_tree(nodes: list[FileSystemNode], *, root_node_id: UUID) -> NodeTreeItem:
    node_by_id = {node.id: node for node in nodes}
    root = node_by_id.get(root_node_id)
    if root is None:
        raise ServiceError(
            "Root node is missing from descendants result.",
            service=SERVICE_NAME,
            operation="get_tree",
        )

    children_by_parent: dict[UUID | None, list[FileSystemNode]] = {}
    for node in nodes:
        children_by_parent.setdefault(node.parent_id, []).append(node)

    def build(node: FileSystemNode) -> NodeTreeItem:
        children = [
            build(child)
            for child in sorted(
                children_by_parent.get(node.id, []),
                key=lambda item: (
                    item.node_type.value,
                    item.name.casefold(),
                    str(item.id),
                ),
            )
        ]
        return NodeTreeItem.model_validate(_tree_snapshot(node, children=children))

    return build(root)


def _audit_metadata(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _jsonable(value)
        for key, value in snapshot.items()
        if key
        in {
            "id",
            "owner_id",
            "parent_id",
            "name",
            "node_type",
            "visibility",
            "path",
            "depth",
            "is_deleted",
        }
    }


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return str(value)


def _empty_result_error(operation: str) -> ServiceError:
    return ServiceError(
        "Service operation finished without a result.",
        service=SERVICE_NAME,
        operation=operation,
    )


_nodes_service: NodesService | None = None


def get_nodes_service(
    *,
    uow_factory: UnitOfWorkFactory | None = None,
    access_service: AccessService | None = None,
    audit_service: AuditService | None = None,
) -> NodesService:
    if (
        uow_factory is not None
        or access_service is not None
        or audit_service is not None
    ):
        return NodesService(
            uow_factory=uow_factory,
            access_service=access_service,
            audit_service=audit_service,
        )

    global _nodes_service
    if _nodes_service is None:
        _nodes_service = NodesService()
    return _nodes_service


__all__ = [
    "NodesService",
    "get_nodes_service",
]
