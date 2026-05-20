from typing import Final


class DatabaseConstants:
    """Значения по умолчанию для настроек PostgreSQL."""

    POSTGRES_DRIVER: Final[str] = "postgresql+asyncpg"
    POSTGRES_HOST: Final[str] = "localhost"
    POSTGRES_PORT: Final[int] = 5432
    POSTGRES_USER: Final[str] = "localcloud"
    POSTGRES_PASSWORD: Final[str] = "localcloud"
    POSTGRES_DB: Final[str] = "localcloud"
    POSTGRES_ECHO: Final[bool] = False
    POSTGRES_POOL_SIZE: Final[int] = 10
    POSTGRES_MAX_OVERFLOW: Final[int] = 20
    POSTGRES_POOL_TIMEOUT: Final[int] = 30
    POSTGRES_POOL_RECYCLE: Final[int] = 1800
    POSTGRES_POOL_PRE_PING: Final[bool] = True
