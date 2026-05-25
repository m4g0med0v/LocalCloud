from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, Request

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"
FORWARDED_FOR_HEADER = "X-Forwarded-For"
USER_AGENT_HEADER = "User-Agent"


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Контекст текущего HTTP-запроса."""

    request_id: str
    correlation_id: str
    client_ip: str | None = None
    user_agent: str | None = None


def build_request_context(request: Request) -> RequestContext:
    """Собирает контекст запроса из state и HTTP-заголовков."""

    existing = getattr(request.state, "request_context", None)
    if isinstance(existing, RequestContext):
        return existing

    request_id = _normalize_identifier(
        request.headers.get(REQUEST_ID_HEADER),
        fallback=uuid4().hex,
    )
    correlation_id = _normalize_identifier(
        request.headers.get(CORRELATION_ID_HEADER),
        fallback=request_id,
    )
    context = RequestContext(
        request_id=request_id,
        correlation_id=correlation_id,
        client_ip=_extract_client_ip(request),
        user_agent=_normalize_optional_text(request.headers.get(USER_AGENT_HEADER)),
    )
    request.state.request_context = context
    request.state.request_id = context.request_id
    request.state.correlation_id = context.correlation_id
    return context


def get_request_context(request: Request) -> RequestContext:
    """FastAPI dependency для получения контекста запроса."""

    return build_request_context(request)


def get_request_id(context: Annotated[RequestContext, Depends(get_request_context)]) -> str:
    """Возвращает идентификатор запроса."""

    return context.request_id


def get_correlation_id(
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> str:
    """Возвращает идентификатор корреляции."""

    return context.correlation_id


def get_client_ip(
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> str | None:
    """Возвращает IP-адрес клиента."""

    return context.client_ip


def get_user_agent(
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> str | None:
    """Возвращает User-Agent клиента."""

    return context.user_agent


RequestContextDependency = Annotated[RequestContext, Depends(get_request_context)]
RequestIdDependency = Annotated[str, Depends(get_request_id)]
CorrelationIdDependency = Annotated[str, Depends(get_correlation_id)]
ClientIpDependency = Annotated[str | None, Depends(get_client_ip)]
UserAgentDependency = Annotated[str | None, Depends(get_user_agent)]


def _extract_client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get(FORWARDED_FOR_HEADER)
    if forwarded_for:
        first_ip = forwarded_for.split(",", maxsplit=1)[0]
        normalized_ip = _normalize_optional_text(first_ip)
        if normalized_ip is not None:
            return normalized_ip

    if request.client is None:
        return None

    return _normalize_optional_text(request.client.host)


def _normalize_identifier(value: str | None, *, fallback: str) -> str:
    normalized_value = _normalize_optional_text(value)
    return normalized_value or fallback


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized_value = value.strip()
    return normalized_value or None


__all__ = [
    "REQUEST_ID_HEADER",
    "CORRELATION_ID_HEADER",
    "FORWARDED_FOR_HEADER",
    "USER_AGENT_HEADER",
    "RequestContext",
    "build_request_context",
    "get_request_context",
    "get_request_id",
    "get_correlation_id",
    "get_client_ip",
    "get_user_agent",
    "RequestContextDependency",
    "RequestIdDependency",
    "CorrelationIdDependency",
    "ClientIpDependency",
    "UserAgentDependency",
]
