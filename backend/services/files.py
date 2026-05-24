from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from core.logging import get_logger
from database import DatabaseError, UnitOfWorkFactory, create_unit_of_work_factory
from database.models.enums import (
    AuditAction,
    AuditResourceType,
    AuditResult,
    FilePreviewStatus,
    FileProcessingStatus,
    FileVersionStatus,
    NodeType,
    NodeVisibility,
    StorageObjectStatus,
)
from database.models.filesystem import File, FileSystemNode, FileVersion
from schemas.common import PageMeta, PageResponse
from schemas.files import (
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

logger = get_logger("services.files")

SERVICE_NAME = "files"
REPOSITORY_PAGE_LIMIT = 1000
ALLOWED_FILE_SORT_FIELDS: set[str] = {
    "name",
    "path",
    "size_bytes",
    "mime_type",
    "extension",
    "created_at",
    "updated_at",
}


@dataclass(frozen=True, slots=True)
class FileMetadataCreate:
    """Input DTO for committing uploaded object metadata as a file node."""

    name: str
    storage_bucket: str
    storage_key: str
    size_bytes: int
    parent_id: UUID | None = None
    mime_type: str | None = None
    extension: str | None = None
    checksum: str | None = None
    checksum_algorithm: str | None = None
    preview_status: FilePreviewStatus = FilePreviewStatus.NOT_REQUIRED
    visibility: NodeVisibility = NodeVisibility.PRIVATE
    change_comment: str | None = None


@dataclass(frozen=True, slots=True)
class FileVersionCreate:
    """Input DTO for adding a new physical object version to an existing file."""

    storage_bucket: str
    storage_key: str
    size_bytes: int
    checksum: str | None = None
    checksum_algorithm: str | None = None
    mime_type: str | None = None
    extension: str | None = None
    change_comment: str | None = None
    make_current: bool = True


class FilesService:
    """Business service for file metadata, versions, movement, and preview state."""

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

    async def create_file_metadata(
        self,
        data: FileMetadataCreate,
        *,
        owner_id: UUID,
        actor_id: UUID | None = None,
    ) -> FileRead:
        """Create a file node, its file metadata row, and the initial version."""

        operation = "create_file_metadata"
        snapshot: dict[str, Any] | None = None
        version_snapshot: dict[str, Any] | None = None
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
                        "Only the owner can create root-level files.",
                        user_id=resolved_actor_id,
                        resource_type="filesystem_root",
                        resource_id=owner_id,
                        action=PermissionAction.WRITE,
                        reason="not_owner",
                        details={"service": SERVICE_NAME, "operation": operation},
                    )

                file = await uow.files.create_file_with_node(
                    owner_id=owner_id,
                    parent_id=data.parent_id,
                    name=data.name,
                    storage_bucket=data.storage_bucket,
                    storage_key=data.storage_key,
                    size_bytes=data.size_bytes,
                    mime_type=data.mime_type,
                    extension=data.extension,
                    checksum=data.checksum,
                    checksum_algorithm=data.checksum_algorithm,
                    storage_status=StorageObjectStatus.AVAILABLE,
                    processing_status=FileProcessingStatus.READY,
                    preview_status=data.preview_status,
                    visibility=data.visibility,
                    created_by=resolved_actor_id,
                    check_owner_exists=True,
                    check_conflict=True,
                    flush=True,
                    refresh=True,
                )
                version = await uow.versions.create_version(
                    file_id=file.id,
                    storage_bucket=data.storage_bucket,
                    storage_key=_version_storage_key(data.storage_key),
                    size_bytes=data.size_bytes,
                    checksum=data.checksum,
                    mime_type=data.mime_type,
                    created_by=resolved_actor_id,
                    change_comment=data.change_comment,
                    is_current=True,
                    update_file_current_version=True,
                    check_file_exists=False,
                    flush=True,
                    refresh=True,
                )
                version.checksum_algorithm = data.checksum_algorithm
                await uow.files.update_current_version(
                    file_id=file.id,
                    current_version_id=version.id,
                    flush=True,
                    refresh=False,
                )
                file = await uow.files.get_required_by_id(file.id)
                snapshot = _file_snapshot(file)
                version_snapshot = _file_version_snapshot(version)
                await uow.commit()

            if snapshot is None:
                raise _empty_result_error(operation)

            await self._safe_log_file_event(
                user_id=resolved_actor_id,
                action=AuditAction.FILE_UPLOADED,
                snapshot=snapshot,
                message="File metadata created.",
                metadata={"version": _jsonable(version_snapshot)},
            )
            return FileRead.model_validate(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to create file metadata."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to create file metadata."
            ) from exc

    async def get_file(
        self,
        node_id: UUID,
        *,
        user_id: UUID | None,
        allow_deleted: bool = False,
        allow_public: bool = True,
    ) -> FileRead:
        operation = "get_file"
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
                _ensure_file_node(node, operation=operation)
                file = await uow.files.get_required_by_node_id(
                    node.id,
                    include_deleted_node=allow_deleted,
                )
                snapshot = _file_snapshot(file)

            if snapshot is None:
                raise _empty_result_error(operation)
            return FileRead.model_validate(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to load file."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to load file."
            ) from exc

    async def get_file_by_id(
        self,
        file_id: UUID,
        *,
        user_id: UUID | None,
        allow_deleted: bool = False,
        allow_public: bool = True,
    ) -> FileRead:
        operation = "get_file_by_id"
        snapshot: dict[str, Any] | None = None

        try:
            async with self.uow_factory() as uow:
                file = await uow.files.get_required_by_id(file_id)
                await self.access_service.require_access(
                    node_id=file.node_id,
                    user_id=user_id,
                    action=PermissionAction.READ,
                    allow_deleted=allow_deleted,
                    allow_public=allow_public,
                    uow=uow,
                )
                if file.node is not None:
                    _ensure_file_node(file.node, operation=operation)
                snapshot = _file_snapshot(file)

            if snapshot is None:
                raise _empty_result_error(operation)
            return FileRead.model_validate(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to load file."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to load file."
            ) from exc

    async def update_file(
        self,
        node_id: UUID,
        data: FileUpdateRequest,
        *,
        actor_id: UUID,
    ) -> FileRead:
        operation = "update_file"
        snapshot: dict[str, Any] | None = None

        try:
            async with self.uow_factory() as uow:
                node = await self.access_service.get_accessible_node(
                    node_id=node_id,
                    user_id=actor_id,
                    action=PermissionAction.WRITE,
                    uow=uow,
                )
                _ensure_file_node(node, operation=operation)
                file = await uow.files.update_metadata(
                    node_id=node.id,
                    mime_type=data.mime_type,
                    extension=data.extension,
                    checksum=data.checksum,
                    checksum_algorithm=data.checksum_algorithm,
                    flush=True,
                    refresh=True,
                )
                snapshot = _file_snapshot(file)
                await uow.commit()

            if snapshot is None:
                raise _empty_result_error(operation)

            await self._safe_log_file_event(
                user_id=actor_id,
                action=AuditAction.FILE_UPDATED,
                snapshot=snapshot,
                message="File metadata updated.",
            )
            return FileRead.model_validate(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to update file metadata."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to update file metadata."
            ) from exc

    async def rename_file(
        self,
        node_id: UUID,
        data: FileRenameRequest,
        *,
        actor_id: UUID,
    ) -> FileRead:
        operation = "rename_file"
        snapshot: dict[str, Any] | None = None

        try:
            async with self.uow_factory() as uow:
                node = await self.access_service.get_accessible_node(
                    node_id=node_id,
                    user_id=actor_id,
                    action=PermissionAction.WRITE,
                    uow=uow,
                )
                _ensure_file_node(node, operation=operation)
                await uow.nodes.rename_node(
                    node_id=node.id,
                    new_name=data.name,
                    updated_by=actor_id,
                    flush=True,
                    refresh=False,
                )
                file = await uow.files.get_required_by_node_id(node.id)
                snapshot = _file_snapshot(file)
                await uow.commit()

            if snapshot is None:
                raise _empty_result_error(operation)

            await self._safe_log_file_event(
                user_id=actor_id,
                action=AuditAction.FILE_RENAMED,
                snapshot=snapshot,
                message="File renamed.",
            )
            return FileRead.model_validate(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to rename file."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to rename file."
            ) from exc

    async def move_file(
        self,
        node_id: UUID,
        data: FileMoveRequest,
        *,
        actor_id: UUID,
    ) -> FileRead:
        operation = "move_file"
        snapshot: dict[str, Any] | None = None

        try:
            async with self.uow_factory() as uow:
                node = await self.access_service.get_accessible_node(
                    node_id=node_id,
                    user_id=actor_id,
                    action=PermissionAction.WRITE,
                    uow=uow,
                )
                _ensure_file_node(node, operation=operation)

                if data.target_parent_id is not None:
                    parent = await self.access_service.get_accessible_node(
                        node_id=data.target_parent_id,
                        user_id=actor_id,
                        action=PermissionAction.WRITE,
                        uow=uow,
                    )
                    _ensure_folder_node(parent, operation=operation)
                    if parent.owner_id != node.owner_id:
                        raise ValidationServiceError(
                            "Target folder belongs to another owner.",
                            field="target_parent_id",
                            value=data.target_parent_id,
                            reason="owner_mismatch",
                            details={"service": SERVICE_NAME, "operation": operation},
                        )
                elif actor_id != node.owner_id:
                    raise PermissionServiceError(
                        "Only the owner can move a file to root level.",
                        user_id=actor_id,
                        resource_type="filesystem_root",
                        resource_id=node.owner_id,
                        action=PermissionAction.WRITE,
                        reason="not_owner",
                        details={"service": SERVICE_NAME, "operation": operation},
                    )

                await uow.nodes.move_node(
                    node_id=node.id,
                    new_parent_id=data.target_parent_id,
                    updated_by=actor_id,
                    flush=True,
                    refresh=False,
                )
                file = await uow.files.get_required_by_node_id(node.id)
                snapshot = _file_snapshot(file)
                await uow.commit()

            if snapshot is None:
                raise _empty_result_error(operation)

            await self._safe_log_file_event(
                user_id=actor_id,
                action=AuditAction.FILE_MOVED,
                snapshot=snapshot,
                message="File moved.",
            )
            return FileRead.model_validate(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to move file."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to move file."
            ) from exc

    async def delete_file(self, node_id: UUID, *, actor_id: UUID) -> FileRead:
        operation = "delete_file"
        snapshot: dict[str, Any] | None = None

        try:
            async with self.uow_factory() as uow:
                node = await self.access_service.get_accessible_node(
                    node_id=node_id,
                    user_id=actor_id,
                    action=PermissionAction.DELETE,
                    uow=uow,
                )
                _ensure_file_node(node, operation=operation)
                await uow.nodes.soft_delete_node(
                    node_id=node.id,
                    deleted_by=actor_id,
                    flush=True,
                    refresh=False,
                )
                file = await uow.files.get_required_by_node_id(
                    node.id,
                    include_deleted_node=True,
                )
                snapshot = _file_snapshot(file)
                await uow.commit()

            if snapshot is None:
                raise _empty_result_error(operation)

            await self._safe_log_file_event(
                user_id=actor_id,
                action=AuditAction.FILE_DELETED,
                snapshot=snapshot,
                message="File moved to trash.",
            )
            return FileRead.model_validate(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to delete file."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to delete file."
            ) from exc

    async def restore_file(self, node_id: UUID, *, actor_id: UUID) -> FileRead:
        operation = "restore_file"
        snapshot: dict[str, Any] | None = None

        try:
            async with self.uow_factory() as uow:
                node = await self.access_service.get_accessible_node(
                    node_id=node_id,
                    user_id=actor_id,
                    action=PermissionAction.DELETE,
                    allow_deleted=True,
                    uow=uow,
                )
                _ensure_file_node(node, operation=operation)
                await uow.nodes.restore_node(
                    node_id=node.id,
                    updated_by=actor_id,
                    flush=True,
                    refresh=False,
                )
                file = await uow.files.get_required_by_node_id(node.id)
                snapshot = _file_snapshot(file)
                await uow.commit()

            if snapshot is None:
                raise _empty_result_error(operation)

            await self._safe_log_file_event(
                user_id=actor_id,
                action=AuditAction.FILE_RESTORED,
                snapshot=snapshot,
                message="File restored from trash.",
            )
            return FileRead.model_validate(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to restore file."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to restore file."
            ) from exc

    async def purge_file(self, node_id: UUID, *, actor_id: UUID) -> None:
        operation = "purge_file"
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
                _ensure_file_node(node, operation=operation)
                file = await uow.files.get_required_by_node_id(
                    node.id,
                    include_deleted_node=True,
                )
                snapshot = _file_snapshot(file)
                await uow.versions.delete_versions_by_file_id(file.id, flush=False)
                await uow.files.delete_by_node_id(node.id, flush=False, required=True)
                await uow.nodes.mark_purged(node_id=node.id, flush=True)
                await uow.commit()

            if snapshot is not None:
                await self._safe_log_file_event(
                    user_id=actor_id,
                    action=AuditAction.FILE_PURGED,
                    snapshot=snapshot,
                    message="File metadata purged.",
                )

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to purge file."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to purge file."
            ) from exc

    async def search_files(
        self,
        params: FileSearchQuery,
        *,
        user_id: UUID | None,
    ) -> PageResponse[FileListItem]:
        operation = "search_files"
        page: PageResponse[FileListItem] | None = None

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
                    _ensure_folder_node(parent, operation=operation)
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
                        "Root-level file search requires an authenticated owner.",
                        action=PermissionAction.READ,
                        reason="anonymous_user",
                        details={"service": SERVICE_NAME, "operation": operation},
                    )
                elif user_id != owner_id:
                    raise PermissionServiceError(
                        "Root-level file search is available only to the owner.",
                        user_id=user_id,
                        resource_type="filesystem_root",
                        resource_id=owner_id,
                        action=PermissionAction.READ,
                        reason="not_owner",
                        details={"service": SERVICE_NAME, "operation": operation},
                    )

                files = await _query_files(uow, params=params, owner_id=owner_id)
                page = _files_page(files, limit=params.limit, offset=params.offset)

            if page is None:
                raise _empty_result_error(operation)
            return page

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to search files."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to search files."
            ) from exc

    async def create_file_version(
        self,
        node_id: UUID,
        data: FileVersionCreate,
        *,
        actor_id: UUID,
    ) -> FileVersionRead:
        operation = "create_file_version"
        snapshot: dict[str, Any] | None = None
        file_snapshot: dict[str, Any] | None = None

        try:
            async with self.uow_factory() as uow:
                node = await self.access_service.get_accessible_node(
                    node_id=node_id,
                    user_id=actor_id,
                    action=PermissionAction.WRITE,
                    uow=uow,
                )
                _ensure_file_node(node, operation=operation)
                file = await uow.files.get_required_by_node_id(node.id)
                version = await uow.versions.create_version(
                    file_id=file.id,
                    storage_bucket=data.storage_bucket,
                    storage_key=data.storage_key,
                    size_bytes=data.size_bytes,
                    checksum=data.checksum,
                    mime_type=data.mime_type,
                    created_by=actor_id,
                    change_comment=data.change_comment,
                    is_current=data.make_current,
                    update_file_current_version=data.make_current,
                    flush=True,
                    refresh=True,
                    check_file_exists=False,
                )
                version.checksum_algorithm = data.checksum_algorithm
                if data.make_current:
                    file = await uow.files.update_metadata(
                        file_id=file.id,
                        size_bytes=data.size_bytes,
                        mime_type=data.mime_type,
                        extension=data.extension,
                        checksum=data.checksum,
                        checksum_algorithm=data.checksum_algorithm,
                        flush=False,
                        refresh=False,
                    )
                    await uow.files.update_storage_info(
                        file_id=file.id,
                        storage_bucket=data.storage_bucket,
                        storage_key=data.storage_key,
                        size_bytes=data.size_bytes,
                        checksum=data.checksum,
                        checksum_algorithm=data.checksum_algorithm,
                        storage_status=StorageObjectStatus.AVAILABLE,
                        flush=True,
                        refresh=True,
                    )
                file = await uow.files.get_required_by_id(file.id)
                snapshot = _file_version_snapshot(version)
                file_snapshot = _file_snapshot(file)
                await uow.commit()

            if snapshot is None:
                raise _empty_result_error(operation)

            if file_snapshot is not None:
                await self._safe_log_file_event(
                    user_id=actor_id,
                    action=AuditAction.FILE_VERSION_CREATED,
                    snapshot=file_snapshot,
                    message="File version created.",
                    metadata={"version": _jsonable(snapshot)},
                )
            return FileVersionRead.model_validate(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to create file version."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to create file version."
            ) from exc

    async def list_versions(
        self,
        node_id: UUID,
        *,
        user_id: UUID | None,
        limit: int = 50,
        offset: int = 0,
    ) -> PageResponse[FileVersionListItem]:
        operation = "list_versions"
        page: PageResponse[FileVersionListItem] | None = None

        try:
            _validate_pagination(limit=limit, offset=offset)
            async with self.uow_factory() as uow:
                node = await self.access_service.get_accessible_node(
                    node_id=node_id,
                    user_id=user_id,
                    action=PermissionAction.READ,
                    uow=uow,
                )
                _ensure_file_node(node, operation=operation)
                file = await uow.files.get_required_by_node_id(node.id)
                versions = await uow.versions.get_versions_by_file_id(
                    file.id,
                    offset=0,
                    limit=REPOSITORY_PAGE_LIMIT,
                    newest_first=True,
                )
                page = _versions_page(versions, limit=limit, offset=offset)

            if page is None:
                raise _empty_result_error(operation)
            return page

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to list file versions."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to list file versions."
            ) from exc

    async def restore_version(
        self,
        node_id: UUID,
        data: FileVersionRestoreRequest,
        *,
        actor_id: UUID,
    ) -> FileRead:
        operation = "restore_version"
        snapshot: dict[str, Any] | None = None
        version_snapshot: dict[str, Any] | None = None

        try:
            async with self.uow_factory() as uow:
                node = await self.access_service.get_accessible_node(
                    node_id=node_id,
                    user_id=actor_id,
                    action=PermissionAction.WRITE,
                    uow=uow,
                )
                _ensure_file_node(node, operation=operation)
                file = await uow.files.get_required_by_node_id(node.id)
                version = await uow.versions.get_required_by_id(data.version_id)
                if version.file_id != file.id:
                    raise ValidationServiceError(
                        "File version does not belong to the requested file.",
                        field="version_id",
                        value=data.version_id,
                        reason="file_version_mismatch",
                        details={"service": SERVICE_NAME, "operation": operation},
                    )
                if version.status == FileVersionStatus.DELETED:
                    raise ValidationServiceError(
                        "Deleted file version cannot be restored.",
                        field="version_id",
                        value=data.version_id,
                        reason="deleted_version",
                        details={"service": SERVICE_NAME, "operation": operation},
                    )

                version = await uow.versions.set_current_version(
                    version_id=version.id,
                    update_file_current_version=True,
                    flush=False,
                    refresh=True,
                )
                if data.change_comment is not None:
                    version = await uow.versions.update_change_comment(
                        version_id=version.id,
                        change_comment=data.change_comment,
                        flush=False,
                        refresh=True,
                    )
                await uow.files.update_storage_info(
                    file_id=file.id,
                    storage_bucket=version.storage_bucket,
                    storage_key=version.storage_key,
                    size_bytes=version.size_bytes,
                    checksum=version.checksum,
                    checksum_algorithm=version.checksum_algorithm,
                    storage_status=StorageObjectStatus.AVAILABLE,
                    flush=False,
                    refresh=False,
                )
                file = await uow.files.update_metadata(
                    file_id=file.id,
                    size_bytes=version.size_bytes,
                    mime_type=version.mime_type,
                    checksum=version.checksum,
                    checksum_algorithm=version.checksum_algorithm,
                    flush=True,
                    refresh=True,
                )
                snapshot = _file_snapshot(file)
                version_snapshot = _file_version_snapshot(version)
                await uow.commit()

            if snapshot is None:
                raise _empty_result_error(operation)

            await self._safe_log_file_event(
                user_id=actor_id,
                action=AuditAction.FILE_VERSION_RESTORED,
                snapshot=snapshot,
                message="File version restored as current.",
                metadata={"version": _jsonable(version_snapshot)},
            )
            return FileRead.model_validate(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to restore file version."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to restore file version."
            ) from exc

    async def get_preview(
        self,
        node_id: UUID,
        *,
        user_id: UUID | None,
    ) -> FilePreviewRead:
        operation = "get_preview"
        preview: FilePreviewRead | None = None

        try:
            async with self.uow_factory() as uow:
                node = await self.access_service.get_accessible_node(
                    node_id=node_id,
                    user_id=user_id,
                    action=PermissionAction.READ,
                    uow=uow,
                )
                _ensure_file_node(node, operation=operation)
                file = await uow.files.get_required_by_node_id(node.id)
                preview = FilePreviewRead(
                    file_id=file.id,
                    preview_status=file.preview_status,
                    preview_available=bool(file.preview_available),
                    presigned_url=None,
                    expires_at=None,
                    mime_type=file.mime_type,
                    message=_preview_message(file),
                )

            if preview is None:
                raise _empty_result_error(operation)
            return preview

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to load file preview state."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to load file preview state."
            ) from exc

    async def mark_preview_pending(
        self,
        node_id: UUID,
        *,
        actor_id: UUID,
    ) -> FileRead:
        return await self._update_preview_state(
            node_id=node_id,
            actor_id=actor_id,
            operation="mark_preview_pending",
            status=FilePreviewStatus.PENDING,
            message="File preview queued.",
        )

    async def mark_preview_generating(
        self,
        node_id: UUID,
        *,
        actor_id: UUID,
    ) -> FileRead:
        return await self._update_preview_state(
            node_id=node_id,
            actor_id=actor_id,
            operation="mark_preview_generating",
            status=FilePreviewStatus.GENERATING,
            message="File preview generation started.",
        )

    async def mark_preview_failed(
        self,
        node_id: UUID,
        *,
        actor_id: UUID,
    ) -> FileRead:
        return await self._update_preview_state(
            node_id=node_id,
            actor_id=actor_id,
            operation="mark_preview_failed",
            status=FilePreviewStatus.FAILED,
            message="File preview generation failed.",
        )

    async def set_preview_ready(
        self,
        node_id: UUID,
        *,
        preview_storage_key: str,
        actor_id: UUID,
    ) -> FileRead:
        return await self._update_preview_state(
            node_id=node_id,
            actor_id=actor_id,
            operation="set_preview_ready",
            status=FilePreviewStatus.READY,
            preview_storage_key=preview_storage_key,
            audit_action=AuditAction.FILE_PREVIEW_GENERATED,
            message="File preview generated.",
        )

    async def _update_preview_state(
        self,
        *,
        node_id: UUID,
        actor_id: UUID,
        operation: str,
        status: FilePreviewStatus,
        message: str,
        preview_storage_key: str | None = None,
        audit_action: AuditAction = AuditAction.FILE_UPDATED,
    ) -> FileRead:
        snapshot: dict[str, Any] | None = None

        try:
            async with self.uow_factory() as uow:
                node = await self.access_service.get_accessible_node(
                    node_id=node_id,
                    user_id=actor_id,
                    action=PermissionAction.WRITE,
                    uow=uow,
                )
                _ensure_file_node(node, operation=operation)
                if status == FilePreviewStatus.READY:
                    file = await uow.files.set_preview_ready(
                        node_id=node.id,
                        preview_storage_key=cast(str, preview_storage_key),
                        flush=True,
                        refresh=True,
                    )
                else:
                    file = await uow.files.update_preview(
                        node_id=node.id,
                        preview_status=status,
                        preview_storage_key=preview_storage_key,
                        flush=True,
                        refresh=True,
                    )
                snapshot = _file_snapshot(file)
                await uow.commit()

            if snapshot is None:
                raise _empty_result_error(operation)

            await self._safe_log_file_event(
                user_id=actor_id,
                action=audit_action,
                snapshot=snapshot,
                message=message,
            )
            return FileRead.model_validate(snapshot)

        except DatabaseError as exc:
            raise self._database_error(
                exc, operation=operation, message="Failed to update preview state."
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc, operation=operation, message="Failed to update preview state."
            ) from exc

    async def _safe_log_file_event(
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
                entity_type="file",
                entity_id=cast(UUID, snapshot["node_id"]),
                resource_type=AuditResourceType.FILE,
                message=message,
                metadata=merged_metadata,
            )
        except Exception as exc:
            logger.warning(
                "Failed to write file audit event",
                extra={
                    "action": action.value,
                    "file_node_id": str(snapshot.get("node_id")),
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


async def _query_files(
    uow: Any,
    *,
    params: FileSearchQuery,
    owner_id: UUID,
) -> list[File]:
    statement = (
        select(File)
        .join(FileSystemNode, File.node_id == FileSystemNode.id)
        .where(
            FileSystemNode.owner_id == owner_id,
            FileSystemNode.node_type == NodeType.FILE,
        )
        .options(selectinload(File.node), selectinload(File.current_version))
    )

    if params.parent_id is not None:
        statement = statement.where(FileSystemNode.parent_id == params.parent_id)
    if not params.include_deleted:
        statement = statement.where(FileSystemNode.is_deleted.is_(False))
    if params.query is not None:
        pattern = f"%{params.query}%"
        statement = statement.where(
            or_(
                FileSystemNode.name.ilike(pattern),
                FileSystemNode.path.ilike(pattern),
                File.mime_type.ilike(pattern),
                File.extension.ilike(pattern),
                File.checksum.ilike(pattern),
            )
        )
    if params.mime_type is not None:
        statement = statement.where(File.mime_type == params.mime_type)
    if params.extension is not None:
        statement = statement.where(File.extension == params.extension)
    if params.storage_status is not None:
        statement = statement.where(File.storage_status == params.storage_status)
    if params.processing_status is not None:
        statement = statement.where(File.processing_status == params.processing_status)
    if params.preview_status is not None:
        statement = statement.where(File.preview_status == params.preview_status)
    if params.min_size_bytes is not None:
        statement = statement.where(File.size_bytes >= params.min_size_bytes)
    if params.max_size_bytes is not None:
        statement = statement.where(File.size_bytes <= params.max_size_bytes)
    if params.created_from is not None:
        statement = statement.where(File.created_at >= params.created_from)
    if params.created_to is not None:
        statement = statement.where(File.created_at <= params.created_to)
    if params.updated_from is not None:
        statement = statement.where(File.updated_at >= params.updated_from)
    if params.updated_to is not None:
        statement = statement.where(File.updated_at <= params.updated_to)

    statement = statement.order_by(_file_sort_column(params.sort_by, params.sort_desc))
    result = await uow.session.execute(statement)
    return list(result.scalars().unique().all())


def _file_snapshot(file: File) -> dict[str, Any]:
    return {
        "id": file.id,
        "node_id": file.node_id,
        "size_bytes": file.size_bytes,
        "mime_type": file.mime_type,
        "extension": file.extension,
        "checksum": file.checksum,
        "checksum_algorithm": file.checksum_algorithm,
        "storage_status": file.storage_status,
        "processing_status": file.processing_status,
        "preview_status": file.preview_status,
        "current_version_id": file.current_version_id,
        "created_at": file.created_at,
        "updated_at": file.updated_at,
        "node": _node_snapshot(file.node) if file.node is not None else None,
    }


def _file_version_snapshot(version: FileVersion) -> dict[str, Any]:
    return {
        "id": version.id,
        "file_id": version.file_id,
        "version_number": version.version_number,
        "status": version.status,
        "size_bytes": version.size_bytes,
        "checksum": version.checksum,
        "checksum_algorithm": version.checksum_algorithm,
        "mime_type": version.mime_type,
        "created_at": version.created_at,
        "created_by": version.created_by,
        "change_comment": version.change_comment,
        "is_current": version.is_current,
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


def _files_page(
    files: list[File],
    *,
    limit: int,
    offset: int,
) -> PageResponse[FileListItem]:
    page_files = files[offset : offset + limit]
    items = [FileListItem.model_validate(_file_snapshot(file)) for file in page_files]
    return PageResponse(
        items=items,
        meta=PageMeta(
            limit=limit,
            offset=offset,
            total=len(files),
            count=len(items),
        ),
    )


def _versions_page(
    versions: list[FileVersion],
    *,
    limit: int,
    offset: int,
) -> PageResponse[FileVersionListItem]:
    page_versions = versions[offset : offset + limit]
    items = [
        FileVersionListItem.model_validate(_file_version_snapshot(version))
        for version in page_versions
    ]
    return PageResponse(
        items=items,
        meta=PageMeta(
            limit=limit,
            offset=offset,
            total=len(versions),
            count=len(items),
        ),
    )


def _ensure_file_node(node: FileSystemNode, *, operation: str) -> None:
    if node.node_type == NodeType.FILE:
        return
    raise ValidationServiceError(
        "Filesystem node is not a file.",
        field="node_id",
        value=node.id,
        reason="not_file",
        details={
            "service": SERVICE_NAME,
            "operation": operation,
            "node_type": node.node_type.value,
        },
    )


def _ensure_folder_node(node: FileSystemNode, *, operation: str) -> None:
    if node.node_type == NodeType.FOLDER:
        return
    raise ValidationServiceError(
        "Filesystem node is not a folder.",
        field="parent_id",
        value=node.id,
        reason="not_folder",
        details={
            "service": SERVICE_NAME,
            "operation": operation,
            "node_type": node.node_type.value,
        },
    )


def _file_sort_column(sort_by: str, sort_desc: bool) -> Any:
    normalized = sort_by.strip().lower()
    if normalized not in ALLOWED_FILE_SORT_FIELDS:
        raise ValidationServiceError(
            "Unsupported file sort field.",
            field="sort_by",
            value=sort_by,
            reason="unsupported_sort_field",
            details={
                "service": SERVICE_NAME,
                "allowed_values": sorted(ALLOWED_FILE_SORT_FIELDS),
            },
        )

    columns: dict[str, Any] = {
        "name": func.lower(FileSystemNode.name),
        "path": func.lower(FileSystemNode.path),
        "size_bytes": File.size_bytes,
        "mime_type": File.mime_type,
        "extension": File.extension,
        "created_at": File.created_at,
        "updated_at": File.updated_at,
    }
    column = columns[normalized]
    return column.desc() if sort_desc else column.asc()


def _validate_pagination(*, limit: int, offset: int) -> None:
    if limit < 1 or limit > REPOSITORY_PAGE_LIMIT:
        raise ValidationServiceError(
            "Invalid pagination limit.",
            field="limit",
            value=limit,
            reason="out_of_range",
            details={"service": SERVICE_NAME, "max_limit": REPOSITORY_PAGE_LIMIT},
        )
    if offset < 0:
        raise ValidationServiceError(
            "Invalid pagination offset.",
            field="offset",
            value=offset,
            reason="negative_offset",
            details={"service": SERVICE_NAME},
        )


def _version_storage_key(storage_key: str) -> str:
    return f"{storage_key}.v1"


def _preview_message(file: File) -> str:
    messages: dict[FilePreviewStatus, str] = {
        FilePreviewStatus.NOT_REQUIRED: "Preview is not required for this file.",
        FilePreviewStatus.PENDING: "Preview generation is queued.",
        FilePreviewStatus.GENERATING: "Preview generation is in progress.",
        FilePreviewStatus.READY: "Preview is ready.",
        FilePreviewStatus.FAILED: "Preview generation failed.",
    }
    return messages[file.preview_status]


def _audit_metadata(snapshot: dict[str, Any]) -> dict[str, Any]:
    node = snapshot.get("node")
    metadata: dict[str, Any] = {
        "file_id": _jsonable(snapshot.get("id")),
        "node_id": _jsonable(snapshot.get("node_id")),
        "size_bytes": snapshot.get("size_bytes"),
        "mime_type": snapshot.get("mime_type"),
        "extension": snapshot.get("extension"),
        "checksum_algorithm": snapshot.get("checksum_algorithm"),
        "storage_status": _jsonable(snapshot.get("storage_status")),
        "processing_status": _jsonable(snapshot.get("processing_status")),
        "preview_status": _jsonable(snapshot.get("preview_status")),
        "current_version_id": _jsonable(snapshot.get("current_version_id")),
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
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, Iterable):
        return [_jsonable(item) for item in value]
    return str(value)


def _empty_result_error(operation: str) -> ServiceError:
    return ServiceError(
        "Service operation finished without a result.",
        service=SERVICE_NAME,
        operation=operation,
    )


_files_service: FilesService | None = None


def get_files_service(
    *,
    uow_factory: UnitOfWorkFactory | None = None,
    access_service: AccessService | None = None,
    audit_service: AuditService | None = None,
) -> FilesService:
    if (
        uow_factory is not None
        or access_service is not None
        or audit_service is not None
    ):
        return FilesService(
            uow_factory=uow_factory,
            access_service=access_service,
            audit_service=audit_service,
        )

    global _files_service
    if _files_service is None:
        _files_service = FilesService()
    return _files_service


__all__ = [
    "FileMetadataCreate",
    "FileVersionCreate",
    "FilesService",
    "get_files_service",
]
