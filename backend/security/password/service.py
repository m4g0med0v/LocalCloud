from __future__ import annotations

from functools import lru_cache

from passlib.context import CryptContext
from passlib.exc import InvalidHashError, UnknownHashError

from core.config import Settings, get_settings
from security.password.enums import PasswordHashScheme
from security.password.validators import (
    normalize_password_hash_scheme,
    validate_password_value,
)


def build_password_context(scheme: str | PasswordHashScheme) -> CryptContext:
    normalized_scheme = normalize_password_hash_scheme(scheme)
    deprecated_scheme = "argon2" if normalized_scheme == "bcrypt" else "bcrypt"
    return CryptContext(
        schemes=[normalized_scheme, deprecated_scheme],
        deprecated=[deprecated_scheme],
        bcrypt__rounds=12,
        argon2__time_cost=3,
        argon2__memory_cost=65536,
        argon2__parallelism=4,
    )


@lru_cache(maxsize=8)
def get_password_context(scheme: str | PasswordHashScheme | None = None) -> CryptContext:
    app_settings = get_settings()
    resolved_scheme = scheme or app_settings.security.password_hash_scheme
    return build_password_context(resolved_scheme)


def hash_password(
    password: str,
    *,
    scheme: str | PasswordHashScheme | None = None,
) -> str:
    normalized_password = validate_password_value(password)
    return str(get_password_context(scheme).hash(normalized_password))


def verify_password(
    plain_password: str,
    password_hash: str | None,
    *,
    scheme: str | PasswordHashScheme | None = None,
) -> bool:
    if not isinstance(plain_password, str):
        return False
    if not isinstance(password_hash, str) or not password_hash.strip():
        return False

    try:
        return bool(get_password_context(scheme).verify(plain_password, password_hash))
    except (InvalidHashError, UnknownHashError, ValueError, TypeError):
        return False


def password_needs_rehash(
    password_hash: str | None,
    *,
    scheme: str | PasswordHashScheme | None = None,
) -> bool:
    if not isinstance(password_hash, str) or not password_hash.strip():
        return True

    try:
        return bool(get_password_context(scheme).needs_update(password_hash))
    except (InvalidHashError, UnknownHashError, ValueError, TypeError):
        return True


def verify_and_update_password_hash(
    plain_password: str,
    password_hash: str | None,
    *,
    scheme: str | PasswordHashScheme | None = None,
) -> tuple[bool, str | None]:
    is_valid = verify_password(
        plain_password=plain_password,
        password_hash=password_hash,
        scheme=scheme,
    )
    if not is_valid:
        return False, None

    if password_needs_rehash(password_hash, scheme=scheme):
        return True, hash_password(plain_password, scheme=scheme)

    return True, None


def get_password_hash_scheme_from_settings(
    settings: Settings | None = None,
) -> PasswordHashScheme:
    app_settings = settings or get_settings()
    return normalize_password_hash_scheme(app_settings.security.password_hash_scheme)


__all__ = [
    "build_password_context",
    "get_password_context",
    "hash_password",
    "verify_password",
    "password_needs_rehash",
    "verify_and_update_password_hash",
    "get_password_hash_scheme_from_settings",
]
