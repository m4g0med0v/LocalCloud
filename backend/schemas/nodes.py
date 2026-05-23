from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator

from database.models.enums import NodeType, NodeVisibility
from schemas.common import BaseSchema, PaginationParams

FORBIDDEN_NODE_NAME_CHARS = {"/", "\\", "\x00"}


def validate_node_name(value: str) -> str:
    """Проверяет и нормализует имя узла файловой системы."""

    normalized_value = value.strip()

    if not normalized_value:
        raise ValueError("Имя узла не должно быть пустым.")

    if any(char in normalized_value for char in FORBIDDEN_NODE_NAME_CHARS):
        raise ValueError("Имя узла не должно содержать '/', '\\' или NUL-символ.")

    if normalized_value in {".", ".."}:
        raise ValueError("Имя узла не может быть '.' или '..'.")

    return normalized_value


class NodeBase(BaseSchema):
    """Базовые поля узла файловой системы."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Имя файла или папки, отображаемое пользователю.",
        examples=["Документы", "report.pdf"],
    )
    parent_id: UUID | None = Field(
        default=None,
        description="Идентификатор родительской папки. None означает корневой уровень.",
    )
    visibility: NodeVisibility = Field(
        default=NodeVisibility.PRIVATE,
        description="Видимость узла файловой системы.",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return validate_node_name(value)


class NodeCreate(NodeBase):
    """Запрос на создание узла файловой системы."""

    node_type: NodeType = Field(
        ...,
        description="Тип создаваемого узла файловой системы.",
    )


class NodeUpdate(BaseSchema):
    """Запрос на обновление общих данных узла файловой системы."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Новое имя узла файловой системы.",
    )
    parent_id: UUID | None = Field(
        default=None,
        description="Новый идентификатор родительской папки. None означает перенос в корень.",
    )
    visibility: NodeVisibility | None = Field(
        default=None,
        description="Новая видимость узла файловой системы.",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return validate_node_name(value)


class NodeRenameRequest(BaseSchema):
    """Запрос на переименование узла файловой системы."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Новое имя файла или папки.",
        examples=["Новый отчёт.pdf"],
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return validate_node_name(value)


class NodeMoveRequest(BaseSchema):
    """Запрос на перемещение узла файловой системы."""

    target_parent_id: UUID | None = Field(
        default=None,
        description="Идентификатор целевой родительской папки. None означает перемещение в корень.",
    )


class NodeRead(BaseSchema):
    """Полное представление узла файловой системы."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор узла файловой системы.",
    )
    owner_id: UUID = Field(
        ...,
        description="Идентификатор владельца узла.",
    )
    parent_id: UUID | None = Field(
        default=None,
        description="Идентификатор родительской папки. None означает корневой уровень.",
    )
    name: str = Field(
        ...,
        description="Имя файла или папки, отображаемое пользователю.",
    )
    node_type: NodeType = Field(
        ...,
        description="Тип узла файловой системы.",
    )
    visibility: NodeVisibility = Field(
        ...,
        description="Видимость узла файловой системы.",
    )
    path: str = Field(
        ...,
        description="Материализованный логический путь узла.",
    )
    depth: int = Field(
        ...,
        ge=0,
        description="Глубина вложенности узла.",
    )
    created_by: UUID | None = Field(
        default=None,
        description="Идентификатор пользователя, создавшего узел.",
    )
    updated_by: UUID | None = Field(
        default=None,
        description="Идентификатор пользователя, последним изменившего узел.",
    )
    deleted_by: UUID | None = Field(
        default=None,
        description="Идентификатор пользователя, удалившего узел.",
    )
    created_at: datetime = Field(
        ...,
        description="Дата и время создания узла.",
    )
    updated_at: datetime = Field(
        ...,
        description="Дата и время последнего обновления узла.",
    )
    is_deleted: bool = Field(
        ...,
        description="Признак логического удаления узла.",
    )
    deleted_at: datetime | None = Field(
        default=None,
        description="Дата и время логического удаления узла.",
    )


class NodeListItem(BaseSchema):
    """Краткое представление узла файловой системы для списков."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор узла файловой системы.",
    )
    owner_id: UUID = Field(
        ...,
        description="Идентификатор владельца узла.",
    )
    parent_id: UUID | None = Field(
        default=None,
        description="Идентификатор родительской папки. None означает корневой уровень.",
    )
    name: str = Field(
        ...,
        description="Имя файла или папки.",
    )
    node_type: NodeType = Field(
        ...,
        description="Тип узла файловой системы.",
    )
    visibility: NodeVisibility = Field(
        ...,
        description="Видимость узла файловой системы.",
    )
    path: str = Field(
        ...,
        description="Материализованный логический путь узла.",
    )
    depth: int = Field(
        ...,
        ge=0,
        description="Глубина вложенности узла.",
    )
    created_at: datetime = Field(
        ...,
        description="Дата и время создания узла.",
    )
    updated_at: datetime = Field(
        ...,
        description="Дата и время последнего обновления узла.",
    )
    is_deleted: bool = Field(
        ...,
        description="Признак логического удаления узла.",
    )


class NodeTreeItem(BaseSchema):
    """Элемент дерева файловой системы."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор узла файловой системы.",
    )
    parent_id: UUID | None = Field(
        default=None,
        description="Идентификатор родительской папки. None означает корневой уровень.",
    )
    name: str = Field(
        ...,
        description="Имя узла файловой системы.",
    )
    node_type: NodeType = Field(
        ...,
        description="Тип узла файловой системы.",
    )
    visibility: NodeVisibility = Field(
        ...,
        description="Видимость узла файловой системы.",
    )
    path: str = Field(
        ...,
        description="Материализованный логический путь узла.",
    )
    depth: int = Field(
        ...,
        ge=0,
        description="Глубина вложенности узла.",
    )
    children: list[NodeTreeItem] = Field(
        default_factory=list,
        description="Дочерние узлы файловой системы.",
    )


class NodeBreadcrumbItem(BaseSchema):
    """Элемент хлебных крошек для отображения пути."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(
        ...,
        description="Уникальный идентификатор узла в цепочке пути.",
    )
    name: str = Field(
        ...,
        description="Имя узла в цепочке пути.",
    )
    node_type: NodeType = Field(
        ...,
        description="Тип узла в цепочке пути.",
    )
    path: str = Field(
        ...,
        description="Логический путь узла.",
    )
    depth: int = Field(
        ...,
        ge=0,
        description="Глубина вложенности узла.",
    )


class NodeQueryParams(PaginationParams):
    """Параметры фильтрации списка узлов файловой системы."""

    parent_id: UUID | None = Field(
        default=None,
        description="Фильтр по родительской папке. None может означать корневой уровень.",
    )
    owner_id: UUID | None = Field(
        default=None,
        description="Фильтр по владельцу узла.",
    )
    node_type: NodeType | None = Field(
        default=None,
        description="Фильтр по типу узла.",
    )
    visibility: NodeVisibility | None = Field(
        default=None,
        description="Фильтр по видимости узла.",
    )
    is_deleted: bool | None = Field(
        default=False,
        description="Фильтр по признаку логического удаления.",
    )
    created_from: datetime | None = Field(
        default=None,
        description="Фильтр по дате создания: начало диапазона включительно.",
    )
    created_to: datetime | None = Field(
        default=None,
        description="Фильтр по дате создания: конец диапазона включительно.",
    )
    updated_from: datetime | None = Field(
        default=None,
        description="Фильтр по дате обновления: начало диапазона включительно.",
    )
    updated_to: datetime | None = Field(
        default=None,
        description="Фильтр по дате обновления: конец диапазона включительно.",
    )
    sort_by: str = Field(
        default="name",
        min_length=1,
        max_length=64,
        description="Поле сортировки.",
        examples=["name", "created_at", "updated_at", "node_type"],
    )
    sort_desc: bool = Field(
        default=False,
        description="Сортировать по убыванию.",
    )

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

    @field_validator("updated_to")
    @classmethod
    def validate_updated_range(
        cls,
        value: datetime | None,
        info: object,
    ) -> datetime | None:
        data = getattr(info, "data", {})
        updated_from = data.get("updated_from")

        if updated_from is not None and value is not None and value < updated_from:
            raise ValueError("updated_to не может быть раньше updated_from.")

        return value


class NodeSearchQuery(PaginationParams):
    """Параметры поиска узлов файловой системы."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Поисковая строка по имени или пути узла.",
        examples=["отчёт", "photo", "pdf"],
    )
    parent_id: UUID | None = Field(
        default=None,
        description="Ограничить поиск указанной папкой.",
    )
    owner_id: UUID | None = Field(
        default=None,
        description="Ограничить поиск указанным владельцем.",
    )
    node_type: NodeType | None = Field(
        default=None,
        description="Фильтр по типу узла.",
    )
    visibility: NodeVisibility | None = Field(
        default=None,
        description="Фильтр по видимости узла.",
    )
    include_deleted: bool = Field(
        default=False,
        description="Включать ли логически удалённые узлы в результаты поиска.",
    )
    sort_by: str = Field(
        default="name",
        min_length=1,
        max_length=64,
        description="Поле сортировки результатов поиска.",
        examples=["name", "created_at", "updated_at"],
    )
    sort_desc: bool = Field(
        default=False,
        description="Сортировать по убыванию.",
    )

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError("query не должен быть пустым.")

        return normalized_value


class NodeOperationResponse(BaseSchema):
    """Результат операции над узлом файловой системы."""

    success: bool = Field(
        ...,
        description="Признак успешного выполнения операции.",
    )
    node: NodeRead | None = Field(
        default=None,
        description="Узел файловой системы после выполнения операции, если применимо.",
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Человекочитаемое сообщение о результате операции.",
    )
