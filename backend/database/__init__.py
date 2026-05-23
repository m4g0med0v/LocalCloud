from database.client import (
    async_engine,
    async_session_factory,
    close_db_client,
    create_session,
    get_async_engine,
    get_async_session_factory,
    get_db_session,
    init_db_client,
    is_db_client_initialized,
    ping_database,
)
from database.config import DatabaseSettings
from database.constants import DatabaseConstants
from database.exceptions import (
    ConstraintViolationError,
    DatabaseConnectionError,
    DatabaseError,
    DatabaseHealthCheckError,
    DatabaseTimeoutError,
    DuplicateEntityError,
    EntityNotFoundError,
    InvalidPaginationError,
    InvalidQueryError,
    RepositoryError,
    TransactionCommitError,
    TransactionError,
    TransactionRollbackError,
    UnitOfWorkError,
)
from database.health import (
    DatabaseHealthStatus,
    check_database_connection,
    check_database_health,
    check_database_latency,
    get_database_health_report,
)
from database.transactions import (
    ensure_transaction_closed,
    nested_transaction,
    readonly_transaction,
    reset_session_state,
    safe_commit,
    safe_flush,
    safe_flush_and_refresh,
    safe_refresh,
    safe_rollback,
    transaction,
)
from database.unit_of_work import (
    UnitOfWork,
    UnitOfWorkFactory,
    create_unit_of_work_factory,
)

__all__ = [
    # Client
    "async_engine",
    "async_session_factory",
    "close_db_client",
    "create_session",
    "get_async_engine",
    "get_async_session_factory",
    "get_db_session",
    "init_db_client",
    "is_db_client_initialized",
    "ping_database",
    # Config
    "DatabaseSettings",
    # Constants
    "DatabaseConstants",
    # Exceptions
    "ConstraintViolationError",
    "DatabaseConnectionError",
    "DatabaseError",
    "DatabaseTimeoutError",
    "DuplicateEntityError",
    "EntityNotFoundError",
    "InvalidPaginationError",
    "InvalidQueryError",
    "RepositoryError",
    "TransactionCommitError",
    "TransactionError",
    "TransactionRollbackError",
    "UnitOfWorkError",
    "DatabaseHealthCheckError",
    # Health
    "DatabaseHealthStatus",
    "check_database_connection",
    "check_database_health",
    "check_database_latency",
    "get_database_health_report",
    # Transactions
    "ensure_transaction_closed",
    "nested_transaction",
    "readonly_transaction",
    "reset_session_state",
    "safe_commit",
    "safe_flush",
    "safe_flush_and_refresh",
    "safe_refresh",
    "safe_rollback",
    "transaction",
    # UnitOfWork
    "UnitOfWork",
    "UnitOfWorkFactory",
    "create_unit_of_work_factory",
]
