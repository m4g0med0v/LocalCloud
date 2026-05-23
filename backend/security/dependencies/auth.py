from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Settings, get_settings
from database.client import get_db_session
from security.cookies import (
    CookieError,
    get_access_token_from_cookies,
    get_refresh_token_from_cookies,
    require_access_token_from_cookies,
    require_refresh_token_from_cookies,
)
from security.jwt import (
    JwtExpiredError,
    JwtInvalidClaimsError,
    JwtInvalidTokenTypeError,
    JwtPayload,
    JwtTokenError,
    decode_access_token,
    decode_refresh_token,
)


AUTHENTICATION_ERROR_HEADERS: dict[str, str] = {"WWW-Authenticate": "Bearer"}
SettingsDependency = Annotated[Settings, Depends(get_settings)]
DatabaseSessionDependency = Annotated[AsyncSession, Depends(get_db_session)]


class SecurityDependencyError(HTTPException):
    """HTTP-ошибка security dependency."""


def unauthorized_exception(
    detail: str = "Не удалось подтвердить учётные данные.",
) -> SecurityDependencyError:
    return SecurityDependencyError(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers=AUTHENTICATION_ERROR_HEADERS,
    )


def forbidden_exception(
    detail: str = "Недостаточно прав для выполнения операции.",
) -> SecurityDependencyError:
    return SecurityDependencyError(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


async def get_current_access_payload(
    request: Request,
    settings: SettingsDependency,
) -> JwtPayload:
    try:
        access_token = require_access_token_from_cookies(request, settings=settings)
        return decode_access_token(access_token, settings=settings)
    except CookieError as exc:
        raise unauthorized_exception("Access token отсутствует.") from exc
    except JwtExpiredError as exc:
        raise unauthorized_exception("Срок действия access token истёк.") from exc
    except JwtInvalidTokenTypeError as exc:
        raise unauthorized_exception("Передан токен недопустимого типа.") from exc
    except JwtInvalidClaimsError as exc:
        raise unauthorized_exception("Access token содержит некорректные данные.") from exc
    except JwtTokenError as exc:
        raise unauthorized_exception("Access token недействителен.") from exc


async def get_optional_access_payload(
    request: Request,
    settings: SettingsDependency,
) -> JwtPayload | None:
    access_token = get_access_token_from_cookies(request, settings=settings)
    if access_token is None:
        return None
    try:
        return decode_access_token(access_token, settings=settings)
    except JwtExpiredError as exc:
        raise unauthorized_exception("Срок действия access token истёк.") from exc
    except JwtInvalidTokenTypeError as exc:
        raise unauthorized_exception("Передан токен недопустимого типа.") from exc
    except JwtInvalidClaimsError as exc:
        raise unauthorized_exception("Access token содержит некорректные данные.") from exc
    except JwtTokenError as exc:
        raise unauthorized_exception("Access token недействителен.") from exc


async def get_current_refresh_payload(
    request: Request,
    settings: SettingsDependency,
) -> JwtPayload:
    try:
        refresh_token = require_refresh_token_from_cookies(request, settings=settings)
        return decode_refresh_token(refresh_token, settings=settings)
    except CookieError as exc:
        raise unauthorized_exception("Refresh token отсутствует.") from exc
    except JwtExpiredError as exc:
        raise unauthorized_exception("Срок действия refresh token истёк.") from exc
    except JwtInvalidTokenTypeError as exc:
        raise unauthorized_exception("Передан токен недопустимого типа.") from exc
    except JwtInvalidClaimsError as exc:
        raise unauthorized_exception("Refresh token содержит некорректные данные.") from exc
    except JwtTokenError as exc:
        raise unauthorized_exception("Refresh token недействителен.") from exc


async def get_optional_refresh_payload(
    request: Request,
    settings: SettingsDependency,
) -> JwtPayload | None:
    refresh_token = get_refresh_token_from_cookies(request, settings=settings)
    if refresh_token is None:
        return None
    try:
        return decode_refresh_token(refresh_token, settings=settings)
    except JwtExpiredError as exc:
        raise unauthorized_exception("Срок действия refresh token истёк.") from exc
    except JwtInvalidTokenTypeError as exc:
        raise unauthorized_exception("Передан токен недопустимого типа.") from exc
    except JwtInvalidClaimsError as exc:
        raise unauthorized_exception("Refresh token содержит некорректные данные.") from exc
    except JwtTokenError as exc:
        raise unauthorized_exception("Refresh token недействителен.") from exc


CurrentAccessPayloadDependency = Annotated[
    JwtPayload,
    Depends(get_current_access_payload),
]
OptionalAccessPayloadDependency = Annotated[
    JwtPayload | None,
    Depends(get_optional_access_payload),
]
CurrentRefreshPayloadDependency = Annotated[
    JwtPayload,
    Depends(get_current_refresh_payload),
]


__all__ = [
    "AUTHENTICATION_ERROR_HEADERS",
    "SettingsDependency",
    "DatabaseSessionDependency",
    "SecurityDependencyError",
    "unauthorized_exception",
    "forbidden_exception",
    "get_current_access_payload",
    "get_optional_access_payload",
    "get_current_refresh_payload",
    "get_optional_refresh_payload",
    "CurrentAccessPayloadDependency",
    "OptionalAccessPayloadDependency",
    "CurrentRefreshPayloadDependency",
]
