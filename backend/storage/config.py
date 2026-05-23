from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from storage.constants import StorageConstants as STC


class StorageSettings(BaseSettings):
    """Настройки объектного хранилища MinIO/S3."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    minio_host: str = Field(default=STC.MINIO_HOST, alias="MINIO_HOST")
    minio_port: int = Field(default=STC.MINIO_PORT, alias="MINIO_PORT")
    minio_public_host: str = Field(
        default=STC.MINIO_PUBLIC_HOST,
        alias="MINIO_PUBLIC_HOST",
    )
    minio_public_port: int = Field(
        default=STC.MINIO_PUBLIC_PORT,
        alias="MINIO_PUBLIC_PORT",
    )
    minio_access_key: str = Field(
        default=STC.MINIO_ACCESS_KEY,
        alias="MINIO_ACCESS_KEY",
    )
    minio_secret_key: str = Field(
        default=STC.MINIO_SECRET_KEY,
        alias="MINIO_SECRET_KEY",
    )
    minio_secure: bool = Field(default=STC.MINIO_SECURE, alias="MINIO_SECURE")
    minio_region: str = Field(default=STC.MINIO_REGION, alias="MINIO_REGION")

    @computed_field
    @property
    def minio_endpoint(self) -> str:
        """Возвращает внутренний endpoint MinIO для SDK."""

        return f"{self.minio_host}:{self.minio_port}"

    @computed_field
    @property
    def minio_public_endpoint(self) -> str:
        """Возвращает публичный endpoint MinIO."""

        return f"{self.minio_public_host}:{self.minio_public_port}"

    @computed_field
    @property
    def minio_scheme(self) -> str:
        """Возвращает HTTP-схему подключения к MinIO."""

        return "https" if self.minio_secure else "http"

    @computed_field
    @property
    def minio_base_url(self) -> str:
        """Возвращает базовый URL MinIO."""

        return f"{self.minio_scheme}://{self.minio_endpoint}"

    @computed_field
    @property
    def minio_public_url(self) -> str:
        """Возвращает публичный URL MinIO."""

        return f"{self.minio_scheme}://{self.minio_public_endpoint}"
