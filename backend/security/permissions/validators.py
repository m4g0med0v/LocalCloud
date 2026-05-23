from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from database.models.enums import NodeVisibility, PermissionLevel
from security.permissions.enums import PermissionAction, PermissionErrorCode
from security.permissions.exceptions import PermissionCheckError
from security.permissions.protocols import SupportsUser


def normalize_permission_action(action: PermissionAction | str) -> PermissionAction:
    if isinstance(action, PermissionAction):
        return action
    if not isinstance(action, str):
        raise PermissionCheckError(
            "Действие доступа должно быть строкой.",
            code=PermissionErrorCode.INVALID_ACTION,
            details={"value_type": type(action).__name__},
        )
    try:
        return PermissionAction(action.strip().lower())
    except ValueError as exc:
        raise PermissionCheckError(
            "Действие доступа не поддерживается.",
            code=PermissionErrorCode.INVALID_ACTION,
            details={
                "action": action,
                "allowed_actions": [item.value for item in PermissionAction],
            },
            cause=exc,
        ) from exc


def normalize_permission_level(permission_level: PermissionLevel | str) -> PermissionLevel:
    if isinstance(permission_level, PermissionLevel):
        return permission_level
    if not isinstance(permission_level, str):
        raise PermissionCheckError(
            "Уровень доступа должен быть строкой.",
            code=PermissionErrorCode.INVALID_PERMISSION_LEVEL,
            details={"value_type": type(permission_level).__name__},
        )
    try:
        return PermissionLevel(permission_level.strip().lower())
    except ValueError as exc:
        raise PermissionCheckError(
            "Уровень доступа не поддерживается.",
            code=PermissionErrorCode.INVALID_PERMISSION_LEVEL,
            details={
                "permission_level": permission_level,
                "allowed_levels": [item.value for item in PermissionLevel],
            },
            cause=exc,
        ) from exc


def normalize_node_visibility(value: NodeVisibility | str | None) -> NodeVisibility:
    if isinstance(value, NodeVisibility):
        return value
    if not isinstance(value, str):
        raise PermissionCheckError(
            "Видимость узла должна быть строкой.",
            code=PermissionErrorCode.INVALID_NODE,
            details={"value_type": type(value).__name__},
        )
    try:
        return NodeVisibility(value.strip().lower())
    except ValueError as exc:
        raise PermissionCheckError(
            "Видимость узла не поддерживается.",
            code=PermissionErrorCode.INVALID_NODE,
            details={
                "visibility": value,
                "allowed_values": [item.value for item in NodeVisibility],
            },
            cause=exc,
        ) from exc


def get_object_uuid(obj: Any, field_name: str) -> uuid.UUID:
    value = getattr(obj, field_name, None)
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str):
        try:
            return uuid.UUID(value)
        except ValueError as exc:
            raise PermissionCheckError(
                f"Поле {field_name} должно быть корректным UUID.",
                details={"field": field_name, "value": value},
                cause=exc,
            ) from exc
    raise PermissionCheckError(
        f"Поле {field_name} должно быть UUID.",
        details={
            "field": field_name,
            "value": value,
            "value_type": type(value).__name__,
        },
    )


def get_optional_user_id(user: SupportsUser | None) -> uuid.UUID | None:
    if user is None:
        return None
    try:
        return get_object_uuid(user, "id")
    except PermissionCheckError:
        return None


def normalize_moment(moment: datetime | None) -> datetime:
    if moment is None:
        return datetime.now(UTC)
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


__all__ = [
    "normalize_permission_action",
    "normalize_permission_level",
    "normalize_node_visibility",
    "get_object_uuid",
    "get_optional_user_id",
    "normalize_moment",
]
