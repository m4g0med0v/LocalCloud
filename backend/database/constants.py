import os
from typing import Final

# Scale the pool with available CPU cores; clamp to a safe operational range.
# These are code-level defaults — override via POSTGRES_POOL_SIZE /
# POSTGRES_MAX_OVERFLOW env vars for production tuning.
_CPU_COUNT: Final[int] = os.cpu_count() or 1
_DEFAULT_POOL_SIZE: Final[int] = min(max(_CPU_COUNT * 4, 20), 50)
_DEFAULT_MAX_OVERFLOW: Final[int] = max(_CPU_COUNT * 2, 10)


class DatabaseConstants:
    """Значения по умолчанию для настроек PostgreSQL."""

    POSTGRES_DRIVER: Final[str] = "postgresql+asyncpg"
    POSTGRES_HOST: Final[str] = "localhost"
    POSTGRES_PORT: Final[int] = 5432
    POSTGRES_USER: Final[str] = "localcloud"
    POSTGRES_PASSWORD: Final[str] = "localcloud"
    POSTGRES_DB: Final[str] = "localcloud"
    POSTGRES_ECHO: Final[bool] = False
    POSTGRES_POOL_SIZE: Final[int] = _DEFAULT_POOL_SIZE
    POSTGRES_MAX_OVERFLOW: Final[int] = _DEFAULT_MAX_OVERFLOW
    POSTGRES_POOL_TIMEOUT: Final[int] = 30
    POSTGRES_POOL_RECYCLE: Final[int] = 1800
    POSTGRES_POOL_PRE_PING: Final[bool] = True
