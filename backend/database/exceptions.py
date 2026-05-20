from __future__ import annotations

from typing import Any


class DatabaseError(Exception):
    """Базовое исключение для ошибок базы данных."""

    def __init__(
        self,
        message: str = "Операция с базой данных не удалась.",
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        self.message = message
        self.details = details.copy() if details else {}
        self.cause = cause

        super().__init__(self.message)

        if cause is not None:
            self.__cause__ = cause

    def __str__(self) -> str:
        """Вернуть человекочитаемое описание ошибки."""
        if not self.details:
            return self.message

        return f"{self.message} Details: {self.details}"

    def to_dict(self) -> dict[str, Any]:
        """Возвращает сериализуемое представление ошибки."""

        payload: dict[str, Any] = {
            "error": self.__class__.__name__,
            "message": self.message,
        }

        if self.details:
            payload["details"] = self.details

        if self.cause is not None:
            payload["cause"] = self.cause.__class__.__name__

        return payload


class DatabaseConnectionError(DatabaseError):
    """Исключение при ошибке подключения к базе данных."""

    def __init__(
        self,
        message: str = "Не удалось подключиться к базе данных.",
        *,
        host: str | None = None,
        port: int | None = None,
        database: str | None = None,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        merged_details = details.copy() if details else {}

        if host is not None:
            merged_details["host"] = host

        if port is not None:
            merged_details["port"] = port

        if database is not None:
            merged_details["database"] = database

        super().__init__(
            message,
            details=merged_details,
            cause=cause,
        )


class DatabaseTimeoutError(DatabaseError):
    """Исключение при превышении времени ожидания операции с БД."""

    def __init__(
        self,
        message: str = "Время выполнения операции с базой данных истекло.",
        *,
        operation: str | None = None,
        timeout_seconds: float | None = None,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        merged_details = details.copy() if details else {}

        if operation is not None:
            merged_details["operation"] = operation

        if timeout_seconds is not None:
            merged_details["timeout_seconds"] = timeout_seconds

        super().__init__(
            message,
            details=merged_details,
            cause=cause,
        )


class TransactionError(DatabaseError):
    """
    Базовое исключение для ошибок транзакций.
    """

    def __init__(
        self,
        message: str = "Транзакция базы данных не удалась.",
        *,
        operation: str | None = None,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        merged_details = details.copy() if details else {}

        if operation is not None:
            merged_details["operation"] = operation

        super().__init__(
            message,
            details=merged_details,
            cause=cause,
        )


class TransactionCommitError(TransactionError):
    """
    Возникает при ошибке фиксации транзакции.
    """

    def __init__(
        self,
        message: str = "Не удалось зафиксировать транзакцию.",
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            operation="commit",
            details=details,
            cause=cause,
        )


class TransactionRollbackError(TransactionError):
    """
    Возникает при ошибке отката транзакции.
    """

    def __init__(
        self,
        message: str = "Не удалось откатить транзакцию.",
        *,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(
            message,
            operation="rollback",
            details=details,
            cause=cause,
        )
