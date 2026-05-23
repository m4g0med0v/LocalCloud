from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import cast

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.constants import ApplicationConstants as APC
from core.constants import CookieConstants as CKC
from core.constants import LoggingConstants as LGC
from core.constants import LoggingLevels
from core.constants import SecurityConstants as SCC
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


class SecuritySettings(BaseSettings):
    """Настройки безопасности и JWT."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    secret_key: str = Field(default=SCC.SECRET_KEY, alias="SECRET_KEY")
    jwt_algorithm: str = Field(default=SCC.JWT_ALGORITHM, alias="JWT_ALGORITHM")
    jwt_issuer: str = Field(default=SCC.JWT_ISSUER, alias="JWT_ISSUER")
    jwt_audience: str = Field(default=SCC.JWT_AUDIENCE, alias="JWT_AUDIENCE")
    access_token_expire_minutes: int = Field(
        default=SCC.ACCESS_TOKEN_EXPIRE_MINUTES,
        alias="ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    refresh_token_expire_days: int = Field(
        default=SCC.REFRESH_TOKEN_EXPIRE_DAYS,
        alias="REFRESH_TOKEN_EXPIRE_DAYS",
    )
    password_hash_scheme: str = Field(
        default=SCC.PASSWORD_HASH_SCHEME,
        alias="PASSWORD_HASH_SCHEME",
    )


class CookieSettings(BaseSettings):
    """Настройки auth cookie."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    access_cookie_name: str = Field(
        default=CKC.ACCESS_COOKIE_NAME,
        alias="ACCESS_COOKIE_NAME",
    )
    refresh_cookie_name: str = Field(
        default=CKC.REFRESH_COOKIE_NAME,
        alias="REFRESH_COOKIE_NAME",
    )
    cookie_secure: bool = Field(default=CKC.COOKIE_SECURE, alias="COOKIE_SECURE")
    cookie_httponly: bool = Field(
        default=CKC.COOKIE_HTTPONLY,
        alias="COOKIE_HTTPONLY",
    )
    cookie_samesite: str = Field(default=CKC.COOKIE_SAMESITE, alias="COOKIE_SAMESITE")
    cookie_domain: str | None = Field(
        default=CKC.COOKIE_DOMAIN,
        alias="COOKIE_DOMAIN",
    )
    cookie_path: str = Field(default=CKC.COOKIE_PATH, alias="COOKIE_PATH")


class Settings(BaseModel):
    """Общие настройки приложения."""

    app: ApplicationSettings = Field(default_factory=ApplicationSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    cookies: CookieSettings = Field(default_factory=CookieSettings)
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
