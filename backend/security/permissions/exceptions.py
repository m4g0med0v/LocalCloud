from __future__ import annotations

import uuid
from typing import Any

from security.permissions.enums import (
    PermissionAction,
    PermissionDeniedReason,
    PermissionErrorCode,
)


class PermissionCheckError(Exception):
    def __init__(
        self,
        message: str = "Ошибка проверки прав доступа.",
        *,
        code: PermissionErrorCode = PermissionErrorCode.PERMISSION_DENIED,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.details = details.copy() if details else {}
        self.cause = cause
        super().__init__(self.message)
        if cause is not None:
            self.__cause__ = cause

    def __str__(self) -> str:
        if not self.details:
            return self.message
        return f"{self.message} Details: {self.details}"

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "error": self.__class__.__name__,
            "code": self.code.value,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        if self.cause is not None:
            payload["cause"] = self.cause.__class__.__name__
        return payload


class PermissionDeniedError(PermissionCheckError):
    def __init__(
        self,
        message: str = "Недостаточно прав для выполнения операции.",
        *,
        action: PermissionAction | str | None = None,
        reason: PermissionDeniedReason | str | None = None,
        user_id: uuid.UUID | str | None = None,
        node_id: uuid.UUID | str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged_details = details.copy() if details else {}
        if action is not None:
            merged_details["action"] = str(action)
        if reason is not None:
            merged_details["reason"] = str(reason)
        if user_id is not None:
            merged_details["user_id"] = str(user_id)
        if node_id is not None:
            merged_details["node_id"] = str(node_id)
        super().__init__(
            message,
            code=PermissionErrorCode.PERMISSION_DENIED,
            details=merged_details,
        )


__all__ = ["PermissionCheckError", "PermissionDeniedError"]
