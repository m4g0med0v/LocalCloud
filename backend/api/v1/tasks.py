from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status

from api.dependencies import get_tasks_service_dependency
from database.models.enums import BackgroundTaskType
from schemas.common import PageResponse
from schemas.tasks import (
    BackgroundTaskCancelRequest,
    BackgroundTaskCreate,
    BackgroundTaskListItem,
    BackgroundTaskQueryParams,
    BackgroundTaskRead,
    BackgroundTaskRetryRequest,
    TaskResultRead,
)
from security import CurrentActiveUserDependency
from security.permissions import is_admin_user
from services import TasksService

router = APIRouter(prefix="/tasks", tags=["tasks"])

USER_CREATABLE_TASK_TYPES: frozenset[BackgroundTaskType] = frozenset(
    {
        BackgroundTaskType.CREATE_FOLDER_ARCHIVE,
    }
)


@router.post(
    "/",
    response_model=BackgroundTaskRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    data: BackgroundTaskCreate,
    current_user: CurrentActiveUserDependency,
    tasks_service: TasksService = Depends(get_tasks_service_dependency),
) -> BackgroundTaskRead:
    """Создаёт фоновую задачу."""

    user_is_admin = bool(is_admin_user(cast(Any, current_user)))
    if (not user_is_admin) and data.task_type not in USER_CREATABLE_TASK_TYPES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для создания этого типа задачи.",
        )

    if data.created_by not in (None, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нельзя создать задачу от имени другого пользователя.",
        )

    request_data = data.model_copy(update={"created_by": current_user.id})
    return await tasks_service.create_task(request_data, actor_id=current_user.id)


@router.get(
    "/",
    response_model=PageResponse[BackgroundTaskListItem],
    status_code=status.HTTP_200_OK,
)
async def list_tasks(
    current_user: CurrentActiveUserDependency,
    params: BackgroundTaskQueryParams = Depends(),
    tasks_service: TasksService = Depends(get_tasks_service_dependency),
) -> PageResponse[BackgroundTaskListItem]:
    """Возвращает список фоновых задач."""

    return await tasks_service.list_tasks(params, actor_id=current_user.id)


@router.get(
    "/{task_id}",
    response_model=BackgroundTaskRead,
    status_code=status.HTTP_200_OK,
)
async def get_task(
    current_user: CurrentActiveUserDependency,
    task_id: UUID = Path(...),
    tasks_service: TasksService = Depends(get_tasks_service_dependency),
) -> BackgroundTaskRead:
    """Возвращает фоновую задачу по идентификатору."""

    return await tasks_service.get_task(task_id, actor_id=current_user.id)


@router.get(
    "/{task_id}/result",
    response_model=TaskResultRead,
    status_code=status.HTTP_200_OK,
)
async def get_task_result(
    current_user: CurrentActiveUserDependency,
    task_id: UUID = Path(...),
    tasks_service: TasksService = Depends(get_tasks_service_dependency),
) -> TaskResultRead:
    """Возвращает результат выполнения задачи."""

    return await tasks_service.get_task_result(task_id, actor_id=current_user.id)


@router.get(
    "/{task_id}/progress",
    response_model=TaskResultRead,
    status_code=status.HTTP_200_OK,
)
async def get_task_progress(
    current_user: CurrentActiveUserDependency,
    task_id: UUID = Path(...),
    tasks_service: TasksService = Depends(get_tasks_service_dependency),
) -> TaskResultRead:
    """Возвращает текущий прогресс задачи."""

    return await tasks_service.get_task_result(task_id, actor_id=current_user.id)


@router.post(
    "/{task_id}/cancel",
    response_model=BackgroundTaskRead,
    status_code=status.HTTP_200_OK,
)
async def cancel_task(
    data: BackgroundTaskCancelRequest,
    current_user: CurrentActiveUserDependency,
    task_id: UUID = Path(...),
    tasks_service: TasksService = Depends(get_tasks_service_dependency),
) -> BackgroundTaskRead:
    """Отменяет фоновую задачу."""

    return await tasks_service.cancel_task(task_id, data, actor_id=current_user.id)


@router.post(
    "/{task_id}/retry",
    response_model=BackgroundTaskRead,
    status_code=status.HTTP_200_OK,
)
async def retry_task(
    data: BackgroundTaskRetryRequest,
    current_user: CurrentActiveUserDependency,
    task_id: UUID = Path(...),
    tasks_service: TasksService = Depends(get_tasks_service_dependency),
) -> BackgroundTaskRead:
    """Повторно ставит задачу в очередь."""

    return await tasks_service.retry_task(task_id, data, actor_id=current_user.id)


__all__ = ["router"]
