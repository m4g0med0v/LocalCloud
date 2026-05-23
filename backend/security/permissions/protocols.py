from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime
from typing import Protocol

from database.models.enums import NodeVisibility, PermissionLevel, UserStatus


class SupportsUserRole(Protocol):
    code: str
    name: str


class SupportsUser(Protocol):
    id: uuid.UUID
    status: UserStatus | str
    roles: Iterable[SupportsUserRole]


class SupportsNode(Protocol):
    id: uuid.UUID
    owner_id: uuid.UUID
    visibility: NodeVisibility | str
    is_deleted: bool


class SupportsNodePermission(Protocol):
    user_id: uuid.UUID
    permission_level: PermissionLevel | str
    can_read: bool
    can_download: bool
    can_write: bool
    can_delete: bool
    can_share: bool
    revoked_at: datetime | None
    expires_at: datetime | None

    def is_active_at(self, moment: datetime) -> bool: ...


__all__ = [
    "SupportsUserRole",
    "SupportsUser",
    "SupportsNode",
    "SupportsNodePermission",
]
