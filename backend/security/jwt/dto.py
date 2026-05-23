from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from security.jwt.enums import JwtErrorCode, JwtTokenType
from security.jwt.exceptions import JwtTokenError


@dataclass(frozen=True, slots=True)
class JwtPayload:
    subject: str
    token_type: JwtTokenType
    jti: str
    issued_at: datetime
    not_before: datetime
    expires_at: datetime
    issuer: str
    audience: str
    claims: dict[str, Any]

    @property
    def user_id(self) -> uuid.UUID:
        try:
            return uuid.UUID(self.subject)
        except ValueError as exc:
            raise JwtTokenError(
                "JWT subject не является корректным UUID.",
                code=JwtErrorCode.INVALID_SUBJECT,
                details={"subject": self.subject},
                cause=exc,
            ) from exc

    @property
    def is_access_token(self) -> bool:
        return self.token_type == "access"

    @property
    def is_refresh_token(self) -> bool:
        return self.token_type == "refresh"

    def is_expired_at(self, moment: datetime | None = None) -> bool:
        current_moment = moment or datetime.now(UTC)
        return self.expires_at <= current_moment


__all__ = ["JwtPayload"]
