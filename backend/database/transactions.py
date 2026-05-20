from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, TypeVar

from sqlalchemy.exc import SQLAlchemyError, TimeoutError
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from database.exceptions import (
    DatabaseTimeoutError,
    TransactionCommitError,
    TransactionError,
    TransactionRollbackError,
)

logger = get_logger("database.transactions")

ModelT = TypeVar("ModelT")


def _build_error_details(
    exc: BaseException,
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Сформировать диагностические данные для ошибки транзакции."""
    details: dict[str, Any] = {
        "original_error": str(exc),
        "original_error_type": exc.__class__.__name__,
    }

    if extra:
        details.update(extra)

    return details


async def _rollback_after_failure(session: AsyncSession) -> dict[str, Any]:
    """Попытаться выполнить rollback после неудачной операции."""
    try:
        await session.rollback()

    except SQLAlchemyError as exc:
        return {
            "rollback_error": str(exc),
            "rollback_error_type": exc.__class__.__name__,
        }

    return {}


async def safe_commit(
    session: AsyncSession,
    *,
    operation: str = "commit",
) -> None:
    """Безопасно зафиксировать текущую транзакцию.

    При ошибке commit выполняется попытка rollback. Затем исходная ошибка
    преобразуется в исключение приложения.

    Args:
        session: Асинхронная SQLAlchemy-сессия.
        operation: Название операции для диагностических данных.

    Raises:
        DatabaseTimeoutError: Если commit завершился по timeout.
        TransactionCommitError: Если commit завершился ошибкой SQLAlchemy.
    """
    try:
        await session.commit()

    except TimeoutError as exc:
        rollback_details = await _rollback_after_failure(session)

        details = _build_error_details(
            exc,
            extra={
                "operation": operation,
                **rollback_details,
            },
        )

        raise DatabaseTimeoutError(
            "Время фиксации транзакции базы данных истекло.",
            operation=operation,
            details=details,
            cause=exc,
        ) from exc

    except SQLAlchemyError as exc:
        rollback_details = await _rollback_after_failure(session)

        details = _build_error_details(
            exc,
            extra={
                "operation": operation,
                **rollback_details,
            },
        )

        raise TransactionCommitError(
            "Не удалось зафиксировать транзакцию базы данных.",
            details=details,
            cause=exc,
        ) from exc


async def safe_rollback(
    session: AsyncSession,
    *,
    operation: str = "rollback",
    suppress_errors: bool = False,
) -> None:
    """Безопасно откатить текущую транзакцию.

    Args:
        session: Асинхронная SQLAlchemy-сессия.
        operation: Название операции для диагностических данных.
        suppress_errors: Подавлять ли ошибку rollback.

    Raises:
        TransactionRollbackError: Если rollback завершился ошибкой и
            suppress_errors=False.
    """
    try:
        await session.rollback()

    except SQLAlchemyError as exc:
        details = _build_error_details(
            exc,
            extra={"operation": operation},
        )

        if suppress_errors:
            logger.warning(
                "Ошибка rollback подавлена",
                extra=details,
            )
            return

        raise TransactionRollbackError(
            "Не удалось выполнить откат транзакции базы данных.",
            details=details,
            cause=exc,
        ) from exc


async def safe_flush(
    session: AsyncSession,
    *,
    operation: str = "flush",
) -> None:
    """Безопасно выполнить flush текущей сессии.

    Flush отправляет накопленные изменения в базу данных без фиксации
    транзакции.

    Args:
        session: Асинхронная SQLAlchemy-сессия.
        operation: Название операции для диагностических данных.

    Raises:
        DatabaseTimeoutError: Если flush завершился по timeout.
        TransactionError: Если flush завершился ошибкой SQLAlchemy.
    """
    try:
        await session.flush()

    except TimeoutError as exc:
        raise DatabaseTimeoutError(
            "Время синхронизации изменений с базой данных истекло.",
            operation=operation,
            details=_build_error_details(
                exc,
                extra={"operation": operation},
            ),
            cause=exc,
        ) from exc

    except SQLAlchemyError as exc:
        raise TransactionError(
            "Не удалось синхронизировать изменения с базой данных.",
            operation=operation,
            details=_build_error_details(
                exc,
                extra={"operation": operation},
            ),
            cause=exc,
        ) from exc


async def safe_refresh(
    session: AsyncSession,
    instance: ModelT,
    *,
    operation: str = "refresh",
    attribute_names: list[str] | None = None,
) -> ModelT:
    """Безопасно обновить ORM-объект данными из базы.

    Args:
        session: Асинхронная SQLAlchemy-сессия.
        instance: ORM-объект, который нужно обновить.
        operation: Название операции для диагностических данных.
        attribute_names: Список атрибутов, которые нужно обновить.

    Returns:
        Тот же ORM-объект после refresh.

    Raises:
        DatabaseTimeoutError: Если refresh завершился по timeout.
        TransactionError: Если refresh завершился ошибкой SQLAlchemy.
    """
    details_extra = {
        "operation": operation,
        "model": instance.__class__.__name__,
        "attribute_names": attribute_names,
    }

    try:
        await session.refresh(instance, attribute_names=attribute_names)
        return instance

    except TimeoutError as exc:
        raise DatabaseTimeoutError(
            "Время обновления объекта из базы данных истекло.",
            operation=operation,
            details=_build_error_details(exc, extra=details_extra),
            cause=exc,
        ) from exc

    except SQLAlchemyError as exc:
        raise TransactionError(
            "Не удалось обновить объект из базы данных.",
            operation=operation,
            details=_build_error_details(exc, extra=details_extra),
            cause=exc,
        ) from exc


async def safe_flush_and_refresh(
    session: AsyncSession,
    instance: ModelT,
    *,
    operation: str = "flush_and_refresh",
    attribute_names: list[str] | None = None,
) -> ModelT:
    """Выполнить flush и refresh указанного ORM-объекта.

    Args:
        session: Асинхронная SQLAlchemy-сессия.
        instance: ORM-объект, который нужно синхронизировать.
        operation: Название операции для диагностических данных.
        attribute_names: Список атрибутов, которые нужно обновить.

    Returns:
        Тот же ORM-объект после flush и refresh.

    Raises:
        DatabaseTimeoutError: Если flush или refresh завершились по timeout.
        TransactionError: Если flush или refresh завершились ошибкой SQLAlchemy.
    """
    await safe_flush(session, operation=f"{operation}.flush")

    return await safe_refresh(
        session,
        instance,
        operation=f"{operation}.refresh",
        attribute_names=attribute_names,
    )


@asynccontextmanager
async def transaction(
    session: AsyncSession,
    *,
    commit_on_exit: bool = True,
    rollback_on_error: bool = True,
    operation: str = "transaction",
) -> AsyncGenerator[AsyncSession]:
    """Создать асинхронный транзакционный context manager.

    По умолчанию при успешном выходе выполняется commit, а при ошибке внутри
    блока выполняется rollback. Ошибка rollback при обработке исходной ошибки
    подавляется и логируется.

    Args:
        session: Асинхронная SQLAlchemy-сессия.
        commit_on_exit: Выполнять ли commit при успешном выходе.
        rollback_on_error: Выполнять ли rollback при ошибке внутри блока.
        operation: Название операции для диагностических данных.

    Yields:
        Переданная SQLAlchemy-сессия.

    Raises:
        DatabaseTimeoutError: Если commit завершился по timeout.
        TransactionCommitError: Если commit завершился ошибкой SQLAlchemy.
    """
    try:
        yield session

    except Exception:
        if rollback_on_error:
            await safe_rollback(
                session,
                operation=f"{operation}.rollback",
                suppress_errors=True,
            )
        raise

    else:
        if commit_on_exit:
            await safe_commit(
                session,
                operation=f"{operation}.commit",
            )


@asynccontextmanager
async def readonly_transaction(
    session: AsyncSession,
    *,
    rollback_on_exit: bool = True,
    operation: str = "readonly_transaction",
) -> AsyncGenerator[AsyncSession]:
    """Создать context manager для read-only сценариев.

    Для SELECT-запросов commit обычно не нужен. При выходе можно выполнить
    rollback, чтобы закрыть неявно открытую транзакцию.

    Args:
        session: Асинхронная SQLAlchemy-сессия.
        rollback_on_exit: Выполнять ли rollback при выходе.
        operation: Название операции для диагностических данных.

    Yields:
        Переданная SQLAlchemy-сессия.
    """
    try:
        yield session

    except Exception:
        await safe_rollback(
            session,
            operation=f"{operation}.rollback_after_error",
            suppress_errors=True,
        )

        raise

    finally:
        if rollback_on_exit and session.in_transaction():
            await safe_rollback(
                session,
                operation=f"{operation}.rollback_on_exit",
                suppress_errors=True,
            )


@asynccontextmanager
async def nested_transaction(
    session: AsyncSession,
    *,
    operation: str = "nested_transaction",
) -> AsyncGenerator[AsyncSession]:
    """Создать context manager для вложенной транзакции SAVEPOINT.

    Args:
        session: Асинхронная SQLAlchemy-сессия.
        operation: Название операции для диагностических данных.

    Yields:
        Переданная SQLAlchemy-сессия.

    Raises:
        DatabaseTimeoutError: Если SAVEPOINT завершился по timeout.
        TransactionError: Если SAVEPOINT завершился ошибкой SQLAlchemy.
    """
    try:
        async with session.begin_nested():
            yield session

    except TimeoutError as exc:
        raise DatabaseTimeoutError(
            "Время выполнения вложенной транзакции истекло.",
            operation=operation,
            details=_build_error_details(
                exc,
                extra={"operation": operation},
            ),
            cause=exc,
        ) from exc

    except SQLAlchemyError as exc:
        raise TransactionError(
            "Вложенная транзакция базы данных не удалась.",
            operation=operation,
            details=_build_error_details(
                exc,
                extra={"operation": operation},
            ),
            cause=exc,
        ) from exc


async def ensure_transaction_closed(
    session: AsyncSession,
    *,
    operation: str = "ensure_transaction_closed",
) -> None:
    """Откатить активную транзакцию, если она есть.

    Args:
        session: Асинхронная SQLAlchemy-сессия.
        operation: Название операции для диагностических данных.

    Raises:
        TransactionRollbackError: Если rollback завершился ошибкой.
    """
    if not session.in_transaction():
        return

    await safe_rollback(
        session,
        operation=operation,
    )


async def reset_session_state(
    session: AsyncSession,
    *,
    operation: str = "reset_session_state",
) -> None:
    """Привести сессию в безопасное состояние.

    Если есть активная транзакция, выполняется rollback. Затем очищается
    identity map через expunge_all().

    Args:
        session: Асинхронная SQLAlchemy-сессия.
        operation: Название операции для диагностических данных.

    Raises:
        TransactionRollbackError: Если rollback завершился ошибкой.
    """
    if session.in_transaction():
        await safe_rollback(
            session,
            operation=f"{operation}.rollback",
        )

    session.expunge_all()
