from __future__ import annotations

from enum import StrEnum
from typing import Final, Literal


PasswordHashScheme = Literal["bcrypt", "argon2"]


class PasswordValidationErrorCode(StrEnum):
    EMPTY = "empty"
    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"
    MISSING_LETTER = "missing_letter"
    MISSING_DIGIT = "missing_digit"
    MISSING_SPECIAL = "missing_special"
    CONTAINS_WHITESPACE = "contains_whitespace"


SUPPORTED_PASSWORD_HASH_SCHEMES: Final[tuple[PasswordHashScheme, ...]] = (
    "bcrypt",
    "argon2",
)
DEFAULT_MIN_PASSWORD_LENGTH: Final[int] = 8
DEFAULT_MAX_PASSWORD_LENGTH: Final[int] = 128


__all__ = [
    "PasswordHashScheme",
    "PasswordValidationErrorCode",
    "SUPPORTED_PASSWORD_HASH_SCHEMES",
    "DEFAULT_MIN_PASSWORD_LENGTH",
    "DEFAULT_MAX_PASSWORD_LENGTH",
]
