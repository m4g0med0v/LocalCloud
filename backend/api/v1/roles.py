"""Эндпоинты для управления ролями пользователей.

Модуль содержит маршрутизатор FastAPI для просмотра, создания, обновления
и деактивации ролей, а также для назначения и снятия ролей с пользователей.
Дополнительно предоставляет эндпоинт для получения списка назначений ролей
конкретного пользователя.

Все маршруты модуля предназначены для административного доступа и требуют
текущего пользователя с правами администратора.

Attributes:
    router: Маршрутизатор FastAPI с префиксом `/roles` и тегом `roles`.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status

from api.dependencies import get_roles_service_dependency
from schemas.common import MessageResponse, PageResponse
from schemas.roles import (
    RoleAssignRequest,
    RoleCreate,
    RoleListItem,
    RoleRead,
    RoleRemoveRequest,
    RoleUpdate,
    UserRoleRead,
)
from security import CurrentAdminUserDependency
from services import RolesService

# Маршрутизатор эндпоинтов для управления ролями пользователей.
router = APIRouter(prefix="/roles", tags=["roles"])


@router.get(
    "/",
    response_model=PageResponse[RoleListItem],
    status_code=status.HTTP_200_OK,
)
async def list_roles(
    _: CurrentAdminUserDependency,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    only_active: bool | None = Query(default=None),
    only_system: bool | None = Query(default=None),
    search: str | None = Query(default=None),
    roles_service: RolesService = Depends(get_roles_service_dependency),
) -> PageResponse[RoleListItem]:
    """Возвращает список ролей.

    Получает страницу ролей с учётом фильтров активности, системности,
    поисковой строки и параметров пагинации. Результат сортируется по имени
    роли. Эндпоинт доступен только текущему администратору.

    Args:
        _: Текущий авторизованный администратор. Используется как зависимость
            безопасности и не применяется внутри функции напрямую.
        offset: Смещение от начала списка ролей.
        limit: Максимальное количество ролей в ответе.
        only_active: Фильтр по активным ролям. Если `None`, фильтр
            не применяется.
        only_system: Фильтр по системным ролям. Если `None`, фильтр
            не применяется.
        search: Поисковая строка для фильтрации ролей.
        roles_service: Сервис ролей, выполняющий получение списка.

    Returns:
        Страница ролей с метаданными пагинации.

    Raises:
        HTTPException: Если пользователь не аутентифицирован, не является
            администратором, параметры пагинации некорректны или доступ
            запрещён.
    """

    return await roles_service.list_roles(
        offset=offset,
        limit=limit,
        only_active=only_active,
        only_system=only_system,
        search=search,
        order_by_name=True,
    )


@router.post(
    "/",
    response_model=RoleRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_role(
    data: RoleCreate,
    admin_user: CurrentAdminUserDependency,
    roles_service: RolesService = Depends(get_roles_service_dependency),
) -> RoleRead:
    """Создаёт новую роль.

    Создаёт пользовательскую или системную роль с переданными параметрами.
    Операция выполняется от имени текущего администратора.

    Args:
        data: Данные для создания роли.
        admin_user: Текущий авторизованный администратор, создающий роль.
        roles_service: Сервис ролей, выполняющий создание роли.

    Returns:
        Данные созданной роли.

    Raises:
        HTTPException: Если администратор не аутентифицирован, доступ запрещён,
            роль с такими параметрами уже существует или данные создания
            некорректны.
    """

    return await roles_service.create_role(data, actor_id=admin_user.id)


@router.get(
    "/{role_id}",
    response_model=RoleRead,
    status_code=status.HTTP_200_OK,
)
async def get_role(
    _: CurrentAdminUserDependency,
    role_id: UUID = Path(...),
    roles_service: RolesService = Depends(get_roles_service_dependency),
) -> RoleRead:
    """Возвращает роль по идентификатору.

    Получает подробные данные роли по её уникальному идентификатору. Эндпоинт
    доступен только текущему администратору.

    Args:
        _: Текущий авторизованный администратор. Используется как зависимость
            безопасности и не применяется внутри функции напрямую.
        role_id: Уникальный идентификатор роли.
        roles_service: Сервис ролей, выполняющий получение роли.

    Returns:
        Подробные данные роли.

    Raises:
        HTTPException: Если администратор не аутентифицирован, роль не найдена
            или доступ запрещён.
    """

    return await roles_service.get_role(role_id)


@router.patch(
    "/{role_id}",
    response_model=RoleRead,
    status_code=status.HTTP_200_OK,
)
async def update_role(
    data: RoleUpdate,
    admin_user: CurrentAdminUserDependency,
    role_id: UUID = Path(...),
    roles_service: RolesService = Depends(get_roles_service_dependency),
) -> RoleRead:
    """Обновляет роль.

    Изменяет параметры существующей роли от имени текущего администратора.

    Args:
        data: Новые параметры роли.
        admin_user: Текущий авторизованный администратор, обновляющий роль.
        role_id: Уникальный идентификатор обновляемой роли.
        roles_service: Сервис ролей, выполняющий обновление роли.

    Returns:
        Данные роли после обновления.

    Raises:
        HTTPException: Если администратор не аутентифицирован, роль не найдена,
            доступ запрещён, роль нельзя изменить или параметры обновления
            некорректны.
    """

    return await roles_service.update_role(
        role_id,
        data,
        actor_id=admin_user.id,
    )


@router.delete(
    "/{role_id}",
    response_model=RoleRead,
    status_code=status.HTTP_200_OK,
)
async def delete_role(
    admin_user: CurrentAdminUserDependency,
    role_id: UUID = Path(...),
    roles_service: RolesService = Depends(get_roles_service_dependency),
) -> RoleRead:
    """Деактивирует роль.

    Выполняет логическое удаление роли через деактивацию. Операция выполняется
    от имени текущего администратора.

    Args:
        admin_user: Текущий авторизованный администратор, деактивирующий роль.
        role_id: Уникальный идентификатор деактивируемой роли.
        roles_service: Сервис ролей, выполняющий деактивацию роли.

    Returns:
        Данные деактивированной роли.

    Raises:
        HTTPException: Если администратор не аутентифицирован, роль не найдена,
            доступ запрещён, роль уже неактивна или её нельзя деактивировать.
    """

    return await roles_service.deactivate_role(
        role_id,
        actor_id=admin_user.id,
    )


@router.post(
    "/assign",
    response_model=UserRoleRead,
    status_code=status.HTTP_200_OK,
)
async def assign_role(
    data: RoleAssignRequest,
    admin_user: CurrentAdminUserDependency,
    roles_service: RolesService = Depends(get_roles_service_dependency),
) -> UserRoleRead:
    """Назначает роль пользователю.

    Создаёт назначение роли для указанного пользователя. Операция выполняется
    от имени текущего администратора.

    Args:
        data: Данные для назначения роли пользователю.
        admin_user: Текущий авторизованный администратор, назначающий роль.
        roles_service: Сервис ролей, выполняющий назначение роли.

    Returns:
        Данные созданного назначения роли пользователю.

    Raises:
        HTTPException: Если администратор не аутентифицирован, пользователь
            или роль не найдены, роль неактивна, назначение уже существует
            или доступ запрещён.
    """

    return await roles_service.assign_role(data, actor_id=admin_user.id)


@router.post(
    "/remove",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def remove_role(
    data: RoleRemoveRequest,
    admin_user: CurrentAdminUserDependency,
    roles_service: RolesService = Depends(get_roles_service_dependency),
) -> MessageResponse:
    """Снимает роль с пользователя.

    Удаляет или деактивирует назначение роли для указанного пользователя.
    Возвращает сообщение о результате операции: роль снята либо назначение
    не найдено.

    Args:
        data: Данные для снятия роли с пользователя.
        admin_user: Текущий авторизованный администратор, снимающий роль.
        roles_service: Сервис ролей, выполняющий снятие роли.

    Returns:
        Сообщение с результатом снятия роли.

    Raises:
        HTTPException: Если администратор не аутентифицирован, пользователь
            или роль не найдены, доступ запрещён или снятие роли невозможно.
    """

    removed = await roles_service.remove_role(data, actor_id=admin_user.id)
    if removed:
        message = "Роль снята с пользователя."
    else:
        message = "Назначение роли не найдено."
    return MessageResponse(message=message)


@router.get(
    "/users/{user_id}",
    response_model=list[UserRoleRead],
    status_code=status.HTTP_200_OK,
)
async def get_user_roles(
    _: CurrentAdminUserDependency,
    user_id: UUID = Path(...),
    roles_service: RolesService = Depends(get_roles_service_dependency),
) -> list[UserRoleRead]:
    """Возвращает назначения ролей пользователя.

    Получает список ролей, назначенных указанному пользователю. Эндпоинт
    доступен только текущему администратору.

    Args:
        _: Текущий авторизованный администратор. Используется как зависимость
            безопасности и не применяется внутри функции напрямую.
        user_id: Уникальный идентификатор пользователя.
        roles_service: Сервис ролей, выполняющий получение назначений ролей.

    Returns:
        Список назначений ролей указанного пользователя.

    Raises:
        HTTPException: Если администратор не аутентифицирован, пользователь
            не найден или доступ запрещён.
    """

    return await roles_service.get_user_role_assignments(user_id)


__all__ = ["router"]
