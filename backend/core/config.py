from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import cast

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.constants import ApplicationConstants as APC
from core.constants import LoggingConstants as LGC
from core.constants import LoggingLevels
from database.config import DatabaseSettings
from storage.config import StorageSettings


class ApplicationSettings(BaseSettings):
    """Настройки приложения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = Field(default=APC.APP_NAME, alias="APP_NAME")
    app_version: str = Field(default=APC.APP_VERSION, alias="APP_VERSION")
    app_description: str = Field(default=APC.APP_DESCRIPTION, alias="APP_DESCRIPTION")
    debug: bool = Field(default=APC.DEBUG, alias="DEBUG")
    api_prefix: str = Field(default=APC.API_PREFIX, alias="API_PREFIX")
    api_v1_prefix: str = Field(default=APC.API_V1_PREFIX, alias="API_V1_PREFIX")

    @field_validator("api_prefix", "api_v1_prefix")
    @classmethod
    def ensure_leading_slash(cls, value: str) -> str:
        """Добавить ведущий слеш к API-префиксу, если он отсутствует."""
        if not value.startswith("/"):
            return f"/{value}"
        return value


class LoggingSettings(BaseSettings):
    """Настройки логирования."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    log_level: LoggingLevels = Field(
        default=LGC.LOG_LEVEL,
        alias="LOG_LEVEL",
    )
    log_json: bool = Field(default=LGC.LOG_JSON, alias="LOG_JSON")
    log_file_enabled: bool = Field(
        default=LGC.LOG_FILE_ENABLED,
        alias="LOG_FILE_ENABLED",
    )
    log_file_path: Path = Field(default=LGC.LOG_FILE_PATH, alias="LOG_FILE_PATH")

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: object) -> object:
        """Normalize log level names from environment variables."""
        if isinstance(value, str):
            return value.upper()
        return value


class Settings(BaseModel):
    """Общие настройки приложения."""

    app: ApplicationSettings = Field(default_factory=ApplicationSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Вернуть кэшированный экземпляр настроек."""
    return Settings()


class _SettingsProxy:
    """Lazy proxy that keeps ``from core import settings`` import-safe."""

    def __getattr__(self, name: str) -> object:
        return getattr(get_settings(), name)

    def __repr__(self) -> str:
        return repr(get_settings())


settings = cast(Settings, _SettingsProxy())
