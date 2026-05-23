from __future__ import annotations

from enum import StrEnum
from typing import Final, Literal


JwtTokenType = Literal["access", "refresh"]


class JwtClaimName(StrEnum):
    SUBJECT = "sub"
    TOKEN_TYPE = "type"
    JWT_ID = "jti"
    ISSUED_AT = "iat"
    NOT_BEFORE = "nbf"
    EXPIRES_AT = "exp"
    ISSUER = "iss"
    AUDIENCE = "aud"


class JwtErrorCode(StrEnum):
    INVALID_TOKEN = "invalid_token"
    EXPIRED_TOKEN = "expired_token"
    INVALID_CLAIMS = "invalid_claims"
    INVALID_TOKEN_TYPE = "invalid_token_type"
    MISSING_SUBJECT = "missing_subject"
    MISSING_JTI = "missing_jti"
    INVALID_SUBJECT = "invalid_subject"
    INVALID_SETTINGS = "invalid_settings"


SUPPORTED_JWT_TOKEN_TYPES: Final[tuple[JwtTokenType, ...]] = ("access", "refresh")


__all__ = [
    "JwtTokenType",
    "JwtClaimName",
    "JwtErrorCode",
    "SUPPORTED_JWT_TOKEN_TYPES",
]
