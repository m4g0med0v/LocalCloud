from pathlib import Path
from typing import Final, Literal


class ApplicationConstants:
    """Константы приложения."""

    APP_NAME: Final[str] = "LocalCloud"
    APP_VERSION: Final[str] = "0.1.0"
    APP_DESCRIPTION: Final[str] = "Веб-приложение для персонального хранения файлов"
    DEBUG: Final[bool] = False
    API_PREFIX: Final[str] = "/api"
    API_V1_PREFIX: Final[str] = "/api/v1"


# Допустимые уровни логирования
LoggingLevels = Literal[
    "NOTSET", "DEBUG", "INFO", "WARN", "WARNING", "ERROR", "FATAL", "CRITICAL"
]


class LoggingConstants:
    """Константы логирования."""

    LOG_LEVEL: Final[LoggingLevels] = "INFO"
    LOG_JSON: Final[bool] = False
    LOG_FILE_ENABLED: Final[bool] = False
    LOG_FILE_PATH: Final[Path] = Path("logs/localcloud.log")
    DEFAULT_NOISY_LOGGERS: Final[tuple[str, ...]] = ("asyncio",)


class SecurityConstants:
    """Константы безопасности приложения."""

    SECRET_KEY: Final[str] = "localcloud-development-secret-key-change-me"
    JWT_ALGORITHM: Final[str] = "HS256"
    JWT_ISSUER: Final[str] = "localcloud"
    JWT_AUDIENCE: Final[str] = "localcloud-users"
    ACCESS_TOKEN_EXPIRE_MINUTES: Final[int] = 15
    REFRESH_TOKEN_EXPIRE_DAYS: Final[int] = 30
    PASSWORD_HASH_SCHEME: Final[str] = "bcrypt"


class CookieConstants:
    """Константы auth cookie."""

    ACCESS_COOKIE_NAME: Final[str] = "localcloud_access"
    REFRESH_COOKIE_NAME: Final[str] = "localcloud_refresh"
    COOKIE_SECURE: Final[bool] = False
    COOKIE_HTTPONLY: Final[bool] = True
    COOKIE_SAMESITE: Final[str] = "lax"
    COOKIE_DOMAIN: Final[str | None] = None
    COOKIE_PATH: Final[str] = "/"
