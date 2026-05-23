from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from database.models.enums import PermissionLevel
from security.permissions.enums import PermissionAction, PermissionDeniedReason
from security.permissions.exceptions import PermissionDeniedError


@dataclass(frozen=True, slots=True)
class PermissionCheckResult:
    allowed: bool
    action: PermissionAction
    reason: PermissionDeniedReason | None = None
    user_id: uuid.UUID | None = None
    node_id: uuid.UUID | None = None
    permission_level: PermissionLevel | None = None
    is_admin: bool = False
    is_owner: bool = False
    details: dict[str, Any] | None = None

    @property
    def denied(self) -> bool:
        return not self.allowed

    def raise_if_denied(self) -> None:
        if self.allowed:
            return
        raise PermissionDeniedError(
            action=self.action,
            reason=self.reason,
            user_id=self.user_id,
            node_id=self.node_id,
            details=self.details,
        )


__all__ = ["PermissionCheckResult"]
