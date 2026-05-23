from __future__ import annotations

from security.cookies.enums import CookieErrorCode, CookieSameSite
from security.cookies.exceptions import CookieError


def validate_cookie_name(name: str) -> str:
    if not isinstance(name, str):
        raise CookieError(
            "Имя cookie должно быть строкой.",
            code=CookieErrorCode.INVALID_COOKIE_NAME,
            details={"value_type": type(name).__name__},
        )
    normalized_name = name.strip()
    if not normalized_name:
        raise CookieError(
            "Имя cookie не должно быть пустым.",
            code=CookieErrorCode.INVALID_COOKIE_NAME,
        )
    if any(char.isspace() for char in normalized_name):
        raise CookieError(
            "Имя cookie не должно содержать пробельные символы.",
            code=CookieErrorCode.INVALID_COOKIE_NAME,
            details={"cookie_name": normalized_name},
        )
    if any(char in normalized_name for char in (";", ",", "=")):
        raise CookieError(
            "Имя cookie содержит недопустимые символы.",
            code=CookieErrorCode.INVALID_COOKIE_NAME,
            details={"cookie_name": normalized_name},
        )
    return normalized_name


def validate_cookie_value(value: str) -> str:
    if not isinstance(value, str):
        raise CookieError(
            "Значение cookie должно быть строкой.",
            code=CookieErrorCode.INVALID_TOKEN,
            details={"value_type": type(value).__name__},
        )
    normalized_value = value.strip()
    if not normalized_value:
        raise CookieError(
            "Значение cookie не должно быть пустым.",
            code=CookieErrorCode.INVALID_TOKEN,
        )
    return normalized_value


def validate_max_age_seconds(max_age_seconds: int) -> int:
    if not isinstance(max_age_seconds, int) or isinstance(max_age_seconds, bool):
        raise CookieError(
            "max_age cookie должен быть целым числом секунд.",
            code=CookieErrorCode.INVALID_MAX_AGE,
            details={
                "max_age_seconds": max_age_seconds,
                "value_type": type(max_age_seconds).__name__,
            },
        )
    if max_age_seconds <= 0:
        raise CookieError(
            "max_age cookie должен быть больше нуля.",
            code=CookieErrorCode.INVALID_MAX_AGE,
            details={"max_age_seconds": max_age_seconds},
        )
    return max_age_seconds


def normalize_samesite(value: str) -> CookieSameSite:
    if not isinstance(value, str):
        raise CookieError(
            "SameSite cookie должен быть строкой.",
            code=CookieErrorCode.INVALID_SAMESITE,
            details={"value_type": type(value).__name__},
        )
    normalized_value = value.strip().lower()
    if normalized_value not in {"lax", "strict", "none"}:
        raise CookieError(
            "SameSite cookie имеет недопустимое значение.",
            code=CookieErrorCode.INVALID_SAMESITE,
            details={
                "samesite": value,
                "allowed_values": ["lax", "strict", "none"],
            },
        )
    return normalized_value  # type: ignore[return-value]


def normalize_cookie_domain(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise CookieError(
            "Cookie domain должен быть строкой или None.",
            code=CookieErrorCode.INVALID_SETTINGS,
            details={"value_type": type(value).__name__},
        )
    normalized_value = value.strip()
    if not normalized_value:
        return None
    return normalized_value


def normalize_cookie_path(value: str) -> str:
    if not isinstance(value, str):
        raise CookieError(
            "Cookie path должен быть строкой.",
            code=CookieErrorCode.INVALID_SETTINGS,
            details={"value_type": type(value).__name__},
        )
    normalized_value = value.strip()
    if not normalized_value:
        raise CookieError(
            "Cookie path не должен быть пустым.",
            code=CookieErrorCode.INVALID_SETTINGS,
        )
    if not normalized_value.startswith("/"):
        normalized_value = f"/{normalized_value}"
    return normalized_value


__all__ = [
    "validate_cookie_name",
    "validate_cookie_value",
    "validate_max_age_seconds",
    "normalize_samesite",
    "normalize_cookie_domain",
    "normalize_cookie_path",
]
