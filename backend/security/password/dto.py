from __future__ import annotations

from dataclasses import dataclass

from security.password.enums import PasswordValidationErrorCode


@dataclass(frozen=True, slots=True)
class PasswordValidationError:
    code: PasswordValidationErrorCode
    message: str


@dataclass(frozen=True, slots=True)
class PasswordValidationResult:
    is_valid: bool
    errors: tuple[PasswordValidationError, ...] = ()

    @property
    def messages(self) -> tuple[str, ...]:
        return tuple(error.message for error in self.errors)


__all__ = ["PasswordValidationError", "PasswordValidationResult"]
