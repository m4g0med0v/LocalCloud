from __future__ import annotations

from typing import Any

from security.jwt.enums import JwtErrorCode, JwtTokenType


class JwtTokenError(Exception):
    def __init__(
        self,
        message: str = "Ошибка обработки JWT-токена.",
        *,
        code: JwtErrorCode = JwtErrorCode.INVALID_TOKEN,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.details = details.copy() if details else {}
        self.cause = cause
        super().__init__(self.message)
        if cause is not None:
            self.__cause__ = cause

    def __str__(self) -> str:
        if not self.details:
            return self.message
        return f"{self.message} Details: {self.details}"

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "error": self.__class__.__name__,
            "code": self.code.value,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        if self.cause is not None:
            payload["cause"] = self.cause.__class__.__name__
        return payload


class JwtExpiredError(JwtTokenError):
    def __init__(
        self,
        message: str = "Срок действия JWT-токена истёк.",
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code=JwtErrorCode.EXPIRED_TOKEN,
            details=details,
            cause=cause,
        )


class JwtInvalidClaimsError(JwtTokenError):
    def __init__(
        self,
        message: str = "JWT-токен содержит некорректные claims.",
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            code=JwtErrorCode.INVALID_CLAIMS,
            details=details,
            cause=cause,
        )


class JwtInvalidTokenTypeError(JwtTokenError):
    def __init__(
        self,
        *,
        expected_type: JwtTokenType,
        actual_type: str | None,
        message: str | None = None,
    ) -> None:
        super().__init__(
            message or "JWT-токен имеет недопустимый тип.",
            code=JwtErrorCode.INVALID_TOKEN_TYPE,
            details={"expected_type": expected_type, "actual_type": actual_type},
        )


__all__ = [
    "JwtTokenError",
    "JwtExpiredError",
    "JwtInvalidClaimsError",
    "JwtInvalidTokenTypeError",
]
