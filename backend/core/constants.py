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
