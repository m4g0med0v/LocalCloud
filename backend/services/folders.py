from __future__ import annotations

from enum import Enum
from typing import Any, cast
from uuid import UUID

from core.logging import get_logger
from database import DatabaseError, UnitOfWorkFactory, create_unit_of_work_factory
from database.models.enums import (
    AuditAction,
    AuditResourceType,
    AuditResult,
    BackgroundTaskStatus,
    BackgroundTaskType,
    NodeType,
    NodeVisibility,
)
from database.models.filesystem import FileSystemNode, Folder
from database.models.tasks import BackgroundTask
from database.repositories.folders import FolderSortField
from database.repositories.nodes import NodeSortDirection
from schemas.common import PageMeta, PageResponse
from schemas.folders import (
    FolderArchiveRequest,
    FolderArchiveResponse,
    FolderContentRead,
    FolderCreateRequest,
    FolderListItem,
    FolderRead,
    FolderUpdateRequest,
)
from schemas.nodes import NodeListItem
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

logger = get_logger("services.folders")

SERVICE_NAME = "folders"
REPOSITORY_PAGE_LIMIT = 1000
ALLOWED_FOLDER_SORT_FIELDS: set[str] = {
    "name",
    "created_at",
    "updated_at",
    "deleted_at",
    "depth",
    "color",
}


class FoldersService:
    """Business service for folders as entities on top of FileSystemNode."""

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

    async def create_folder(
        self,
        data: FolderCreateRequest,
        *,
        owner_id: UUID,
        actor_id: UUID | None = None,
        visibility: NodeVisibility = NodeVisibility.PRIVATE,
    ) -> FolderRead:
        operation = "create_folder"
        snapshot: dict[str, Any] | None = None
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
                    _ensure_folder_node(parent, operation=operation)
                    if parent.owner_id != owner_id:
                        raise ValidationServiceError(
                            "Parent folder belongs to another owner.",
                            field="parent_id",
                            value=data.parent_id,
                            reason="owner_mismatch",
                            details={"service": SERVICE_NAME, "operation": operation},
                        )
                elif resolved_actor_id != owner_id:
                    raise PermissionServiceError(
                        "Only the owner can create root-level folders.",
                        user_id=resolved_actor_id,
                        resource_type="filesystem_root",
                        resource_id=owner_id,
                        action=PermissionAction.WRITE,
                        reason="not_owner",
                        details={"service": SERVICE_NAME, "operation": operation},
                    )

                folder = await uow.folders.create_folder(
                    owner_id=owner_id,
                    name=data.name,
                    parent_id=data.parent_id,
                    description=data.description,
                    color=data.color,
                    visibility=visibility,
                    created_by=resolved_actor_id,
                    check_owner_exists=True,
                    check_conflict=True,
                    flush=True,
                    refresh=True,
                )
                folder = await uow.folders.get_required_by_node_id(folder.node_id)
                snapshot = _folder_snapshot(folder)
                await uow.commit()

            if snapshot is None:
                raise _empty_result_error(operation)

            await self._safe_log_folder_event(
                user_id=resolved_actor_id,
                action=AuditAction.FOLDER_CREATED,
                snapshot=snapshot,
                message="Folder created.",
            )
            return FolderRead.model_validate(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to create folder."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to create folder."
            ) from exc

    async def get_folder(
        self,
        node_id: UUID,
        *,
        user_id: UUID | None,
        allow_deleted: bool = False,
        allow_public: bool = True,
    ) -> FolderRead:
        operation = "get_folder"
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
                _ensure_folder_node(node, operation=operation)
                folder = await uow.folders.get_required_by_node_id(
                    node.id,
                    include_deleted=allow_deleted,
                )
                snapshot = _folder_snapshot(folder)

            if snapshot is None:
                raise _empty_result_error(operation)
            return FolderRead.model_validate(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to load folder."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to load folder."
            ) from exc

    async def get_folder_content(
        self,
        node_id: UUID,
        *,
        user_id: UUID | None,
        include_deleted: bool = False,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "name",
        sort_desc: bool = False,
    ) -> FolderContentRead:
        operation = "get_folder_content"
        content: FolderContentRead | None = None

        try:
            async with self.uow_factory() as uow:
                node = await self.access_service.get_accessible_node(
                    node_id=node_id,
                    user_id=user_id,
                    action=PermissionAction.READ,
                    allow_deleted=include_deleted,
                    uow=uow,
                )
                _ensure_folder_node(node, operation=operation)

                folder = await uow.folders.get_required_by_node_id(
                    node.id,
                    include_deleted=include_deleted,
                )
                children = await self._load_child_nodes(
                    uow=uow,
                    parent_id=node.id,
                    include_deleted=include_deleted,
                    sort_by=_normalize_node_sort_by(sort_by),
                    sort_direction=_sort_direction(sort_desc),
                )
                breadcrumbs = await uow.nodes.get_breadcrumbs(
                    node_id=node.id,
                    include_self=True,
                    include_deleted=include_deleted,
                )
                page_children = children[offset : offset + limit]
                content = FolderContentRead(
                    folder=FolderRead.model_validate(_folder_snapshot(folder)),
                    breadcrumbs=[
                        NodeListItem.model_validate(_node_snapshot(item))
                        for item in breadcrumbs
                    ],
                    items=[
                        NodeListItem.model_validate(_node_snapshot(item))
                        for item in page_children
                    ],
                    total=len(children),
                )

            if content is None:
                raise _empty_result_error(operation)
            return content

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to load folder content."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to load folder content."
            ) from exc

    async def list_folders(
        self,
        *,
        owner_id: UUID | None = None,
        parent_id: UUID | None = None,
        user_id: UUID | None,
        include_deleted: bool = False,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "name",
        sort_desc: bool = False,
    ) -> PageResponse[FolderListItem]:
        operation = "list_folders"
        page: PageResponse[FolderListItem] | None = None

        try:
            async with self.uow_factory() as uow:
                resolved_owner_id = owner_id or user_id

                if parent_id is not None:
                    parent = await self.access_service.get_accessible_node(
                        node_id=parent_id,
                        user_id=user_id,
                        action=PermissionAction.READ,
                        allow_deleted=include_deleted,
                        uow=uow,
                    )
                    _ensure_folder_node(parent, operation=operation)
                    resolved_owner_id = resolved_owner_id or parent.owner_id
                    if resolved_owner_id != parent.owner_id:
                        raise ValidationServiceError(
                            "Owner filter does not match parent folder owner.",
                            field="owner_id",
                            value=resolved_owner_id,
                            reason="owner_parent_mismatch",
                            details={"service": SERVICE_NAME, "operation": operation},
                        )
                elif resolved_owner_id is None:
                    raise PermissionServiceError(
                        "Root folder listing requires an authenticated owner.",
                        action=PermissionAction.READ,
                        reason="anonymous_user",
                        details={"service": SERVICE_NAME, "operation": operation},
                    )
                elif user_id != resolved_owner_id:
                    raise PermissionServiceError(
                        "Root folder listing is available only to the owner.",
                        user_id=user_id,
                        resource_type="filesystem_root",
                        resource_id=resolved_owner_id,
                        action=PermissionAction.READ,
                        reason="not_owner",
                        details={"service": SERVICE_NAME, "operation": operation},
                    )

                folders = await self._load_folders(
                    uow=uow,
                    owner_id=resolved_owner_id,
                    parent_id=parent_id,
                    include_deleted=include_deleted,
                    sort_by=_normalize_folder_sort_by(sort_by),
                    sort_direction=_sort_direction(sort_desc),
                )
                page = _folders_page(folders, limit=limit, offset=offset)

            if page is None:
                raise _empty_result_error(operation)
            return page

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to list folders."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to list folders."
            ) from exc

    async def update_folder(
        self,
        node_id: UUID,
        data: FolderUpdateRequest,
        *,
        actor_id: UUID,
    ) -> FolderRead:
        operation = "update_folder"
        snapshot: dict[str, Any] | None = None

        try:
            async with self.uow_factory() as uow:
                node = await self.access_service.get_accessible_node(
                    node_id=node_id,
                    user_id=actor_id,
                    action=PermissionAction.WRITE,
                    uow=uow,
                )
                _ensure_folder_node(node, operation=operation)
                folder = await uow.folders.update_metadata_by_node_id(
                    node_id=node.id,
                    description=data.description,
                    color=data.color,
                    updated_by=actor_id,
                    flush=True,
                    refresh=True,
                )
                snapshot = _folder_snapshot(folder)
                await uow.commit()

            if snapshot is None:
                raise _empty_result_error(operation)

            await self._safe_log_folder_event(
                user_id=actor_id,
                action=AuditAction.FOLDER_MOVED,
                snapshot=snapshot,
                message="Folder metadata updated.",
            )
            return FolderRead.model_validate(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to update folder."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to update folder."
            ) from exc

    async def rename_folder(
        self,
        node_id: UUID,
        *,
        new_name: str,
        actor_id: UUID,
    ) -> FolderRead:
        return await self._mutate_folder(
            node_id=node_id,
            actor_id=actor_id,
            access_action=PermissionAction.WRITE,
            audit_action=AuditAction.FOLDER_RENAMED,
            message="Folder renamed.",
            operation="rename_folder",
            mutate=lambda uow: uow.folders.rename_folder(
                node_id=node_id,
                new_name=new_name,
                updated_by=actor_id,
                flush=True,
                refresh=True,
            ),
        )

    async def move_folder(
        self,
        node_id: UUID,
        *,
        target_parent_id: UUID | None,
        actor_id: UUID,
    ) -> FolderRead:
        operation = "move_folder"
        snapshot: dict[str, Any] | None = None

        try:
            async with self.uow_factory() as uow:
                node = await self.access_service.get_accessible_node(
                    node_id=node_id,
                    user_id=actor_id,
                    action=PermissionAction.WRITE,
                    uow=uow,
                )
                _ensure_folder_node(node, operation=operation)
                if target_parent_id is not None:
                    target = await self.access_service.get_accessible_node(
                        node_id=target_parent_id,
                        user_id=actor_id,
                        action=PermissionAction.WRITE,
                        uow=uow,
                    )
                    _ensure_folder_node(target, operation=operation)

                folder = await uow.folders.move_folder(
                    node_id=node_id,
                    new_parent_id=target_parent_id,
                    updated_by=actor_id,
                    flush=True,
                    refresh=True,
                )
                snapshot = _folder_snapshot(folder)
                await uow.commit()

            if snapshot is None:
                raise _empty_result_error(operation)

            await self._safe_log_folder_event(
                user_id=actor_id,
                action=AuditAction.FOLDER_MOVED,
                snapshot=snapshot,
                message="Folder moved.",
            )
            return FolderRead.model_validate(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to move folder."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to move folder."
            ) from exc

    async def delete_folder(
        self,
        node_id: UUID,
        *,
        actor_id: UUID,
        recursive: bool = True,
    ) -> FolderRead:
        return await self._mutate_folder(
            node_id=node_id,
            actor_id=actor_id,
            access_action=PermissionAction.DELETE,
            audit_action=AuditAction.FOLDER_DELETED,
            message="Folder moved to trash.",
            operation="delete_folder",
            mutate=lambda uow: uow.folders.soft_delete_folder(
                node_id=node_id,
                deleted_by=actor_id,
                recursive=recursive,
                flush=True,
                refresh=True,
            ),
        )

    async def restore_folder(
        self,
        node_id: UUID,
        *,
        actor_id: UUID,
        recursive: bool = True,
    ) -> FolderRead:
        return await self._mutate_folder(
            node_id=node_id,
            actor_id=actor_id,
            access_action=PermissionAction.DELETE,
            audit_action=AuditAction.FOLDER_RESTORED,
            message="Folder restored.",
            operation="restore_folder",
            allow_deleted=True,
            mutate=lambda uow: uow.folders.restore_folder(
                node_id=node_id,
                updated_by=actor_id,
                recursive=recursive,
                flush=True,
                refresh=True,
            ),
        )

    async def purge_folder(self, node_id: UUID, *, actor_id: UUID) -> None:
        operation = "purge_folder"
        snapshot: dict[str, Any] | None = None

        try:
            async with self.uow_factory() as uow:
                node = await self.access_service.get_accessible_node(
                    node_id=node_id,
                    user_id=actor_id,
                    action=PermissionAction.MANAGE,
                    allow_deleted=True,
                    uow=uow,
                )
                _ensure_folder_node(node, operation=operation)
                folder = await uow.folders.get_required_by_node_id(
                    node.id,
                    include_deleted=True,
                )
                snapshot = _folder_snapshot(folder)
                await uow.nodes.mark_purged(node_id=node.id, flush=True)
                await uow.commit()

            if snapshot is None:
                raise _empty_result_error(operation)
            await self._safe_log_folder_event(
                user_id=actor_id,
                action=AuditAction.FOLDER_PURGED,
                snapshot=snapshot,
                message="Folder permanently deleted.",
            )

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to purge folder."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to purge folder."
            ) from exc

    async def search_folders(
        self,
        *,
        query: str | None,
        user_id: UUID | None,
        owner_id: UUID | None = None,
        parent_id: UUID | None = None,
        include_deleted: bool = False,
        color: str | None = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "name",
        sort_desc: bool = False,
    ) -> PageResponse[FolderListItem]:
        operation = "search_folders"
        page: PageResponse[FolderListItem] | None = None

        try:
            async with self.uow_factory() as uow:
                resolved_owner_id = owner_id or user_id
                if parent_id is not None:
                    parent = await self.access_service.get_accessible_node(
                        node_id=parent_id,
                        user_id=user_id,
                        action=PermissionAction.READ,
                        allow_deleted=include_deleted,
                        uow=uow,
                    )
                    _ensure_folder_node(parent, operation=operation)
                    resolved_owner_id = resolved_owner_id or parent.owner_id
                if resolved_owner_id is None:
                    raise PermissionServiceError(
                        "Folder search requires an authenticated owner or parent folder.",
                        action=PermissionAction.READ,
                        reason="anonymous_user",
                        details={"service": SERVICE_NAME, "operation": operation},
                    )
                if parent_id is None and resolved_owner_id != user_id:
                    raise PermissionServiceError(
                        "User can search only own root folders without parent folder.",
                        user_id=user_id,
                        resource_type="filesystem_root",
                        resource_id=resolved_owner_id,
                        action=PermissionAction.READ,
                        reason="not_owner",
                        details={"service": SERVICE_NAME, "operation": operation},
                    )

                folders = await self._search_all_folders(
                    uow=uow,
                    owner_id=resolved_owner_id,
                    parent_id=parent_id,
                    query=query,
                    include_deleted=include_deleted,
                    color=color,
                    sort_by=_normalize_folder_sort_by(sort_by),
                    sort_direction=_sort_direction(sort_desc),
                )
                page = _folders_page(folders, limit=limit, offset=offset)

            if page is None:
                raise _empty_result_error(operation)
            return page

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to search folders."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to search folders."
            ) from exc

    async def request_folder_archive(
        self,
        data: FolderArchiveRequest,
        *,
        actor_id: UUID,
    ) -> FolderArchiveResponse:
        operation = "request_folder_archive"
        task_snapshot: dict[str, Any] | None = None
        folder_snapshot: dict[str, Any] | None = None

        try:
            async with self.uow_factory() as uow:
                node = await self.access_service.get_accessible_node(
                    node_id=data.folder_id,
                    user_id=actor_id,
                    action=PermissionAction.DOWNLOAD,
                    allow_deleted=data.include_deleted,
                    uow=uow,
                )
                _ensure_folder_node(node, operation=operation)
                folder = await uow.folders.get_required_by_node_id(
                    node.id,
                    include_deleted=data.include_deleted,
                )
                task = await uow.tasks.create_user_task(
                    task_type=BackgroundTaskType.CREATE_FOLDER_ARCHIVE,
                    created_by=actor_id,
                    related_entity_type="folder",
                    related_entity_id=folder.node_id,
                    flush=True,
                    refresh=True,
                )
                task.result_data = {
                    "folder_id": str(folder.node_id),
                    "archive_name": data.archive_name or node.name,
                    "include_deleted": data.include_deleted,
                    "password_protected": data.password is not None,
                }
                folder_snapshot = _folder_snapshot(folder)
                task_snapshot = _task_snapshot(task)
                await uow.commit()

            if task_snapshot is None or folder_snapshot is None:
                raise _empty_result_error(operation)

            await self._safe_log_folder_event(
                user_id=actor_id,
                action=AuditAction.FOLDER_ARCHIVE_REQUESTED,
                snapshot=folder_snapshot,
                message="Folder archive requested.",
                metadata={"task_id": task_snapshot["id"]},
            )
            return FolderArchiveResponse(
                task_id=cast(UUID, task_snapshot["id"]),
                status=cast(BackgroundTaskStatus, task_snapshot["status"]),
            )

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to request folder archive."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to request folder archive."
            ) from exc

    async def count_folders(
        self,
        *,
        owner_id: UUID,
        user_id: UUID,
        include_deleted: bool = False,
    ) -> int:
        operation = "count_folders"
        count: int | None = None

        try:
            if owner_id != user_id:
                raise PermissionServiceError(
                    "User can count only own folders.",
                    user_id=user_id,
                    resource_type="filesystem_root",
                    resource_id=owner_id,
                    action=PermissionAction.READ,
                    reason="not_owner",
                    details={"service": SERVICE_NAME, "operation": operation},
                )

            async with self.uow_factory() as uow:
                count = await uow.folders.count_user_folders(
                    owner_id=owner_id,
                    include_deleted=include_deleted,
                )

            if count is None:
                raise _empty_result_error(operation)
            return count

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to count folders."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to count folders."
            ) from exc

    async def _mutate_folder(
        self,
        *,
        node_id: UUID,
        actor_id: UUID,
        access_action: PermissionAction,
        audit_action: AuditAction,
        message: str,
        operation: str,
        mutate: Any,
        allow_deleted: bool = False,
    ) -> FolderRead:
        snapshot: dict[str, Any] | None = None

        try:
            async with self.uow_factory() as uow:
                node = await self.access_service.get_accessible_node(
                    node_id=node_id,
                    user_id=actor_id,
                    action=access_action,
                    allow_deleted=allow_deleted,
                    uow=uow,
                )
                _ensure_folder_node(node, operation=operation)
                folder = await mutate(uow)
                snapshot = _folder_snapshot(folder)
                await uow.commit()

            if snapshot is None:
                raise _empty_result_error(operation)

            await self._safe_log_folder_event(
                user_id=actor_id,
                action=audit_action,
                snapshot=snapshot,
                message=message,
            )
            return FolderRead.model_validate(snapshot)

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

    async def _load_folders(
        self,
        *,
        uow: Any,
        owner_id: UUID,
        parent_id: UUID | None,
        include_deleted: bool,
        sort_by: FolderSortField,
        sort_direction: NodeSortDirection,
    ) -> list[Folder]:
        folders: list[Folder] = []
        offset = 0

        while True:
            chunk = await uow.folders.list_user_folders(
                owner_id=owner_id,
                parent_id=parent_id,
                include_deleted=include_deleted,
                offset=offset,
                limit=REPOSITORY_PAGE_LIMIT,
                sort_by=sort_by,
                sort_direction=sort_direction,
            )
            folders.extend(chunk)
            if len(chunk) < REPOSITORY_PAGE_LIMIT:
                return folders
            offset += REPOSITORY_PAGE_LIMIT

    async def _search_all_folders(
        self,
        *,
        uow: Any,
        owner_id: UUID,
        query: str | None,
        parent_id: UUID | None,
        include_deleted: bool,
        color: str | None,
        sort_by: FolderSortField,
        sort_direction: NodeSortDirection,
    ) -> list[Folder]:
        folders: list[Folder] = []
        offset = 0

        while True:
            chunk = await uow.folders.search_folders(
                owner_id=owner_id,
                query=query,
                parent_id=parent_id,
                include_deleted=include_deleted,
                color=color,
                offset=offset,
                limit=REPOSITORY_PAGE_LIMIT,
                sort_by=sort_by,
                sort_direction=sort_direction,
            )
            folders.extend(chunk)
            if len(chunk) < REPOSITORY_PAGE_LIMIT:
                return folders
            offset += REPOSITORY_PAGE_LIMIT

    async def _load_child_nodes(
        self,
        *,
        uow: Any,
        parent_id: UUID,
        include_deleted: bool,
        sort_by: str,
        sort_direction: NodeSortDirection,
    ) -> list[FileSystemNode]:
        nodes: list[FileSystemNode] = []
        offset = 0

        while True:
            chunk = await uow.nodes.get_children(
                parent_id=parent_id,
                include_deleted=include_deleted,
                offset=offset,
                limit=REPOSITORY_PAGE_LIMIT,
                sort_by=sort_by,
                sort_direction=sort_direction,
            )
            nodes.extend(chunk)
            if len(chunk) < REPOSITORY_PAGE_LIMIT:
                return nodes
            offset += REPOSITORY_PAGE_LIMIT

    async def _safe_log_folder_event(
        self,
        *,
        user_id: UUID,
        action: AuditAction,
        snapshot: dict[str, Any],
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            merged_metadata = _audit_metadata(snapshot)
            if metadata:
                merged_metadata.update(metadata)
            await self.audit_service.log_user_event(
                user_id=user_id,
                action=action,
                result=AuditResult.SUCCESS,
                entity_type="folder",
                entity_id=cast(UUID, snapshot["node_id"]),
                resource_type=AuditResourceType.FOLDER,
                message=message,
                metadata=merged_metadata,
            )
        except Exception as exc:
            logger.warning(
                "Failed to write folder audit event",
                extra={
                    "action": action.value,
                    "folder_node_id": str(snapshot.get("node_id")),
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


def _folder_snapshot(folder: Folder) -> dict[str, Any]:
    return {
        "id": folder.id,
        "node_id": folder.node_id,
        "description": folder.description,
        "color": folder.color,
        "created_at": folder.created_at,
        "updated_at": folder.updated_at,
        "node": _node_snapshot(folder.node) if folder.node is not None else None,
    }


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


def _task_snapshot(task: BackgroundTask) -> dict[str, Any]:
    return {
        "id": task.id,
        "status": task.status,
    }


def _folders_page(
    folders: list[Folder],
    *,
    limit: int,
    offset: int,
) -> PageResponse[FolderListItem]:
    page_folders = folders[offset : offset + limit]
    items = [
        FolderListItem.model_validate(_folder_snapshot(folder))
        for folder in page_folders
    ]
    return PageResponse(
        items=items,
        meta=PageMeta(
            limit=limit,
            offset=offset,
            total=len(folders),
            count=len(items),
        ),
    )


def _ensure_folder_node(node: FileSystemNode, *, operation: str) -> None:
    if node.node_type == NodeType.FOLDER:
        return
    raise ValidationServiceError(
        "Filesystem node is not a folder.",
        field="node_id",
        value=node.id,
        reason="not_folder",
        details={
            "service": SERVICE_NAME,
            "operation": operation,
            "node_type": node.node_type.value,
        },
    )


def _normalize_folder_sort_by(sort_by: str) -> FolderSortField:
    normalized = sort_by.strip().lower()
    if normalized not in ALLOWED_FOLDER_SORT_FIELDS:
        raise ValidationServiceError(
            "Unsupported folder sort field.",
            field="sort_by",
            value=sort_by,
            reason="unsupported_sort_field",
            details={
                "service": SERVICE_NAME,
                "allowed_values": sorted(ALLOWED_FOLDER_SORT_FIELDS),
            },
        )
    return cast(FolderSortField, normalized)


def _normalize_node_sort_by(sort_by: str) -> str:
    normalized = sort_by.strip().lower()
    allowed = {"name", "created_at", "updated_at", "deleted_at", "depth", "node_type"}
    if normalized not in allowed:
        raise ValidationServiceError(
            "Unsupported node sort field.",
            field="sort_by",
            value=sort_by,
            reason="unsupported_sort_field",
            details={"service": SERVICE_NAME, "allowed_values": sorted(allowed)},
        )
    return normalized


def _sort_direction(sort_desc: bool) -> NodeSortDirection:
    return "desc" if sort_desc else "asc"


def _audit_metadata(snapshot: dict[str, Any]) -> dict[str, Any]:
    node = snapshot.get("node")
    metadata: dict[str, Any] = {
        "folder_id": _jsonable(snapshot.get("id")),
        "node_id": _jsonable(snapshot.get("node_id")),
        "description": snapshot.get("description"),
        "color": snapshot.get("color"),
    }
    if isinstance(node, dict):
        metadata.update(
            {
                "name": node.get("name"),
                "path": node.get("path"),
                "parent_id": _jsonable(node.get("parent_id")),
                "owner_id": _jsonable(node.get("owner_id")),
                "is_deleted": node.get("is_deleted"),
            }
        )
    return metadata


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    return str(value)


def _empty_result_error(operation: str) -> ServiceError:
    return ServiceError(
        "Service operation finished without a result.",
        service=SERVICE_NAME,
        operation=operation,
    )


_folders_service: FoldersService | None = None


def get_folders_service(
    *,
    uow_factory: UnitOfWorkFactory | None = None,
    access_service: AccessService | None = None,
    audit_service: AuditService | None = None,
) -> FoldersService:
    if (
        uow_factory is not None
        or access_service is not None
        or audit_service is not None
    ):
        return FoldersService(
            uow_factory=uow_factory,
            access_service=access_service,
            audit_service=audit_service,
        )

    global _folders_service
    if _folders_service is None:
        _folders_service = FoldersService()
    return _folders_service


__all__ = [
    "FoldersService",
    "get_folders_service",
]
