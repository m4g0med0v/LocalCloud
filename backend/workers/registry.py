from __future__ import annotations

from importlib import import_module
from typing import cast

from database.models.enums import BackgroundTaskType
from workers.exceptions import WorkerTaskDispatchError
from workers.types import WorkerTaskHandler


class WorkerTaskRegistry:
    """Реестр соответствия типа фоновой задачи и её обработчика."""

    def __init__(self) -> None:
        self._handlers: dict[BackgroundTaskType, WorkerTaskHandler] = {}

    def register(
        self,
        task_type: BackgroundTaskType,
        handler: WorkerTaskHandler,
        *,
        replace: bool = False,
    ) -> None:
        """Регистрирует обработчик для типа фоновой задачи."""

        if not replace and task_type in self._handlers:
            raise WorkerTaskDispatchError(
                "Обработчик для данного типа задачи уже зарегистрирован.",
                task_type=task_type.value,
                operation="register",
                details={"replace": replace},
            )
        self._handlers[task_type] = handler

    def get_handler(self, task_type: BackgroundTaskType) -> WorkerTaskHandler:
        """Возвращает обработчик задачи по её типу."""

        handler = self._handlers.get(task_type)
        if handler is None:
            raise WorkerTaskDispatchError(
                "Для типа фоновой задачи не найден обработчик.",
                task_type=task_type.value,
                operation="get_handler",
            )
        return handler

    def has_handler(self, task_type: BackgroundTaskType) -> bool:
        """Проверяет наличие обработчика для типа задачи."""

        return task_type in self._handlers

    def supported_task_types(self) -> tuple[BackgroundTaskType, ...]:
        """Возвращает поддерживаемые типы фоновых задач."""

        return tuple(sorted(self._handlers.keys(), key=lambda item: item.value))


def _load_handler(module_name: str, attr_name: str) -> WorkerTaskHandler:
    """Загружает обработчик задачи из указанного модуля."""

    try:
        module = import_module(module_name)
    except Exception as exc:
        raise WorkerTaskDispatchError(
            "Не удалось импортировать модуль обработчика задачи.",
            task_type=None,
            operation="build_default_registry",
            details={"module": module_name, "handler": attr_name},
            cause=exc,
        ) from exc

    try:
        handler = getattr(module, attr_name)
    except AttributeError as exc:
        raise WorkerTaskDispatchError(
            "В модуле не найден указанный обработчик задачи.",
            task_type=None,
            operation="build_default_registry",
            details={"module": module_name, "handler": attr_name},
            cause=exc,
        ) from exc

    if not callable(handler):
        raise WorkerTaskDispatchError(
            "Указанный обработчик задачи не является вызываемым объектом.",
            task_type=None,
            operation="build_default_registry",
            details={
                "module": module_name,
                "handler": attr_name,
                "handler_type": type(handler).__name__,
            },
        )

    return cast(WorkerTaskHandler, handler)


def build_default_registry() -> WorkerTaskRegistry:
    """Создаёт реестр обработчиков фоновых задач по умолчанию."""

    registry = WorkerTaskRegistry()

    create_folder_archive_handler = _load_handler(
        "workers.archives",
        "create_folder_archive_handler",
    )
    clean_trash_handler = _load_handler("workers.cleanup", "clean_trash_handler")
    clean_expired_uploads_handler = _load_handler(
        "workers.cleanup",
        "clean_expired_uploads_handler",
    )
    clean_expired_public_links_handler = _load_handler(
        "workers.public_links",
        "clean_expired_public_links_handler",
    )
    delete_object_from_storage_handler = _load_handler(
        "workers.cleanup",
        "delete_object_from_storage_handler",
    )
    check_storage_integrity_handler = _load_handler(
        "workers.integrity",
        "check_storage_integrity_handler",
    )
    generate_file_preview_handler = _load_handler(
        "workers.previews",
        "generate_file_preview_handler",
    )
    recalculate_user_quota_handler = _load_handler(
        "workers.quotas",
        "recalculate_user_quota_handler",
    )
    unsupported_task_handler = _load_handler(
        "workers.tasks",
        "unsupported_task_handler",
    )

    registry.register(
        BackgroundTaskType.CREATE_FOLDER_ARCHIVE,
        create_folder_archive_handler,
    )
    registry.register(BackgroundTaskType.CLEAN_TRASH, clean_trash_handler)
    registry.register(
        BackgroundTaskType.CLEAN_EXPIRED_UPLOADS,
        clean_expired_uploads_handler,
    )
    registry.register(
        BackgroundTaskType.CLEAN_EXPIRED_PUBLIC_LINKS,
        clean_expired_public_links_handler,
    )
    registry.register(
        BackgroundTaskType.DELETE_OBJECT_FROM_STORAGE,
        delete_object_from_storage_handler,
    )
    registry.register(
        BackgroundTaskType.CHECK_STORAGE_INTEGRITY,
        check_storage_integrity_handler,
    )
    registry.register(
        BackgroundTaskType.GENERATE_FILE_PREVIEW,
        generate_file_preview_handler,
    )
    registry.register(
        BackgroundTaskType.RECALCULATE_USER_QUOTA,
        recalculate_user_quota_handler,
    )
    registry.register(BackgroundTaskType.BACKUP_DATABASE, unsupported_task_handler)
    registry.register(BackgroundTaskType.BACKUP_STORAGE, unsupported_task_handler)

    return registry


__all__ = [
    "WorkerTaskRegistry",
    "build_default_registry",
]
