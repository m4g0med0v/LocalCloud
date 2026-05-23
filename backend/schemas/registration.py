from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, EmailStr, Field, field_validator

from database.models.enums import RegistrationRequestStatus
from schemas.common import BaseSchema, PaginationParams

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


class RegistrationRequestCreate(BaseSchema):
    """Запрос на создание заявки на регистрацию."""

    email: EmailStr = Field(
        ...,
        description="Адрес электронной почты, указанный при регистрации.",
        examples=["user@example.com"],
    )
    username: str = Field(
        ...,
        min_length=3,
        max_length=64,
        description="Желаемое имя пользователя.",
        examples=["ivan.petrov"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Пароль пользователя. Хэширование выполняется в service/security-слое.",
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


class RegistrationRequestRead(BaseSchema):
    """Полное безопасное представление заявки на регистрацию."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор заявки на регистрацию.",
    )
    email: EmailStr = Field(
        ...,
        description="Адрес электронной почты, указанный в заявке.",
    )
    username: str = Field(
        ...,
        description="Имя пользователя, указанное в заявке.",
    )
    status: RegistrationRequestStatus = Field(
        ...,
        description="Текущий статус заявки на регистрацию.",
    )
    comment: str | None = Field(
        default=None,
        description="Комментарий администратора при рассмотрении заявки.",
    )
    rejection_reason: str | None = Field(
        default=None,
        description="Причина отклонения заявки.",
    )
    reviewed_at: datetime | None = Field(
        default=None,
        description="Дата и время рассмотрения заявки.",
    )
    reviewed_by: UUID | None = Field(
        default=None,
        description="Идентификатор администратора, рассмотревшего заявку.",
    )
    created_user_id: UUID | None = Field(
        default=None,
        description="Идентификатор созданной учётной записи после одобрения заявки.",
    )
    created_at: datetime = Field(
        ...,
        description="Дата и время создания заявки.",
    )


class RegistrationRequestListItem(BaseSchema):
    """Краткое представление заявки на регистрацию для списков."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор заявки на регистрацию.",
    )
    email: EmailStr = Field(
        ...,
        description="Адрес электронной почты, указанный в заявке.",
    )
    username: str = Field(
        ...,
        description="Имя пользователя, указанное в заявке.",
    )
    status: RegistrationRequestStatus = Field(
        ...,
        description="Текущий статус заявки на регистрацию.",
    )
    reviewed_at: datetime | None = Field(
        default=None,
        description="Дата и время рассмотрения заявки.",
    )
    reviewed_by: UUID | None = Field(
        default=None,
        description="Идентификатор администратора, рассмотревшего заявку.",
    )
    created_user_id: UUID | None = Field(
        default=None,
        description="Идентификатор созданной учётной записи после одобрения заявки.",
    )
    created_at: datetime = Field(
        ...,
        description="Дата и время создания заявки.",
    )


class RegistrationApproveRequest(BaseSchema):
    """Запрос на одобрение заявки на регистрацию."""

    comment: str | None = Field(
        default=None,
        max_length=512,
        description="Комментарий администратора к одобрению заявки.",
    )
    is_email_verified: bool = Field(
        default=True,
        description="Считать ли email пользователя подтверждённым после одобрения.",
    )

    @field_validator("comment")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None


class RegistrationRejectRequest(BaseSchema):
    """Запрос на отклонение заявки на регистрацию."""

    rejection_reason: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Причина отклонения заявки.",
    )
    comment: str | None = Field(
        default=None,
        max_length=512,
        description="Дополнительный комментарий администратора.",
    )

    @field_validator("rejection_reason")
    @classmethod
    def validate_rejection_reason(cls, value: str) -> str:
        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError("Причина отклонения заявки не должна быть пустой.")

        return normalized_value

    @field_validator("comment")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None


class RegistrationCancelRequest(BaseSchema):
    """Запрос на отмену заявки на регистрацию."""

    reason: str | None = Field(
        default=None,
        max_length=512,
        description="Причина отмены заявки.",
    )

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None


class RegistrationQueryParams(PaginationParams):
    """Параметры фильтрации списка заявок на регистрацию."""

    query: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        description="Поисковая строка по email или username.",
    )
    status: RegistrationRequestStatus | None = Field(
        default=None,
        description="Фильтр по статусу заявки.",
    )
    reviewed_by: UUID | None = Field(
        default=None,
        description="Фильтр по администратору, рассмотревшему заявку.",
    )
    created_from: datetime | None = Field(
        default=None,
        description="Фильтр по дате создания: начало диапазона включительно.",
    )
    created_to: datetime | None = Field(
        default=None,
        description="Фильтр по дате создания: конец диапазона включительно.",
    )
    reviewed_from: datetime | None = Field(
        default=None,
        description="Фильтр по дате рассмотрения: начало диапазона включительно.",
    )
    reviewed_to: datetime | None = Field(
        default=None,
        description="Фильтр по дате рассмотрения: конец диапазона включительно.",
    )
    sort_by: str = Field(
        default="created_at",
        max_length=64,
        description="Поле сортировки.",
        examples=["created_at", "reviewed_at", "email", "username", "status"],
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

    @field_validator("reviewed_to")
    @classmethod
    def validate_reviewed_range(
        cls,
        value: datetime | None,
        info: object,
    ) -> datetime | None:
        data = getattr(info, "data", {})
        reviewed_from = data.get("reviewed_from")

        if reviewed_from is not None and value is not None and value < reviewed_from:
            raise ValueError("reviewed_to не может быть раньше reviewed_from.")

        return value


class RegistrationDecisionResponse(BaseSchema):
    """Результат рассмотрения заявки на регистрацию."""

    request: RegistrationRequestRead = Field(
        ...,
        description="Заявка на регистрацию после изменения статуса.",
    )
    created_user_id: UUID | None = Field(
        default=None,
        description="Идентификатор созданного пользователя, если заявка была одобрена.",
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Человекочитаемое сообщение о результате рассмотрения заявки.",
    )
