from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError as JoseJWTError
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError

from core.config import Settings, get_settings
from security.jwt.dto import JwtPayload
from security.jwt.enums import JwtClaimName, JwtErrorCode, JwtTokenType
from security.jwt.exceptions import (
    JwtExpiredError,
    JwtInvalidClaimsError,
    JwtInvalidTokenTypeError,
    JwtTokenError,
)
from security.jwt.validators import (
    claim_timestamp_to_datetime,
    normalize_datetime,
    normalize_subject,
    normalize_token_type,
    require_claims,
    validate_jwt_settings,
    validate_token_value,
)


def create_access_token(
    subject: str | uuid.UUID,
    *,
    additional_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
    settings: Settings | None = None,
) -> str:
    app_settings = settings or get_settings()
    expiration_delta = expires_delta or timedelta(
        minutes=app_settings.security.access_token_expire_minutes,
    )
    return create_token(
        subject=subject,
        token_type="access",
        expires_delta=expiration_delta,
        additional_claims=additional_claims,
        settings=app_settings,
    )


def create_refresh_token(
    subject: str | uuid.UUID,
    *,
    additional_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
    settings: Settings | None = None,
) -> str:
    app_settings = settings or get_settings()
    expiration_delta = expires_delta or timedelta(
        days=app_settings.security.refresh_token_expire_days,
    )
    return create_token(
        subject=subject,
        token_type="refresh",
        expires_delta=expiration_delta,
        additional_claims=additional_claims,
        settings=app_settings,
    )


def create_token(
    subject: str | uuid.UUID,
    *,
    token_type: JwtTokenType,
    expires_delta: timedelta,
    additional_claims: dict[str, Any] | None = None,
    settings: Settings | None = None,
    issued_at: datetime | None = None,
    jti: str | None = None,
) -> str:
    app_settings = settings or get_settings()
    validate_jwt_settings(app_settings)
    normalized_token_type = normalize_token_type(token_type)
    now = normalize_datetime(issued_at or datetime.now(UTC))
    expires_at = now + expires_delta
    payload: dict[str, Any] = {
        JwtClaimName.SUBJECT.value: normalize_subject(subject),
        JwtClaimName.TOKEN_TYPE.value: normalized_token_type,
        JwtClaimName.JWT_ID.value: jti or generate_jti(),
        JwtClaimName.ISSUED_AT.value: now,
        JwtClaimName.NOT_BEFORE.value: now,
        JwtClaimName.EXPIRES_AT.value: expires_at,
        JwtClaimName.ISSUER.value: app_settings.security.jwt_issuer,
        JwtClaimName.AUDIENCE.value: app_settings.security.jwt_audience,
    }

    if additional_claims:
        reserved_claims = {claim.value for claim in JwtClaimName}
        payload.update(
            {
                key: value
                for key, value in additional_claims.items()
                if key not in reserved_claims
            }
        )

    try:
        return str(
            jwt.encode(
                claims=payload,
                key=app_settings.security.secret_key,
                algorithm=app_settings.security.jwt_algorithm,
            )
        )
    except Exception as exc:
        raise JwtTokenError(
            "Не удалось создать JWT-токен.",
            code=JwtErrorCode.INVALID_TOKEN,
            details={
                "token_type": normalized_token_type,
                "algorithm": app_settings.security.jwt_algorithm,
            },
            cause=exc,
        ) from exc


def decode_token(
    token: str,
    *,
    expected_type: JwtTokenType | None = None,
    settings: Settings | None = None,
    verify_expiration: bool = True,
) -> JwtPayload:
    app_settings = settings or get_settings()
    validate_jwt_settings(app_settings)
    normalized_token = validate_token_value(token)

    try:
        claims = jwt.decode(
            token=normalized_token,
            key=app_settings.security.secret_key,
            algorithms=[app_settings.security.jwt_algorithm],
            issuer=app_settings.security.jwt_issuer,
            audience=app_settings.security.jwt_audience,
            options={
                "verify_signature": True,
                "verify_exp": verify_expiration,
                "verify_nbf": True,
                "verify_iat": True,
                "verify_aud": True,
                "verify_iss": True,
                "require_sub": True,
                "require_exp": True,
                "require_iat": True,
                "require_nbf": True,
            },
        )
    except ExpiredSignatureError as exc:
        raise JwtExpiredError(cause=exc) from exc
    except JWTClaimsError as exc:
        raise JwtInvalidClaimsError(details={"reason": str(exc)}, cause=exc) from exc
    except JoseJWTError as exc:
        raise JwtTokenError(
            "JWT-токен недействителен.",
            code=JwtErrorCode.INVALID_TOKEN,
            details={"reason": str(exc)},
            cause=exc,
        ) from exc
    except Exception as exc:
        raise JwtTokenError(
            "При декодировании JWT-токена возникла непредвиденная ошибка.",
            code=JwtErrorCode.INVALID_TOKEN,
            details={"reason": str(exc), "error_type": exc.__class__.__name__},
            cause=exc,
        ) from exc

    payload = parse_jwt_payload(claims)
    if expected_type is not None:
        require_token_type(payload, expected_type)
    return payload


def decode_access_token(token: str, *, settings: Settings | None = None) -> JwtPayload:
    return decode_token(token, expected_type="access", settings=settings)


def decode_refresh_token(token: str, *, settings: Settings | None = None) -> JwtPayload:
    return decode_token(token, expected_type="refresh", settings=settings)


def parse_jwt_payload(claims: dict[str, Any]) -> JwtPayload:
    if not isinstance(claims, dict):
        raise JwtInvalidClaimsError(
            details={"reason": "claims_is_not_dict", "value_type": type(claims).__name__}
        )

    require_claims(claims)
    subject = claims.get(JwtClaimName.SUBJECT.value)
    if not isinstance(subject, str) or not subject:
        raise JwtTokenError(
            "JWT-токен не содержит корректный subject.",
            code=JwtErrorCode.MISSING_SUBJECT,
            details={"subject": subject},
        )

    jti = claims.get(JwtClaimName.JWT_ID.value)
    if not isinstance(jti, str) or not jti:
        raise JwtTokenError(
            "JWT-токен не содержит корректный jti.",
            code=JwtErrorCode.MISSING_JTI,
            details={"jti": jti},
        )

    issuer = claims.get(JwtClaimName.ISSUER.value)
    audience = claims.get(JwtClaimName.AUDIENCE.value)
    if not isinstance(issuer, str) or not issuer:
        raise JwtInvalidClaimsError(details={"claim": JwtClaimName.ISSUER.value})
    if not isinstance(audience, str) or not audience:
        raise JwtInvalidClaimsError(details={"claim": JwtClaimName.AUDIENCE.value})

    return JwtPayload(
        subject=subject,
        token_type=normalize_token_type(claims.get(JwtClaimName.TOKEN_TYPE.value)),
        jti=jti,
        issued_at=claim_timestamp_to_datetime(
            claims.get(JwtClaimName.ISSUED_AT.value),
            claim_name=JwtClaimName.ISSUED_AT.value,
        ),
        not_before=claim_timestamp_to_datetime(
            claims.get(JwtClaimName.NOT_BEFORE.value),
            claim_name=JwtClaimName.NOT_BEFORE.value,
        ),
        expires_at=claim_timestamp_to_datetime(
            claims.get(JwtClaimName.EXPIRES_AT.value),
            claim_name=JwtClaimName.EXPIRES_AT.value,
        ),
        issuer=issuer,
        audience=audience,
        claims=dict(claims),
    )


def require_token_type(payload: JwtPayload, expected_type: JwtTokenType) -> None:
    normalized_expected_type = normalize_token_type(expected_type)
    if payload.token_type != normalized_expected_type:
        raise JwtInvalidTokenTypeError(
            expected_type=normalized_expected_type,
            actual_type=payload.token_type,
        )


def get_token_subject(
    token: str,
    *,
    expected_type: JwtTokenType | None = None,
    settings: Settings | None = None,
) -> str:
    return decode_token(token, expected_type=expected_type, settings=settings).subject


def get_token_user_id(
    token: str,
    *,
    expected_type: JwtTokenType | None = None,
    settings: Settings | None = None,
) -> uuid.UUID:
    return decode_token(token, expected_type=expected_type, settings=settings).user_id


def get_token_jti(
    token: str,
    *,
    expected_type: JwtTokenType | None = None,
    settings: Settings | None = None,
) -> str:
    return decode_token(token, expected_type=expected_type, settings=settings).jti


def hash_token(token: str, *, settings: Settings | None = None) -> str:
    app_settings = settings or get_settings()
    normalized_token = validate_token_value(token)
    return hmac.new(
        key=app_settings.security.secret_key.encode("utf-8"),
        msg=normalized_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


def verify_token_hash(
    token: str,
    token_hash: str | None,
    *,
    settings: Settings | None = None,
) -> bool:
    if not isinstance(token_hash, str) or not token_hash:
        return False
    return hmac.compare_digest(hash_token(token, settings=settings), token_hash)


def generate_jti() -> str:
    return uuid.uuid4().hex


__all__ = [
    "create_access_token",
    "create_refresh_token",
    "create_token",
    "decode_token",
    "decode_access_token",
    "decode_refresh_token",
    "parse_jwt_payload",
    "require_token_type",
    "get_token_subject",
    "get_token_user_id",
    "get_token_jti",
    "hash_token",
    "verify_token_hash",
    "generate_jti",
]
