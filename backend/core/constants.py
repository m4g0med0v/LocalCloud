"""Константы конфигурации backend-приложения.

Модуль содержит значения по умолчанию для настроек приложения, логирования,
безопасности, JWT и auth-cookie. Эти константы используются конфигурационными
классами как fallback-значения, если соответствующие параметры не заданы
через переменные окружения или файл `.env`.

Attributes:
    LoggingLevels: Тип допустимых строковых уровней логирования.
"""

from pathlib import Path
from typing import Final, Literal


class ApplicationConstants:
    """Константы приложения.

    Хранит базовые значения конфигурации backend-приложения: название,
    версию, описание, режим debug и API-префиксы.

    Attributes:
        APP_NAME: Название приложения.
        APP_VERSION: Версия приложения.
        APP_DESCRIPTION: Описание приложения.
        DEBUG: Признак запуска приложения в debug-режиме.
        API_PREFIX: Общий префикс API.
        API_V1_PREFIX: Префикс API версии 1.
    """

    APP_NAME: Final[str] = "LocalCloud"
    APP_VERSION: Final[str] = "0.1.0"
    APP_DESCRIPTION: Final[str] = "Веб-приложение для персонального хранения файлов"
    DEBUG: Final[bool] = False
    API_PREFIX: Final[str] = "/api"
    API_V1_PREFIX: Final[str] = "/api/v1"


# Допустимые уровни логирования.
LoggingLevels = Literal[
    "NOTSET", "DEBUG", "INFO", "WARN", "WARNING", "ERROR", "FATAL", "CRITICAL"
]


class LoggingConstants:
    """Константы логирования.

    Хранит значения по умолчанию для настройки логирования приложения:
    уровень логирования, формат вывода, параметры записи в файл и список
    шумных логгеров, уровень которых можно приглушать.

    Attributes:
        LOG_LEVEL: Уровень логирования по умолчанию.
        LOG_JSON: Признак вывода логов в JSON-формате.
        LOG_FILE_ENABLED: Признак включения записи логов в файл.
        LOG_FILE_PATH: Путь к файлу логов.
        DEFAULT_NOISY_LOGGERS: Имена логгеров, которые можно приглушать
            при настройке логирования.
    """

    LOG_LEVEL: Final[LoggingLevels] = "INFO"
    LOG_JSON: Final[bool] = False
    LOG_FILE_ENABLED: Final[bool] = False
    LOG_FILE_PATH: Final[Path] = Path("logs/localcloud.log")
    DEFAULT_NOISY_LOGGERS: Final[tuple[str, ...]] = ("asyncio",)


class SecurityConstants:
    """Константы безопасности приложения.

    Хранит значения по умолчанию для криптографических и JWT-настроек,
    включая секретный ключ, алгоритм подписи, issuer, audience, сроки жизни
    токенов и схему хеширования паролей.

    Attributes:
        SECRET_KEY: Секретный ключ для криптографических операций.
        JWT_ALGORITHM: Алгоритм подписи JWT-токенов.
        JWT_ISSUER: Issuer JWT-токенов.
        JWT_AUDIENCE: Audience JWT-токенов.
        ACCESS_TOKEN_EXPIRE_MINUTES: Время жизни access-токена в минутах.
        REFRESH_TOKEN_EXPIRE_DAYS: Время жизни refresh-токена в днях.
        PASSWORD_HASH_SCHEME: Схема хеширования паролей.
    """

    SECRET_KEY: Final[str] = "localcloud-development-secret-key-change-me"
    JWT_ALGORITHM: Final[str] = "HS256"
    JWT_ISSUER: Final[str] = "localcloud"
    JWT_AUDIENCE: Final[str] = "localcloud-users"
    ACCESS_TOKEN_EXPIRE_MINUTES: Final[int] = 15
    REFRESH_TOKEN_EXPIRE_DAYS: Final[int] = 30
    PASSWORD_HASH_SCHEME: Final[str] = "bcrypt"


class CookieConstants:
    """Константы auth cookie.

    Хранит значения по умолчанию для cookie, используемых при хранении
    access и refresh токенов, а также параметры безопасности cookie.

    Attributes:
        ACCESS_COOKIE_NAME: Имя cookie для access-токена.
        REFRESH_COOKIE_NAME: Имя cookie для refresh-токена.
        COOKIE_SECURE: Признак передачи cookie только по HTTPS.
        COOKIE_HTTPONLY: Признак запрета доступа к cookie из JavaScript.
        COOKIE_SAMESITE: Политика SameSite для auth-cookie.
        COOKIE_DOMAIN: Домен cookie или `None`, если домен не задан.
        COOKIE_PATH: Путь cookie.
    """

    ACCESS_COOKIE_NAME: Final[str] = "localcloud_access"
    REFRESH_COOKIE_NAME: Final[str] = "localcloud_refresh"
    COOKIE_SECURE: Final[bool] = False
    COOKIE_HTTPONLY: Final[bool] = True
    COOKIE_SAMESITE: Final[str] = "lax"
    COOKIE_DOMAIN: Final[str | None] = None
    COOKIE_PATH: Final[str] = "/"
