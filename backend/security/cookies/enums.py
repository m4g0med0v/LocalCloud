from __future__ import annotations

from enum import StrEnum
from typing import Literal


CookieSameSite = Literal["lax", "strict", "none"]


class AuthCookieName(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class CookieErrorCode(StrEnum):
    INVALID_COOKIE_NAME = "invalid_cookie_name"
    INVALID_TOKEN = "invalid_token"
    INVALID_MAX_AGE = "invalid_max_age"
    INVALID_SAMESITE = "invalid_samesite"
    INVALID_SETTINGS = "invalid_settings"


__all__ = ["CookieSameSite", "AuthCookieName", "CookieErrorCode"]
