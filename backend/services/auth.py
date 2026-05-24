from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, TypeVar
from uuid import UUID

from fastapi import Response

from core.config import Settings, get_settings
from core.logging import get_logger
from database import DatabaseError, UnitOfWorkFactory, create_unit_of_work_factory
from database.models.enums import (
    AuditAction,
    AuditResourceType,
    AuditResult,
    UserStatus,
)
from database.models.roles import Role
from database.models.tokens import RefreshToken
from database.models.users import User
from schemas.auth import (
    AuthSessionRead,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RefreshTokenResponse,
    TokenPair,
)
from schemas.roles import RoleListItem
from schemas.users import CurrentUserRead
from security.cookies import clear_auth_cookies, set_auth_cookies
from security.jwt import (
    JwtTokenError,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_token,
)
from security.password import verify_and_update_password_hash
from services.audit import AuditService, get_audit_service
from services.exceptions import (
    AuthenticationServiceError,
    ServiceError,
    service_error_from_database,
    service_error_from_exception,
)

logger = get_logger("services.auth")

SERVICE_NAME = "auth"
T = TypeVar("T")
MAX_SESSION_LIMIT = 1000


class AuthService:
    """Business service for JWT authentication and refresh-token sessions."""

    def __init__(
        self,
        *,
        uow_factory: UnitOfWorkFactory | None = None,
        audit_service: AuditService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.uow_factory = uow_factory or create_unit_of_work_factory()
        self.audit_service = audit_service or get_audit_service(
            uow_factory=self.uow_factory,
        )
        self.settings = settings or get_settings()

    async def login(
        self,
        data: LoginRequest,
        *,
        response: Response | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_name: str | None = None,
    ) -> LoginResponse:
        """Authenticate user, create JWT pair and persist refresh session."""

        login_response, _tokens = await self.login_with_tokens(
            data,
            response=response,
            ip_address=ip_address,
            user_agent=user_agent,
            device_name=device_name,
        )
        return login_response

    async def login_with_tokens(
        self,
        data: LoginRequest,
        *,
        response: Response | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_name: str | None = None,
    ) -> tuple[LoginResponse, TokenPair]:
        """Authenticate user and return response plus internal token pair."""

        operation = "login"
        user_snapshot: dict[str, Any] = {}
        roles: list[Role] = []
        token_pair: TokenPair | None = None
        session_id: UUID | None = None

        try:
            async with self.uow_factory() as uow:
                user = await self._find_user_for_login(
                    uow=uow,
                    email_or_username=data.email_or_username,
                )
                if user is None:
                    await self._safe_log_login_failure(
                        email_or_username=data.email_or_username,
                        reason="user_not_found",
                        ip_address=ip_address,
                        user_agent=user_agent,
                    )
                    raise self._invalid_credentials_error(operation=operation)

                password_valid, new_password_hash = verify_and_update_password_hash(
                    plain_password=data.password,
                    password_hash=user.password_hash,
                )
                if not password_valid:
                    await self._safe_log_login_failure(
                        email_or_username=data.email_or_username,
                        reason="invalid_password",
                        user_id=user.id,
                        ip_address=ip_address,
                        user_agent=user_agent,
                    )
                    raise self._invalid_credentials_error(operation=operation)

                if not user.can_login:
                    await self._safe_log_login_failure(
                        email_or_username=data.email_or_username,
                        reason=f"user_status_{user.status.value}",
                        user_id=user.id,
                        ip_address=ip_address,
                        user_agent=user_agent,
                    )
                    raise AuthenticationServiceError(
                        "Учётная запись не может войти в систему.",
                        user_id=user.id,
                        reason=user.status.value,
                        details={"service": SERVICE_NAME, "operation": operation},
                    )

                if new_password_hash is not None:
                    await uow.users.update_password_hash(
                        user,
                        password_hash=new_password_hash,
                        flush=True,
                        refresh=False,
                    )

                token_pair = self._create_token_pair(user.id)
                refresh_token_model = await uow.refresh_tokens.create_token(
                    user_id=user.id,
                    token_hash=hash_token(
                        token_pair.refresh_token,
                        settings=self.settings,
                    ),
                    expires_at=self._require_datetime(
                        token_pair.refresh_expires_at,
                        operation=operation,
                        field="refresh_expires_at",
                    ),
                    ip_address=ip_address,
                    user_agent=user_agent,
                    device_name=device_name,
                    flush=True,
                    refresh=True,
                    check_user_exists=False,
                    check_duplicate=True,
                )
                session_id = refresh_token_model.id
                await uow.users.update_last_login(
                    user,
                    last_login_at=datetime.now(UTC),
                    flush=True,
                    refresh=True,
                )
                roles = await uow.roles.get_user_roles(
                    user.id,
                    only_active_roles=True,
                    order_by_name=True,
                )
                user_snapshot = _user_snapshot(user)
                await uow.commit()

            issued_tokens = self._require_result(token_pair, operation=operation)

            if response is not None:
                self._set_response_cookies(response, issued_tokens)

            await self._safe_log_auth_event(
                actor_id=user_snapshot["id"],
                action=AuditAction.USER_LOGIN,
                result=AuditResult.SUCCESS,
                entity_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                message="User logged in.",
                metadata={
                    "operation": operation,
                    "user": _audit_user(user_snapshot),
                    "session_id": str(session_id) if session_id else None,
                },
            )
            return (
                LoginResponse(user=_current_user_read(user_snapshot, roles)),
                issued_tokens,
            )

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось выполнить вход в систему.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при входе в систему.",
            ) from exc

    async def refresh_session(
        self,
        refresh_token: str,
        *,
        response: Response | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_name: str | None = None,
    ) -> RefreshTokenResponse:
        """Rotate refresh token and issue a new access/refresh JWT pair."""

        refresh_response, _tokens = await self.refresh_session_with_tokens(
            refresh_token,
            response=response,
            ip_address=ip_address,
            user_agent=user_agent,
            device_name=device_name,
        )
        return refresh_response

    async def refresh_session_with_tokens(
        self,
        refresh_token: str,
        *,
        response: Response | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_name: str | None = None,
    ) -> tuple[RefreshTokenResponse, TokenPair]:
        operation = "refresh_session"
        token_pair: TokenPair | None = None
        user_snapshot: dict[str, Any] = {}
        roles: list[Role] = []
        new_session_id: UUID | None = None
        old_session_id: UUID | None = None

        try:
            payload = decode_refresh_token(refresh_token, settings=self.settings)
            old_token_hash = hash_token(refresh_token, settings=self.settings)

            async with self.uow_factory() as uow:
                existing_token = await uow.refresh_tokens.get_by_hash(old_token_hash)
                if existing_token is None:
                    raise AuthenticationServiceError(
                        "Refresh token не найден или уже недействителен.",
                        reason="refresh_token_not_found",
                        details={"service": SERVICE_NAME, "operation": operation},
                    )

                old_session_id = existing_token.id
                if not existing_token.can_be_used_at(datetime.now(UTC)):
                    await uow.refresh_tokens.revoke_all_user_tokens(
                        existing_token.user_id,
                        reason="refresh token reuse detected",
                        flush=True,
                    )
                    await uow.commit()
                    await self._safe_log_auth_event(
                        actor_id=existing_token.user_id,
                        action=AuditAction.USER_SESSION_REVOKED,
                        result=AuditResult.WARNING,
                        entity_id=existing_token.id,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        message="Refresh token reuse was detected.",
                        metadata={"operation": operation},
                    )
                    raise AuthenticationServiceError(
                        "Refresh token уже не может быть использован.",
                        user_id=existing_token.user_id,
                        session_id=existing_token.id,
                        reason="refresh_token_reuse_detected",
                        details={"service": SERVICE_NAME, "operation": operation},
                    )

                if payload.user_id != existing_token.user_id:
                    await uow.refresh_tokens.revoke_all_user_tokens(
                        existing_token.user_id,
                        reason="refresh token subject mismatch",
                        flush=True,
                    )
                    await uow.commit()
                    raise AuthenticationServiceError(
                        "Refresh token содержит некорректного пользователя.",
                        user_id=existing_token.user_id,
                        session_id=existing_token.id,
                        reason="subject_mismatch",
                        details={"service": SERVICE_NAME, "operation": operation},
                    )

                user = await uow.users.get_required_user_by_id(existing_token.user_id)
                if not user.can_login:
                    await uow.refresh_tokens.revoke_all_user_tokens(
                        user.id,
                        reason=f"user status is {user.status.value}",
                        flush=True,
                    )
                    await uow.commit()
                    raise AuthenticationServiceError(
                        "Учётная запись больше не может обновлять сессию.",
                        user_id=user.id,
                        reason=user.status.value,
                        details={"service": SERVICE_NAME, "operation": operation},
                    )

                token_pair = self._create_token_pair(user.id)
                new_token = await uow.refresh_tokens.rotate_token(
                    old_token=existing_token,
                    new_token_hash=hash_token(
                        token_pair.refresh_token,
                        settings=self.settings,
                    ),
                    new_expires_at=self._require_datetime(
                        token_pair.refresh_expires_at,
                        operation=operation,
                        field="refresh_expires_at",
                    ),
                    ip_address=ip_address,
                    user_agent=user_agent,
                    device_name=device_name,
                    revoke_reason="refresh token rotated",
                    flush=True,
                    refresh=True,
                    check_duplicate=True,
                )
                new_session_id = new_token.id
                roles = await uow.roles.get_user_roles(
                    user.id,
                    only_active_roles=True,
                    order_by_name=True,
                )
                user_snapshot = _user_snapshot(user)
                await uow.commit()

            issued_tokens = self._require_result(token_pair, operation=operation)

            if response is not None:
                self._set_response_cookies(response, issued_tokens)

            await self._safe_log_auth_event(
                actor_id=user_snapshot["id"],
                action=AuditAction.USER_REFRESH_TOKEN_ROTATED,
                result=AuditResult.SUCCESS,
                entity_id=new_session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                message="Refresh token was rotated.",
                metadata={
                    "operation": operation,
                    "old_session_id": str(old_session_id) if old_session_id else None,
                    "new_session_id": str(new_session_id) if new_session_id else None,
                },
            )
            return (
                RefreshTokenResponse(user=_current_user_read(user_snapshot, roles)),
                issued_tokens,
            )

        except JwtTokenError as exc:
            raise AuthenticationServiceError(
                "Refresh token недействителен.",
                reason=getattr(getattr(exc, "code", None), "value", None)
                or exc.__class__.__name__,
                details={"service": SERVICE_NAME, "operation": operation},
                cause=exc,
            ) from exc
        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось обновить сессию.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при обновлении сессии.",
            ) from exc

    async def logout(
        self,
        refresh_token: str | None = None,
        *,
        response: Response | None = None,
        reason: str = "logout",
    ) -> LogoutResponse:
        """Revoke current refresh session if token is available and clear cookies."""

        operation = "logout"
        user_id: UUID | None = None
        session_id: UUID | None = None

        try:
            if refresh_token:
                token_hash = hash_token(refresh_token, settings=self.settings)
                async with self.uow_factory() as uow:
                    token = await uow.refresh_tokens.get_by_hash(token_hash)
                    if token is not None:
                        user_id = token.user_id
                        session_id = token.id
                        await uow.refresh_tokens.revoke_token(
                            token,
                            reason=reason,
                            flush=True,
                            refresh=False,
                        )
                        await uow.commit()

            if response is not None:
                clear_auth_cookies(response, settings=self.settings)

            await self._safe_log_auth_event(
                actor_id=user_id,
                action=AuditAction.USER_LOGOUT,
                result=AuditResult.SUCCESS,
                entity_id=session_id,
                message="User logged out.",
                metadata={"operation": operation},
            )
            return LogoutResponse()

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось выполнить выход из системы.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при выходе из системы.",
            ) from exc

    async def logout_all(
        self,
        user_id: UUID,
        *,
        response: Response | None = None,
        reason: str = "logout all sessions",
    ) -> LogoutResponse:
        operation = "logout_all"
        revoked_count = 0

        try:
            async with self.uow_factory() as uow:
                await uow.users.get_required_user_by_id(user_id)
                revoked_count = await uow.refresh_tokens.revoke_all_user_tokens(
                    user_id,
                    reason=reason,
                    flush=True,
                )
                await uow.commit()

            if response is not None:
                clear_auth_cookies(response, settings=self.settings)

            await self._safe_log_auth_event(
                actor_id=user_id,
                action=AuditAction.USER_SESSION_REVOKED,
                result=AuditResult.SUCCESS,
                entity_id=None,
                message="All user sessions were revoked.",
                metadata={"operation": operation, "revoked_count": revoked_count},
            )
            return LogoutResponse(message="Все сессии завершены.")

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось завершить все сессии пользователя.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при завершении всех сессий.",
            ) from exc

    async def get_current_user_from_access_token(
        self,
        access_token: str,
    ) -> CurrentUserRead:
        operation = "get_current_user_from_access_token"
        current_user: CurrentUserRead | None = None

        try:
            payload = decode_access_token(access_token, settings=self.settings)
            async with self.uow_factory() as uow:
                user = await uow.users.get_required_user_by_id(payload.user_id)
                if not user.can_login:
                    raise AuthenticationServiceError(
                        "Учётная запись неактивна.",
                        user_id=user.id,
                        reason=user.status.value,
                        details={"service": SERVICE_NAME, "operation": operation},
                    )
                roles = await uow.roles.get_user_roles(
                    user.id,
                    only_active_roles=True,
                    order_by_name=True,
                )
                current_user = _current_user_read(_user_snapshot(user), roles)

        except JwtTokenError as exc:
            raise AuthenticationServiceError(
                "Access token недействителен.",
                reason=getattr(getattr(exc, "code", None), "value", None)
                or exc.__class__.__name__,
                details={"service": SERVICE_NAME, "operation": operation},
                cause=exc,
            ) from exc
        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось получить пользователя по access token.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при проверке access token.",
            ) from exc

        return self._require_result(current_user, operation=operation)

    async def list_sessions(
        self,
        user_id: UUID,
        *,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuthSessionRead]:
        operation = "list_sessions"
        sessions: list[AuthSessionRead] | None = None
        self._validate_session_pagination(
            limit=limit, offset=offset, operation=operation
        )

        try:
            async with self.uow_factory() as uow:
                await uow.users.get_required_user_by_id(user_id)
                tokens = await uow.refresh_tokens.list_user_tokens(
                    user_id,
                    offset=offset,
                    limit=limit,
                    include_inactive=include_inactive,
                    include_revoked=include_inactive,
                    include_expired=include_inactive,
                    order_by_created_desc=True,
                )
                sessions = [_auth_session_read(token) for token in tokens]

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось получить список сессий.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при получении списка сессий.",
            ) from exc

        return self._require_result(sessions, operation=operation)

    async def revoke_session(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        reason: str = "session revoked",
    ) -> AuthSessionRead:
        operation = "revoke_session"
        result: AuthSessionRead | None = None

        try:
            async with self.uow_factory() as uow:
                token = await uow.refresh_tokens.get_required_token_by_id(session_id)
                if token.user_id != user_id:
                    raise AuthenticationServiceError(
                        "Сессия не принадлежит указанному пользователю.",
                        user_id=user_id,
                        session_id=session_id,
                        reason="session_owner_mismatch",
                        details={"service": SERVICE_NAME, "operation": operation},
                    )
                revoked_token = await uow.refresh_tokens.revoke_token(
                    token,
                    reason=reason,
                    flush=True,
                    refresh=True,
                )
                result = _auth_session_read(revoked_token)
                await uow.commit()

            await self._safe_log_auth_event(
                actor_id=user_id,
                action=AuditAction.USER_SESSION_REVOKED,
                result=AuditResult.SUCCESS,
                entity_id=session_id,
                message="User session was revoked.",
                metadata={"operation": operation},
            )
            return self._require_result(result, operation=operation)

        except DatabaseError as exc:
            raise self._database_error(
                exc,
                operation=operation,
                message="Не удалось отозвать сессию.",
            ) from exc
        except ServiceError:
            raise
        except Exception as exc:
            raise self._unexpected_error(
                exc,
                operation=operation,
                message="Непредвиденная ошибка при отзыве сессии.",
            ) from exc

    def _create_token_pair(self, user_id: UUID) -> TokenPair:
        access_token = create_access_token(user_id, settings=self.settings)
        refresh_token = create_refresh_token(user_id, settings=self.settings)
        access_payload = decode_access_token(access_token, settings=self.settings)
        refresh_payload = decode_refresh_token(refresh_token, settings=self.settings)
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_at=access_payload.expires_at,
            refresh_expires_at=refresh_payload.expires_at,
        )

    async def _find_user_for_login(
        self,
        *,
        uow: Any,
        email_or_username: str,
    ) -> User | None:
        if "@" in email_or_username:
            user = await uow.users.get_by_email(
                email_or_username,
                include_deleted=False,
            )
            if user is not None:
                return user
        return await uow.users.get_by_username(
            email_or_username,
            include_deleted=False,
        )

    def _set_response_cookies(self, response: Response, token_pair: TokenPair) -> None:
        set_auth_cookies(
            response,
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            settings=self.settings,
        )

    @staticmethod
    def _require_datetime(
        value: datetime | None,
        *,
        operation: str,
        field: str,
    ) -> datetime:
        if value is None:
            raise ServiceError(
                "JWT-сервис не вернул дату истечения токена.",
                service=SERVICE_NAME,
                operation=operation,
                details={"field": field},
            )
        return value

    @staticmethod
    def _validate_session_pagination(
        *,
        limit: int,
        offset: int,
        operation: str,
    ) -> None:
        if limit < 1 or limit > MAX_SESSION_LIMIT:
            raise AuthenticationServiceError(
                "Некорректный размер страницы списка сессий.",
                reason="invalid_limit",
                details={
                    "service": SERVICE_NAME,
                    "operation": operation,
                    "limit": limit,
                },
            )
        if offset < 0:
            raise AuthenticationServiceError(
                "Смещение списка сессий не может быть отрицательным.",
                reason="invalid_offset",
                details={
                    "service": SERVICE_NAME,
                    "operation": operation,
                    "offset": offset,
                },
            )

    @staticmethod
    def _invalid_credentials_error(*, operation: str) -> AuthenticationServiceError:
        return AuthenticationServiceError(
            "Неверный логин или пароль.",
            reason="invalid_credentials",
            details={"service": SERVICE_NAME, "operation": operation},
        )

    @staticmethod
    def _require_result(result: T | None, *, operation: str) -> T:
        if result is None:
            raise ServiceError(
                "Сервис аутентификации не вернул результат операции.",
                service=SERVICE_NAME,
                operation=operation,
            )
        return result

    @staticmethod
    def _database_error(
        exc: DatabaseError, *, operation: str, message: str
    ) -> ServiceError:
        return service_error_from_database(
            exc,
            operation=operation,
            message=message,
            service=SERVICE_NAME,
        )

    @staticmethod
    def _unexpected_error(
        exc: Exception, *, operation: str, message: str
    ) -> ServiceError:
        logger.exception(
            message,
            extra={"operation": operation, "error_type": exc.__class__.__name__},
        )
        return service_error_from_exception(
            exc,
            operation=operation,
            message=message,
            service=SERVICE_NAME,
        )

    async def _safe_log_login_failure(
        self,
        *,
        email_or_username: str,
        reason: str,
        user_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        await self._safe_log_auth_event(
            actor_id=user_id,
            action=AuditAction.USER_LOGIN_FAILED,
            result=AuditResult.FAILURE,
            entity_id=None,
            ip_address=ip_address,
            user_agent=user_agent,
            message="User login failed.",
            error_code=reason,
            metadata={
                "operation": "login",
                "email_or_username": email_or_username,
                "reason": reason,
            },
        )

    async def _safe_log_auth_event(
        self,
        *,
        actor_id: UUID | None,
        action: AuditAction,
        result: AuditResult,
        entity_id: UUID | None,
        message: str,
        metadata: Mapping[str, Any] | None = None,
        error_code: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        try:
            if actor_id is None:
                await self.audit_service.log_system_event(
                    action=action,
                    result=result,
                    entity_type=AuditResourceType.SESSION.value,
                    entity_id=entity_id,
                    resource_type=AuditResourceType.SESSION,
                    message=message,
                    error_code=error_code,
                    metadata=metadata,
                )
                return

            await self.audit_service.log_user_event(
                user_id=actor_id,
                action=action,
                result=result,
                entity_type=AuditResourceType.SESSION.value,
                entity_id=entity_id,
                resource_type=AuditResourceType.SESSION,
                ip_address=ip_address,
                user_agent=user_agent,
                message=message,
                error_code=error_code,
                metadata=metadata,
            )
        except Exception as exc:
            logger.warning(
                "Failed to write audit event for auth service.",
                extra={
                    "action": action.value,
                    "entity_id": str(entity_id) if entity_id else None,
                    "actor_id": str(actor_id) if actor_id else None,
                    "error_type": exc.__class__.__name__,
                    "reason": str(exc),
                },
            )


def _user_snapshot(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "status": user.status,
        "is_email_verified": user.is_email_verified,
        "last_login_at": user.last_login_at,
    }


def _role_snapshot(role: Role) -> dict[str, Any]:
    return {
        "id": role.id,
        "name": role.name,
        "code": role.code,
        "display_name": role.display_name,
        "is_system": role.is_system,
        "is_active": role.is_active,
    }


def _role_list_item(role: Role) -> RoleListItem:
    return RoleListItem.model_validate(_role_snapshot(role))


def _current_user_read(
    snapshot: Mapping[str, Any],
    roles: list[Role],
) -> CurrentUserRead:
    payload = dict(snapshot)
    payload["roles"] = [_role_list_item(role) for role in roles]
    return CurrentUserRead.model_validate(payload)


def _auth_session_read(token: RefreshToken) -> AuthSessionRead:
    return AuthSessionRead.model_validate(_refresh_token_snapshot(token))


def _refresh_token_snapshot(token: RefreshToken) -> dict[str, Any]:
    return {
        "id": token.id,
        "user_id": token.user_id,
        "status": _enum_or_value(token.status),
        "expires_at": token.expires_at,
        "revoked_at": token.revoked_at,
        "revoke_reason": token.revoke_reason,
        "replaced_by_token_id": token.replaced_by_token_id,
        "parent_token_id": token.parent_token_id,
        "ip_address": str(token.ip_address) if token.ip_address else None,
        "user_agent": token.user_agent,
        "device_name": token.device_name,
        "is_active": token.can_be_used_at(datetime.now(UTC)),
        "created_at": token.created_at,
    }


def _audit_user(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": str(snapshot["id"]),
        "email": str(snapshot["email"]),
        "username": snapshot["username"],
        "status": snapshot["status"].value
        if isinstance(snapshot["status"], UserStatus)
        else str(snapshot["status"]),
    }


def _enum_or_value(value: Any) -> Any:
    return getattr(value, "value", value)


def get_auth_service(
    *,
    uow_factory: UnitOfWorkFactory | None = None,
    audit_service: AuditService | None = None,
    settings: Settings | None = None,
) -> AuthService:
    return AuthService(
        uow_factory=uow_factory,
        audit_service=audit_service,
        settings=settings,
    )


__all__ = [
    "AuthService",
    "get_auth_service",
]
