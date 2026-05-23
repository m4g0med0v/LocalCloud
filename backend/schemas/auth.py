from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, EmailStr, Field, field_validator

from schemas.common import BaseSchema
from schemas.users import CurrentUserRead


class LoginRequest(BaseSchema):
    """Запрос на вход в систему."""

    email_or_username: str = Field(
        ...,
        min_length=1,
        max_length=320,
        description="Email или username пользователя.",
        examples=["user@example.com", "ivan.petrov"],
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Пароль пользователя.",
    )

    @field_validator("email_or_username")
    @classmethod
    def normalize_email_or_username(cls, value: str) -> str:
        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError("email_or_username не должен быть пустым.")

        return normalized_value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not value:
            raise ValueError("password не должен быть пустым.")

        return value


class LoginResponse(BaseSchema):
    """Ответ после успешной аутентификации."""

    authenticated: bool = Field(
        default=True,
        description="Признак успешной аутентификации.",
    )
    user: CurrentUserRead = Field(
        ...,
        description="Текущий аутентифицированный пользователь.",
    )
    message: str = Field(
        default="Вход выполнен успешно.",
        description="Сообщение о результате входа.",
    )


class LogoutResponse(BaseSchema):
    """Ответ после выхода из системы."""

    authenticated: bool = Field(
        default=False,
        description="Признак того, что пользователь остаётся аутентифицированным после операции.",
    )
    message: str = Field(
        default="Выход выполнен успешно.",
        description="Сообщение о результате выхода.",
    )


class RefreshTokenResponse(BaseSchema):
    """Ответ после обновления access/refresh token."""

    authenticated: bool = Field(
        default=True,
        description="Признак успешного обновления сессии.",
    )
    user: CurrentUserRead | None = Field(
        default=None,
        description="Текущий пользователь, если сервис возвращает его вместе с обновлением токенов.",
    )
    message: str = Field(
        default="Сессия успешно обновлена.",
        description="Сообщение о результате обновления сессии.",
    )


class TokenPair(BaseSchema):
    """
    Пара access/refresh token.

    Обычно не возвращается клиенту напрямую, потому что токены передаются
    через httpOnly cookies. Схема может использоваться во внутренних тестах
    или сервисных контрактах.
    """

    access_token: str = Field(
        ...,
        min_length=1,
        description="JWT access token.",
    )
    refresh_token: str = Field(
        ...,
        min_length=1,
        description="JWT refresh token.",
    )
    token_type: str = Field(
        default="bearer",
        description="Тип токена.",
        examples=["bearer"],
    )
    access_expires_at: datetime | None = Field(
        default=None,
        description="Дата и время истечения access token.",
    )
    refresh_expires_at: datetime | None = Field(
        default=None,
        description="Дата и время истечения refresh token.",
    )


class JwtPayloadRead(BaseSchema):
    """Безопасное представление полезной нагрузки JWT."""

    sub: str = Field(
        ...,
        min_length=1,
        description="Subject токена. Обычно содержит идентификатор пользователя.",
    )
    user_id: UUID | None = Field(
        default=None,
        description="Идентификатор пользователя, если он был извлечён из subject или claims.",
    )
    token_type: str = Field(
        ...,
        min_length=1,
        description="Тип JWT.",
        examples=["access", "refresh"],
    )
    jti: str | None = Field(
        default=None,
        description="Уникальный идентификатор JWT.",
    )
    iss: str | None = Field(
        default=None,
        description="Issuer токена.",
    )
    aud: str | list[str] | None = Field(
        default=None,
        description="Audience токена.",
    )
    issued_at: datetime | None = Field(
        default=None,
        description="Дата и время выпуска токена.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Дата и время истечения токена.",
    )


class AuthSessionRead(BaseSchema):
    """Безопасное представление пользовательской refresh-сессии."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор сессии или refresh-токена.",
    )
    user_id: UUID = Field(
        ...,
        description="Идентификатор пользователя, которому принадлежит сессия.",
    )
    status: str = Field(
        ...,
        description="Статус сессии.",
        examples=["active", "revoked", "expired"],
    )
    expires_at: datetime = Field(
        ...,
        description="Дата и время истечения refresh-сессии.",
    )
    revoked_at: datetime | None = Field(
        default=None,
        description="Дата и время отзыва сессии.",
    )
    revoke_reason: str | None = Field(
        default=None,
        description="Причина отзыва сессии.",
    )
    replaced_by_token_id: UUID | None = Field(
        default=None,
        description="Идентификатор новой сессии, заменившей текущую при ротации.",
    )
    parent_token_id: UUID | None = Field(
        default=None,
        description="Идентификатор предыдущей сессии, из которой была создана текущая.",
    )
    ip_address: str | None = Field(
        default=None,
        description="IP-адрес, с которого была создана сессия.",
    )
    user_agent: str | None = Field(
        default=None,
        description="User-Agent клиента.",
    )
    device_name: str | None = Field(
        default=None,
        description="Условное имя устройства или клиента.",
    )
    is_active: bool = Field(
        ...,
        description="Признак активности сессии.",
    )
    created_at: datetime = Field(
        ...,
        description="Дата и время создания сессии.",
    )


class PasswordChangeRequest(BaseSchema):
    """Запрос на изменение пароля текущего пользователя."""

    current_password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Текущий пароль пользователя.",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Новый пароль пользователя.",
    )

    @field_validator("current_password")
    @classmethod
    def validate_current_password(cls, value: str) -> str:
        if not value:
            raise ValueError("current_password не должен быть пустым.")

        return value

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if not value:
            raise ValueError("new_password не должен быть пустым.")

        return value


class PasswordResetRequest(BaseSchema):
    """Запрос на начало восстановления пароля."""

    email: EmailStr = Field(
        ...,
        description="Email пользователя, для которого нужно начать восстановление пароля.",
        examples=["user@example.com"],
    )


class PasswordResetConfirmRequest(BaseSchema):
    """Запрос на подтверждение восстановления пароля."""

    token: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="Токен подтверждения восстановления пароля.",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Новый пароль пользователя.",
    )

    @field_validator("token")
    @classmethod
    def validate_token(cls, value: str) -> str:
        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError("token не должен быть пустым.")

        return normalized_value

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if not value:
            raise ValueError("new_password не должен быть пустым.")

        return value
