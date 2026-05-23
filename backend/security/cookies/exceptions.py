from __future__ import annotations

from security.cookies.enums import CookieErrorCode


class CookieError(Exception):
    def __init__(
        self,
        message: str = "Ошибка работы с cookie.",
        *,
        code: CookieErrorCode = CookieErrorCode.INVALID_SETTINGS,
        details: dict[str, object] | None = None,
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

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "error": self.__class__.__name__,
            "code": self.code.value,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        if self.cause is not None:
            payload["cause"] = self.cause.__class__.__name__
        return payload


__all__ = ["CookieError"]
