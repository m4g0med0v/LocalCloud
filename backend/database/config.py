from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

from database.constants import DatabaseConstants as DTC


class DatabaseSettings(BaseSettings):
    """Настройки базы данных."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    postgres_host: str = Field(default=DTC.POSTGRES_HOST, alias="POSTGRES_HOST")
    postgres_port: int = Field(default=DTC.POSTGRES_PORT, alias="POSTGRES_PORT")
    postgres_user: str = Field(default=DTC.POSTGRES_USER, alias="POSTGRES_USER")
    postgres_password: str = Field(
        default=DTC.POSTGRES_PASSWORD,
        alias="POSTGRES_PASSWORD",
    )
    postgres_db: str = Field(default=DTC.POSTGRES_DB, alias="POSTGRES_DB")
    postgres_echo: bool = Field(default=DTC.POSTGRES_ECHO, alias="POSTGRES_ECHO")
    postgres_pool_size: int = Field(
        default=DTC.POSTGRES_POOL_SIZE,
        alias="POSTGRES_POOL_SIZE",
    )
    postgres_max_overflow: int = Field(
        default=DTC.POSTGRES_MAX_OVERFLOW,
        alias="POSTGRES_MAX_OVERFLOW",
    )
    postgres_pool_timeout: int = Field(
        default=DTC.POSTGRES_POOL_TIMEOUT,
        alias="POSTGRES_POOL_TIMEOUT",
    )
    postgres_pool_recycle: int = Field(
        default=DTC.POSTGRES_POOL_RECYCLE,
        alias="POSTGRES_POOL_RECYCLE",
    )
    postgres_pool_pre_ping: bool = Field(
        default=DTC.POSTGRES_POOL_PRE_PING,
        alias="POSTGRES_POOL_PRE_PING",
    )

    @computed_field
    @property
    def database_url(self) -> str:
        """Сформировать SQLAlchemy URL для подключения к PostgreSQL."""
        return str(
            URL.create(
                drivername=DTC.POSTGRES_DRIVER,
                username=self.postgres_user,
                password=self.postgres_password,
                host=self.postgres_host,
                port=self.postgres_port,
                database=self.postgres_db,
            )
        )
