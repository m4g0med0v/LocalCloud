from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, EmailStr, Field, field_validator

from database.models.enums import UserStatus
from schemas.common import BaseSchema, PaginationParams
from schemas.roles import RoleListItem

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


class UserBase(BaseSchema):
    """Базовые публичные поля пользователя."""

    email: EmailStr = Field(
        ...,
        description="Адрес электронной почты пользователя.",
        examples=["user@example.com"],
    )
    username: str = Field(
        ...,
        min_length=3,
        max_length=64,
        description="Уникальное имя пользователя.",
        examples=["ivan.petrov"],
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError("username не должен быть пустым.")

        if not USERNAME_PATTERN.fullmatch(normalized_value):
            raise ValueError(
                "username может содержать только латинские буквы, цифры, "
                "underscore, точку и дефис."
            )

        return normalized_value


class UserCreate(UserBase):
    """Запрос на создание пользователя администратором."""

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Пароль пользователя. Хэширование выполняется в security/service-слое.",
    )
    status: UserStatus = Field(
        default=UserStatus.PENDING,
        description="Начальный статус учётной записи.",
    )
    is_email_verified: bool = Field(
        default=False,
        description="Признак подтверждения адреса электронной почты.",
    )


class UserUpdate(BaseSchema):
    """Запрос на обновление собственных данных пользователя."""

    email: EmailStr | None = Field(
        default=None,
        description="Новый адрес электронной почты пользователя.",
    )
    username: str | None = Field(
        default=None,
        min_length=3,
        max_length=64,
        description="Новое имя пользователя.",
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError("username не должен быть пустым.")

        if not USERNAME_PATTERN.fullmatch(normalized_value):
            raise ValueError(
                "username может содержать только латинские буквы, цифры, "
                "underscore, точку и дефис."
            )

        return normalized_value


class UserAdminUpdate(UserUpdate):
    """Запрос на административное обновление пользователя."""

    status: UserStatus | None = Field(
        default=None,
        description="Новый статус учётной записи.",
    )
    is_email_verified: bool | None = Field(
        default=None,
        description="Новый признак подтверждения email.",
    )
    block_reason: str | None = Field(
        default=None,
        max_length=512,
        description="Причина блокировки пользователя.",
    )
    rejection_reason: str | None = Field(
        default=None,
        max_length=512,
        description="Причина отклонения пользователя.",
    )

    @field_validator("block_reason", "rejection_reason")
    @classmethod
    def normalize_optional_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None


class UserRead(UserBase):
    """Полное безопасное представление пользователя."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор пользователя.",
    )
    status: UserStatus = Field(
        ...,
        description="Текущий статус учётной записи.",
    )
    is_email_verified: bool = Field(
        ...,
        description="Признак подтверждения адреса электронной почты.",
    )
    last_login_at: datetime | None = Field(
        default=None,
        description="Дата и время последнего успешного входа.",
    )
    approved_at: datetime | None = Field(
        default=None,
        description="Дата и время одобрения регистрации пользователя.",
    )
    blocked_at: datetime | None = Field(
        default=None,
        description="Дата и время блокировки пользователя.",
    )
    rejected_at: datetime | None = Field(
        default=None,
        description="Дата и время отклонения пользователя.",
    )
    deleted_at: datetime | None = Field(
        default=None,
        description="Дата и время логического удаления пользователя.",
    )
    block_reason: str | None = Field(
        default=None,
        description="Причина блокировки пользователя.",
    )
    rejection_reason: str | None = Field(
        default=None,
        description="Причина отклонения пользователя.",
    )
    created_at: datetime = Field(
        ...,
        description="Дата и время создания пользователя.",
    )
    updated_at: datetime = Field(
        ...,
        description="Дата и время последнего обновления пользователя.",
    )


class UserListItem(BaseSchema):
    """Краткое представление пользователя для списков."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор пользователя.",
    )
    email: EmailStr = Field(
        ...,
        description="Адрес электронной почты пользователя.",
    )
    username: str = Field(
        ...,
        description="Уникальное имя пользователя.",
    )
    status: UserStatus = Field(
        ...,
        description="Текущий статус учётной записи.",
    )
    is_email_verified: bool = Field(
        ...,
        description="Признак подтверждения адреса электронной почты.",
    )
    last_login_at: datetime | None = Field(
        default=None,
        description="Дата и время последнего успешного входа.",
    )
    created_at: datetime = Field(
        ...,
        description="Дата и время создания пользователя.",
    )


class CurrentUserRead(BaseSchema):
    """Представление текущего аутентифицированного пользователя."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор текущего пользователя.",
    )
    email: EmailStr = Field(
        ...,
        description="Адрес электронной почты текущего пользователя.",
    )
    username: str = Field(
        ...,
        description="Имя текущего пользователя.",
    )
    status: UserStatus = Field(
        ...,
        description="Текущий статус учётной записи.",
    )
    is_email_verified: bool = Field(
        ...,
        description="Признак подтверждения адреса электронной почты.",
    )
    last_login_at: datetime | None = Field(
        default=None,
        description="Дата и время последнего успешного входа.",
    )
    roles: list[RoleListItem] = Field(
        default_factory=list,
        description="Роли текущего пользователя.",
    )


class UserStatusUpdateRequest(BaseSchema):
    """Запрос на изменение статуса пользователя."""

    status: UserStatus = Field(
        ...,
        description="Новый статус учётной записи.",
    )
    reason: str | None = Field(
        default=None,
        max_length=512,
        description="Причина изменения статуса.",
    )

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None


class UserBlockRequest(BaseSchema):
    """Запрос на блокировку пользователя."""

    reason: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Причина блокировки пользователя.",
    )

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError("Причина блокировки не должна быть пустой.")

        return normalized_value


class UserRejectRequest(BaseSchema):
    """Запрос на отклонение пользователя."""

    reason: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Причина отклонения пользователя.",
    )

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError("Причина отклонения не должна быть пустой.")

        return normalized_value


class UserApproveRequest(BaseSchema):
    """Запрос на одобрение пользователя."""

    is_email_verified: bool = Field(
        default=True,
        description="Нужно ли считать email пользователя подтверждённым после одобрения.",
    )


class UserQueryParams(PaginationParams):
    """Параметры фильтрации списка пользователей."""

    query: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        description="Поисковая строка по email или username.",
    )
    status: UserStatus | None = Field(
        default=None,
        description="Фильтр по статусу пользователя.",
    )
    is_email_verified: bool | None = Field(
        default=None,
        description="Фильтр по признаку подтверждения email.",
    )
    created_from: datetime | None = Field(
        default=None,
        description="Фильтр по дате создания: начало диапазона включительно.",
    )
    created_to: datetime | None = Field(
        default=None,
        description="Фильтр по дате создания: конец диапазона включительно.",
    )
    sort_by: str = Field(
        default="created_at",
        max_length=64,
        description="Поле сортировки.",
        examples=["created_at", "updated_at", "email", "username", "last_login_at"],
    )
    sort_desc: bool = Field(
        default=True,
        description="Сортировать по убыванию.",
    )

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None

    @field_validator("created_to")
    @classmethod
    def validate_created_range(
        cls,
        value: datetime | None,
        info: object,
    ) -> datetime | None:
        data = getattr(info, "data", {})
        created_from = data.get("created_from")

        if created_from is not None and value is not None and value < created_from:
            raise ValueError("created_to не может быть раньше created_from.")

        return value


class UserWithRolesRead(UserRead):
    """Полное представление пользователя вместе с ролями."""

    roles: list[RoleListItem] = Field(
        default_factory=list,
        description="Роли пользователя.",
    )
