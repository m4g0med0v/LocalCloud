from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator, model_validator

from database.models.enums import PermissionLevel, PermissionSubjectType
from schemas.common import BaseSchema
from security.permissions import PermissionAction, PermissionDeniedReason


class PermissionFlags(BaseSchema):
    """Набор флагов доступа к узлу файловой системы."""

    can_read: bool = Field(
        default=True,
        description="Разрешает просмотр metadata узла и содержимого папки.",
    )
    can_download: bool = Field(
        default=False,
        description="Разрешает скачивание файла или архива папки.",
    )
    can_write: bool = Field(
        default=False,
        description="Разрешает изменение, переименование или загрузку в узел.",
    )
    can_delete: bool = Field(
        default=False,
        description="Разрешает перемещение узла в корзину или окончательное удаление.",
    )
    can_share: bool = Field(
        default=False,
        description="Разрешает выдачу разрешений и создание публичных ссылок.",
    )


class NodePermissionCreate(PermissionFlags):
    """Запрос на создание разрешения доступа к узлу."""

    node_id: UUID = Field(
        ...,
        description="Идентификатор узла файловой системы, для которого выдаётся разрешение.",
    )
    user_id: UUID = Field(
        ...,
        description="Идентификатор пользователя, которому выдаётся разрешение.",
    )
    subject_type: PermissionSubjectType = Field(
        default=PermissionSubjectType.USER,
        description="Тип субъекта доступа.",
    )
    permission_level: PermissionLevel = Field(
        default=PermissionLevel.READ,
        description="Обобщённый уровень доступа.",
    )
    granted_by: UUID | None = Field(
        default=None,
        description="Идентификатор пользователя, который выдал разрешение.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Дата и время истечения срока действия разрешения.",
    )


class NodePermissionUpdate(BaseSchema):
    """Запрос на обновление разрешения доступа к узлу."""

    permission_level: PermissionLevel | None = Field(
        default=None,
        description="Новый обобщённый уровень доступа.",
    )
    can_read: bool | None = Field(
        default=None,
        description="Новое значение флага чтения.",
    )
    can_download: bool | None = Field(
        default=None,
        description="Новое значение флага скачивания.",
    )
    can_write: bool | None = Field(
        default=None,
        description="Новое значение флага записи.",
    )
    can_delete: bool | None = Field(
        default=None,
        description="Новое значение флага удаления.",
    )
    can_share: bool | None = Field(
        default=None,
        description="Новое значение флага управления доступом.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Новая дата истечения срока действия разрешения. None может означать отсутствие срока.",
    )


class NodePermissionRead(BaseSchema):
    """Полное представление разрешения доступа к узлу."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор разрешения.",
    )
    node_id: UUID = Field(
        ...,
        description="Идентификатор узла файловой системы.",
    )
    user_id: UUID = Field(
        ...,
        description="Идентификатор пользователя, которому выдано разрешение.",
    )
    subject_type: PermissionSubjectType = Field(
        ...,
        description="Тип субъекта доступа.",
    )
    permission_level: PermissionLevel = Field(
        ...,
        description="Обобщённый уровень доступа.",
    )
    granted_by: UUID | None = Field(
        default=None,
        description="Идентификатор пользователя, выдавшего разрешение.",
    )
    can_read: bool = Field(
        ...,
        description="Разрешает просмотр metadata узла и содержимого папки.",
    )
    can_download: bool = Field(
        ...,
        description="Разрешает скачивание файла или архива папки.",
    )
    can_write: bool = Field(
        ...,
        description="Разрешает изменение, переименование или загрузку в узел.",
    )
    can_delete: bool = Field(
        ...,
        description="Разрешает перемещение узла в корзину или окончательное удаление.",
    )
    can_share: bool = Field(
        ...,
        description="Разрешает выдачу разрешений и создание публичных ссылок.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Дата и время истечения срока действия разрешения.",
    )
    revoked_at: datetime | None = Field(
        default=None,
        description="Дата и время отзыва разрешения.",
    )
    revoke_reason: str | None = Field(
        default=None,
        description="Причина отзыва разрешения.",
    )
    created_at: datetime = Field(
        ...,
        description="Дата и время создания разрешения.",
    )


class NodePermissionListItem(BaseSchema):
    """Краткое представление разрешения доступа к узлу."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор разрешения.",
    )
    node_id: UUID = Field(
        ...,
        description="Идентификатор узла файловой системы.",
    )
    user_id: UUID = Field(
        ...,
        description="Идентификатор пользователя, которому выдано разрешение.",
    )
    subject_type: PermissionSubjectType = Field(
        ...,
        description="Тип субъекта доступа.",
    )
    permission_level: PermissionLevel = Field(
        ...,
        description="Обобщённый уровень доступа.",
    )
    can_read: bool = Field(
        ...,
        description="Разрешает просмотр metadata узла и содержимого папки.",
    )
    can_download: bool = Field(
        ...,
        description="Разрешает скачивание файла или архива папки.",
    )
    can_write: bool = Field(
        ...,
        description="Разрешает изменение, переименование или загрузку в узел.",
    )
    can_delete: bool = Field(
        ...,
        description="Разрешает перемещение узла в корзину или окончательное удаление.",
    )
    can_share: bool = Field(
        ...,
        description="Разрешает выдачу разрешений и создание публичных ссылок.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Дата и время истечения срока действия разрешения.",
    )
    revoked_at: datetime | None = Field(
        default=None,
        description="Дата и время отзыва разрешения.",
    )
    created_at: datetime = Field(
        ...,
        description="Дата и время создания разрешения.",
    )


class PermissionGrantRequest(PermissionFlags):
    """Запрос на выдачу доступа пользователю к узлу."""

    node_id: UUID = Field(
        ...,
        description="Идентификатор узла файловой системы.",
    )
    user_id: UUID = Field(
        ...,
        description="Идентификатор пользователя, которому выдаётся доступ.",
    )
    permission_level: PermissionLevel = Field(
        default=PermissionLevel.READ,
        description="Обобщённый уровень выдаваемого доступа.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Дата и время истечения доступа. None означает бессрочный доступ.",
    )


class PermissionUpdateRequest(BaseSchema):
    """Запрос на изменение уже выданного доступа."""

    permission_id: UUID | None = Field(
        default=None,
        description="Идентификатор разрешения, которое нужно изменить.",
    )
    node_id: UUID | None = Field(
        default=None,
        description="Идентификатор узла файловой системы. Используется вместе с user_id, если permission_id не передан.",
    )
    user_id: UUID | None = Field(
        default=None,
        description="Идентификатор пользователя. Используется вместе с node_id, если permission_id не передан.",
    )
    permission_level: PermissionLevel | None = Field(
        default=None,
        description="Новый обобщённый уровень доступа.",
    )
    can_read: bool | None = Field(
        default=None,
        description="Новое значение флага чтения.",
    )
    can_download: bool | None = Field(
        default=None,
        description="Новое значение флага скачивания.",
    )
    can_write: bool | None = Field(
        default=None,
        description="Новое значение флага записи.",
    )
    can_delete: bool | None = Field(
        default=None,
        description="Новое значение флага удаления.",
    )
    can_share: bool | None = Field(
        default=None,
        description="Новое значение флага управления доступом.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Новая дата истечения доступа. None может означать бессрочный доступ.",
    )

    @model_validator(mode="after")
    def validate_update_request(self) -> PermissionUpdateRequest:
        if self.permission_id is None and (self.node_id is None or self.user_id is None):
            raise ValueError("Нужно передать permission_id или пару node_id + user_id.")

        update_fields = {
            "permission_level",
            "can_read",
            "can_download",
            "can_write",
            "can_delete",
            "can_share",
            "expires_at",
        }
        if not (self.model_fields_set & update_fields):
            raise ValueError("Нужно передать хотя бы одно поле для изменения разрешения.")

        return self


class PermissionRevokeRequest(BaseSchema):
    """Запрос на отзыв доступа."""

    permission_id: UUID | None = Field(
        default=None,
        description="Идентификатор разрешения, которое нужно отозвать.",
    )
    node_id: UUID | None = Field(
        default=None,
        description="Идентификатор узла файловой системы. Используется вместе с user_id, если permission_id не передан.",
    )
    user_id: UUID | None = Field(
        default=None,
        description="Идентификатор пользователя. Используется вместе с node_id, если permission_id не передан.",
    )
    revoke_reason: str | None = Field(
        default=None,
        max_length=512,
        description="Причина отзыва разрешения.",
    )

    @field_validator("revoke_reason")
    @classmethod
    def normalize_revoke_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None

    @model_validator(mode="after")
    def validate_permission_identifier(self) -> PermissionRevokeRequest:
        if self.permission_id is None and (self.node_id is None or self.user_id is None):
            raise ValueError("Нужно передать permission_id или пару node_id + user_id.")

        return self


class PermissionCheckRequest(BaseSchema):
    """Запрос на проверку доступа пользователя к узлу."""

    node_id: UUID = Field(
        ...,
        description="Идентификатор узла файловой системы.",
    )
    user_id: UUID | None = Field(
        default=None,
        description="Идентификатор пользователя. None может использоваться для проверки публичного доступа.",
    )
    action: PermissionAction = Field(
        ...,
        description="Проверяемое действие.",
    )
    allow_deleted: bool = Field(
        default=False,
        description="Разрешать ли проверку доступа к логически удалённому узлу.",
    )
    allow_public: bool = Field(
        default=True,
        description="Учитывать ли публичную видимость узла при проверке.",
    )


class PermissionCheckResponse(BaseSchema):
    """Результат проверки доступа пользователя к узлу."""

    allowed: bool = Field(
        ...,
        description="Разрешено ли выполнение действия.",
    )
    node_id: UUID = Field(
        ...,
        description="Идентификатор проверенного узла файловой системы.",
    )
    user_id: UUID | None = Field(
        default=None,
        description="Идентификатор пользователя, для которого проверялся доступ.",
    )
    action: PermissionAction = Field(
        ...,
        description="Проверенное действие.",
    )
    permission_level: PermissionLevel | None = Field(
        default=None,
        description="Эффективный уровень доступа, если он определён.",
    )
    denied_reason: PermissionDeniedReason | None = Field(
        default=None,
        description="Причина отказа в доступе, если действие запрещено.",
    )
    message: str | None = Field(
        default=None,
        description="Дополнительное пояснение результата проверки.",
    )


class EffectivePermissionRead(PermissionFlags):
    """Эффективные права пользователя на узел файловой системы."""

    node_id: UUID = Field(
        ...,
        description="Идентификатор узла файловой системы.",
    )
    user_id: UUID | None = Field(
        default=None,
        description="Идентификатор пользователя, для которого рассчитаны эффективные права.",
    )
    permission_level: PermissionLevel | None = Field(
        default=None,
        description="Итоговый обобщённый уровень доступа.",
    )
    source_permission_id: UUID | None = Field(
        default=None,
        description="Идентификатор разрешения, на основе которого рассчитан доступ.",
    )
    is_owner: bool = Field(
        default=False,
        description="Является ли пользователь владельцем узла.",
    )
    is_admin: bool = Field(
        default=False,
        description="Является ли пользователь администратором.",
    )
    is_public: bool = Field(
        default=False,
        description="Получен ли доступ за счёт публичной видимости узла.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Дата и время истечения эффективного доступа, если применимо.",
    )
