from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from core.config import Settings
from security.jwt.enums import (
    SUPPORTED_JWT_TOKEN_TYPES,
    JwtClaimName,
    JwtErrorCode,
    JwtTokenType,
)
from security.jwt.exceptions import JwtInvalidClaimsError, JwtTokenError


def normalize_subject(subject: str | uuid.UUID) -> str:
    if isinstance(subject, uuid.UUID):
        return str(subject)
    if not isinstance(subject, str):
        raise JwtTokenError(
            "JWT subject должен быть строкой или UUID.",
            code=JwtErrorCode.INVALID_SUBJECT,
            details={"value_type": type(subject).__name__},
        )
    normalized_subject = subject.strip()
    if not normalized_subject:
        raise JwtTokenError(
            "JWT subject не должен быть пустым.",
            code=JwtErrorCode.MISSING_SUBJECT,
        )
    return normalized_subject


def normalize_token_type(token_type: Any) -> JwtTokenType:
    if not isinstance(token_type, str):
        raise JwtInvalidClaimsError(
            "Тип JWT-токена должен быть строкой.",
            details={"token_type": token_type, "value_type": type(token_type).__name__},
        )
    normalized_token_type = token_type.strip().lower()
    if normalized_token_type not in SUPPORTED_JWT_TOKEN_TYPES:
        raise JwtInvalidClaimsError(
            "Тип JWT-токена не поддерживается.",
            details={
                "token_type": token_type,
                "allowed_types": list(SUPPORTED_JWT_TOKEN_TYPES),
            },
        )
    return normalized_token_type  # type: ignore[return-value]


def validate_token_value(token: str) -> str:
    if not isinstance(token, str):
        raise JwtTokenError(
            "JWT-токен должен быть строкой.",
            code=JwtErrorCode.INVALID_TOKEN,
            details={"value_type": type(token).__name__},
        )
    normalized_token = token.strip()
    if not normalized_token:
        raise JwtTokenError(
            "JWT-токен не должен быть пустым.",
            code=JwtErrorCode.INVALID_TOKEN,
        )
    return normalized_token


def validate_jwt_settings(settings: Settings) -> None:
    security = settings.security
    if not isinstance(security.secret_key, str) or len(security.secret_key) < 16:
        raise JwtTokenError(
            "SECRET_KEY должен быть строкой длиной не менее 16 символов.",
            code=JwtErrorCode.INVALID_SETTINGS,
        )
    for field_name in ("jwt_algorithm", "jwt_issuer", "jwt_audience"):
        value = getattr(security, field_name)
        if not isinstance(value, str) or not value.strip():
            raise JwtTokenError(
                f"{field_name.upper()} должен быть непустой строкой.",
                code=JwtErrorCode.INVALID_SETTINGS,
            )
    if security.access_token_expire_minutes <= 0:
        raise JwtTokenError(
            "ACCESS_TOKEN_EXPIRE_MINUTES должен быть больше нуля.",
            code=JwtErrorCode.INVALID_SETTINGS,
            details={
                "access_token_expire_minutes": security.access_token_expire_minutes,
            },
        )
    if security.refresh_token_expire_days <= 0:
        raise JwtTokenError(
            "REFRESH_TOKEN_EXPIRE_DAYS должен быть больше нуля.",
            code=JwtErrorCode.INVALID_SETTINGS,
            details={"refresh_token_expire_days": security.refresh_token_expire_days},
        )


def normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def claim_timestamp_to_datetime(value: Any, *, claim_name: str) -> datetime:
    if isinstance(value, datetime):
        return normalize_datetime(value)
    if isinstance(value, int | float) and not isinstance(value, bool):
        return datetime.fromtimestamp(value, tz=UTC)
    raise JwtInvalidClaimsError(
        "JWT claim должен быть timestamp или datetime.",
        details={
            "claim": claim_name,
            "value": value,
            "value_type": type(value).__name__,
        },
    )


def require_claims(claims: dict[str, Any]) -> None:
    required = (
        JwtClaimName.SUBJECT.value,
        JwtClaimName.JWT_ID.value,
        JwtClaimName.ISSUED_AT.value,
        JwtClaimName.NOT_BEFORE.value,
        JwtClaimName.EXPIRES_AT.value,
        JwtClaimName.ISSUER.value,
        JwtClaimName.AUDIENCE.value,
    )
    missing = [claim for claim in required if claim not in claims]
    if missing:
        raise JwtInvalidClaimsError(details={"missing_claims": missing})


__all__ = [
    "normalize_subject",
    "normalize_token_type",
    "validate_token_value",
    "validate_jwt_settings",
    "normalize_datetime",
    "claim_timestamp_to_datetime",
    "require_claims",
]
