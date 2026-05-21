from __future__ import annotations

import re
from typing import Any, ClassVar

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, declared_attr

# Правила именования индексов и ограничений SQLAlchemy.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def camel_to_snake(value: str) -> str:
    """Преобразовать строку из CamelCase в snake_case.

    Args:
        value: Строка в формате CamelCase.

    Returns:
        Строка в формате snake_case.

    Examples:
        >>> camel_to_snake("UserModel")
        'user_model'
        >>> camel_to_snake("PublicLink")
        'public_link'
        >>> camel_to_snake("FileUploadPart")
        'file_upload_part'
    """
    first_pass = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", first_pass).lower()


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей.

    Предоставляет общую metadata SQLAlchemy, задаёт naming convention для
    индексов и ограничений, помогает Alembic корректно автогенерировать
    миграции и автоматически формирует имя таблицы из имени ORM-класса.

    Все ORM-модели проекта должны наследоваться от этого класса.
    """

    metadata: ClassVar[MetaData] = MetaData(naming_convention=NAMING_CONVENTION)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Сформировать имя таблицы на основе имени ORM-класса.

        Returns:
            Имя таблицы в формате snake_case.

        Examples:
            User -> user
            PublicLink -> public_link
            FileUploadPart -> file_upload_part
        """
        return camel_to_snake(cls.__name__)

    def to_dict(self) -> dict[str, Any]:
        """Преобразовать экземпляр ORM-модели в словарь.

        Метод предназначен для внутренней отладки, логирования и тестов.
        Для HTTP-ответов следует использовать Pydantic-схемы, а не возвращать
        ORM-объекты напрямую.

        Returns:
            Словарь вида `{column_name: column_value}`.
        """
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }

    def __repr__(self) -> str:
        """Вернуть компактное отладочное представление ORM-объекта."""
        model_name = self.__class__.__name__
        model_id = getattr(self, "id", None)

        if model_id is not None:
            return f"<{model_name}(id={model_id})>"

        return f"<{model_name}>"
