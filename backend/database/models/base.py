"""Базовые компоненты ORM-моделей SQLAlchemy.

Модуль содержит общую metadata SQLAlchemy с правилами именования индексов
и ограничений, функцию преобразования имён классов из CamelCase в snake_case,
а также базовый декларативный класс `Base` для всех ORM-моделей проекта.

`Base` автоматически формирует имя таблицы из имени ORM-класса и предоставляет
вспомогательные методы для отладочного представления модели.

Attributes:
    NAMING_CONVENTION: Правила именования индексов и ограничений SQLAlchemy.
"""

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
    """Преобразует строку из CamelCase в snake_case.

    Выполняет два прохода регулярными выражениями, чтобы корректно разделить
    границы между словами, цифрами и заглавными буквами, после чего приводит
    результат к нижнему регистру.

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

    Attributes:
        metadata: Общая metadata SQLAlchemy с правилами именования индексов,
            ограничений и внешних ключей.
    """

    metadata: ClassVar[MetaData] = MetaData(naming_convention=NAMING_CONVENTION)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Формирует имя таблицы на основе имени ORM-класса.

        Преобразует имя класса из CamelCase в snake_case и использует результат
        как имя таблицы по умолчанию. Модели могут переопределить это поведение,
        явно задав `__tablename__`.

        Returns:
            Имя таблицы в формате snake_case.

        Examples:
            User -> user
            PublicLink -> public_link
            FileUploadPart -> file_upload_part
        """

        return camel_to_snake(cls.__name__)

    def to_dict(self) -> dict[str, Any]:
        """Преобразует экземпляр ORM-модели в словарь.

        Метод предназначен для внутренней отладки, логирования и тестов.
        Для HTTP-ответов следует использовать Pydantic-схемы, а не возвращать
        ORM-объекты напрямую.

        Returns:
            Словарь вида `{column_name: column_value}`, содержащий значения
            всех колонок текущей ORM-модели.
        """

        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }

    def __repr__(self) -> str:
        """Возвращает компактное отладочное представление ORM-объекта.

        Если у объекта есть атрибут `id`, включает его в строковое
        представление. В противном случае возвращает только имя класса модели.

        Returns:
            Строковое представление ORM-объекта.
        """

        model_name = self.__class__.__name__
        model_id = getattr(self, "id", None)

        if model_id is not None:
            return f"<{model_name}(id={model_id})>"

        return f"<{model_name}>"
