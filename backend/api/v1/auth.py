from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request, Response, status

from api.dependencies import get_auth_service_dependency, get_users_service_dependency
from schemas.auth import (
    AuthSessionRead,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    PasswordChangeRequest,
    RefreshTokenResponse,
)
from schemas.users import CurrentUserRead
from security import (
    CookieError,
    CurrentActiveUserDependency,
    require_refresh_token_from_cookies,
    unauthorized_exception,
)
from services import AuthService, UsersService

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    """Возвращает IP-адрес клиента из запроса."""

    if request.client is None:
        return None
    return request.client.host


def _user_agent(request: Request) -> str | None:
    """Возвращает User-Agent клиента из запроса."""

    user_agent = request.headers.get("user-agent")
    if user_agent is None:
        return None
    normalized = user_agent.strip()
    return normalized or None


def _refresh_token_from_request(request: Request) -> str:
    """Извлекает refresh-токен из cookie запроса."""

    try:
        return require_refresh_token_from_cookies(request)
    except CookieError as exc:
        raise unauthorized_exception("Refresh token отсутствует.") from exc


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
)
async def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service_dependency),
) -> LoginResponse:
    """Выполняет вход пользователя."""

    return await auth_service.login(
        data,
        response=response,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    status_code=status.HTTP_200_OK,
)
async def refresh_session(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service_dependency),
) -> RefreshTokenResponse:
    """Обновляет access/refresh токены по refresh cookie."""

    refresh_token = _refresh_token_from_request(request)
    return await auth_service.refresh_session(
        refresh_token,
        response=response,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
)
async def logout(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service_dependency),
) -> LogoutResponse:
    """Выполняет выход пользователя и очищает auth cookies."""

    refresh_token = None
    try:
        refresh_token = require_refresh_token_from_cookies(request)
    except CookieError:
        refresh_token = None

    return await auth_service.logout(
        refresh_token,
        response=response,
        reason="logout",
    )


@router.get(
    "/me",
    response_model=CurrentUserRead,
    status_code=status.HTTP_200_OK,
)
async def get_me(user: CurrentActiveUserDependency) -> CurrentUserRead:
    """Возвращает данные текущего активного пользователя."""

    return CurrentUserRead.model_validate(user)


@router.get(
    "/sessions",
    response_model=list[AuthSessionRead],
    status_code=status.HTTP_200_OK,
)
async def list_sessions(
    user: CurrentActiveUserDependency,
    include_inactive: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    auth_service: AuthService = Depends(get_auth_service_dependency),
) -> list[AuthSessionRead]:
    """Возвращает список сессий текущего пользователя."""

    return await auth_service.list_sessions(
        user_id=user.id,
        include_inactive=include_inactive,
        limit=limit,
        offset=offset,
    )


@router.delete(
    "/sessions/{session_id}",
    response_model=AuthSessionRead,
    status_code=status.HTTP_200_OK,
)
async def revoke_session(
    user: CurrentActiveUserDependency,
    session_id: UUID = Path(...),
    auth_service: AuthService = Depends(get_auth_service_dependency),
) -> AuthSessionRead:
    """Отзывает конкретную refresh-сессию пользователя."""

    return await auth_service.revoke_session(
        user_id=user.id,
        session_id=session_id,
        reason="session revoked by user",
    )


@router.post(
    "/password/change",
    response_model=CurrentUserRead,
    status_code=status.HTTP_200_OK,
)
async def change_password(
    data: PasswordChangeRequest,
    user: CurrentActiveUserDependency,
    users_service: UsersService = Depends(get_users_service_dependency),
) -> CurrentUserRead:
    """Изменяет пароль текущего активного пользователя."""

    await users_service.change_password(
        user_id=user.id,
        new_password=data.new_password,
        actor_id=user.id,
    )
    return CurrentUserRead.model_validate(user)


# TODO: password reset endpoints не добавлены, так как в AuthService
# отсутствуют реализованные публичные методы request/confirm reset password.

__all__ = ["router"]
