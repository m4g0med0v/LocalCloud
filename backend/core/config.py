"""Конфигурация backend-приложения.

Модуль содержит Pydantic-настройки приложения, логирования, безопасности,
JWT, auth-cookie, базы данных и объектного хранилища. Значения настроек
загружаются из переменных окружения и файла `.env`, а при их отсутствии
используются значения по умолчанию из констант приложения.

Также модуль предоставляет кэшированную функцию получения настроек и ленивый
proxy-объект `settings` для безопасного импорта настроек из пакета `core`.

Attributes:
    settings: Ленивый proxy-объект для доступа к текущим настройкам приложения.
"""

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
    """Настройки приложения.

    Описывает базовые параметры backend-приложения: название, версию,
    описание, режим debug и API-префиксы. Значения могут быть переопределены
    через переменные окружения или файл `.env`.

    Attributes:
        app_name: Название приложения.
        app_version: Версия приложения.
        app_description: Описание приложения.
        debug: Признак запуска приложения в debug-режиме.
        api_prefix: Общий префикс API.
        api_v1_prefix: Префикс API версии 1.
    """

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
        """Добавляет ведущий слеш к API-префиксу.

        Нормализует значения `api_prefix` и `api_v1_prefix`, чтобы они всегда
        начинались с символа `/`. Если слеш уже присутствует, значение
        возвращается без изменений.

        Args:
            value: Исходное значение API-префикса.

        Returns:
            API-префикс с ведущим слешем.
        """

        if not value.startswith("/"):
            return f"/{value}"
        return value


class LoggingSettings(BaseSettings):
    """Настройки логирования.

    Описывает уровень логирования, формат вывода логов и параметры записи
    логов в файл. Значения могут быть переопределены через переменные окружения
    или файл `.env`.

    Attributes:
        log_level: Уровень логирования приложения.
        log_json: Признак вывода логов в JSON-формате.
        log_file_enabled: Признак включения записи логов в файл.
        log_file_path: Путь к файлу логов.
    """

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
        """Нормализует уровень логирования.

        Приводит строковое значение уровня логирования из переменных окружения
        к верхнему регистру, чтобы оно соответствовало допустимым значениям
        перечисления уровней логирования.

        Args:
            value: Исходное значение уровня логирования.

        Returns:
            Нормализованное значение уровня логирования.
        """

        if isinstance(value, str):
            return value.upper()
        return value


class SecuritySettings(BaseSettings):
    """Настройки безопасности и JWT.

    Описывает параметры подписи и проверки JWT-токенов, сроки действия access
    и refresh токенов, а также схему хеширования паролей. Значения могут быть
    переопределены через переменные окружения или файл `.env`.

    Attributes:
        secret_key: Секретный ключ для криптографических операций.
        jwt_algorithm: Алгоритм подписи JWT-токенов.
        jwt_issuer: Ожидаемый issuer JWT-токенов.
        jwt_audience: Ожидаемая audience JWT-токенов.
        access_token_expire_minutes: Время жизни access-токена в минутах.
        refresh_token_expire_days: Время жизни refresh-токена в днях.
        password_hash_scheme: Схема хеширования паролей.
    """

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
    """Настройки auth cookie.

    Описывает имена cookie для access и refresh токенов, а также параметры
    безопасности cookie: `secure`, `httponly`, `samesite`, домен и путь.
    Значения могут быть переопределены через переменные окружения или файл
    `.env`.

    Attributes:
        access_cookie_name: Имя cookie для access-токена.
        refresh_cookie_name: Имя cookie для refresh-токена.
        cookie_secure: Признак передачи cookie только по HTTPS.
        cookie_httponly: Признак запрета доступа к cookie из JavaScript.
        cookie_samesite: Политика SameSite для auth-cookie.
        cookie_domain: Домен cookie или `None`, если домен не задан.
        cookie_path: Путь cookie.
    """

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
    """Общие настройки приложения.

    Агрегирует настройки всех основных подсистем backend-приложения:
    приложения, логирования, безопасности, cookie, базы данных и объектного
    хранилища.

    Attributes:
        app: Настройки приложения.
        logging: Настройки логирования.
        security: Настройки безопасности и JWT.
        cookies: Настройки auth-cookie.
        database: Настройки подключения к базе данных.
        storage: Настройки объектного хранилища.
    """

    app: ApplicationSettings = Field(default_factory=ApplicationSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    cookies: CookieSettings = Field(default_factory=CookieSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Возвращает кэшированный экземпляр настроек.

    Создаёт объект `Settings` при первом вызове и переиспользует его при
    последующих обращениях. Это предотвращает повторное чтение переменных
    окружения и файла `.env` в рамках одного процесса приложения.

    Returns:
        Кэшированный экземпляр общих настроек приложения.
    """

    return Settings()


class _SettingsProxy:
    """Ленивый proxy для безопасного импорта настроек.

    Позволяет использовать импорт вида `from core import settings` без
    немедленного создания объекта настроек на этапе импорта модуля. Реальный
    объект настроек создаётся только при обращении к атрибутам proxy.

    Methods:
        __getattr__: Делегирует доступ к атрибутам объекту `Settings`.
        __repr__: Возвращает строковое представление текущих настроек.
    """

    def __getattr__(self, name: str) -> object:
        """Возвращает атрибут текущих настроек.

        Делегирует получение атрибута объекту, возвращаемому `get_settings`.

        Args:
            name: Имя запрашиваемого атрибута настроек.

        Returns:
            Значение атрибута текущих настроек.

        Raises:
            AttributeError: Если запрашиваемый атрибут отсутствует
                в объекте настроек.
        """

        return getattr(get_settings(), name)

    def __repr__(self) -> str:
        """Возвращает строковое представление текущих настроек.

        Returns:
            Строковое представление объекта `Settings`.
        """

        return repr(get_settings())


settings = cast(Settings, _SettingsProxy())
