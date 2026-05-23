from __future__ import annotations

from enum import StrEnum


class PermissionAction(StrEnum):
    READ = "read"
    DOWNLOAD = "download"
    WRITE = "write"
    DELETE = "delete"
    SHARE = "share"
    OWNER = "owner"
    MANAGE = "manage"
    RESTORE = "restore"
    PURGE = "purge"


class PermissionDeniedReason(StrEnum):
    ANONYMOUS_USER = "anonymous_user"
    INACTIVE_USER = "inactive_user"
    DELETED_NODE = "deleted_node"
    NOT_OWNER = "not_owner"
    NOT_ADMIN = "not_admin"
    PERMISSION_NOT_FOUND = "permission_not_found"
    PERMISSION_REVOKED = "permission_revoked"
    PERMISSION_EXPIRED = "permission_expired"
    INSUFFICIENT_PERMISSION = "insufficient_permission"
    PRIVATE_NODE = "private_node"
    INVALID_ACTION = "invalid_action"


class PermissionErrorCode(StrEnum):
    PERMISSION_DENIED = "permission_denied"
    INVALID_ACTION = "invalid_action"
    INVALID_PERMISSION_LEVEL = "invalid_permission_level"
    INVALID_USER = "invalid_user"
    INVALID_NODE = "invalid_node"


__all__ = [
    "PermissionAction",
    "PermissionDeniedReason",
    "PermissionErrorCode",
]
