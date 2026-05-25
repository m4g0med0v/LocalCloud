from __future__ import annotations

import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.dependencies import (
    CORRELATION_ID_HEADER,
    REQUEST_ID_HEADER,
    RequestContext,
    USER_AGENT_HEADER,
    build_request_context,
)
from core.logging import get_logger

logger = get_logger("app.middleware")

DEFAULT_CORS_ORIGINS: tuple[str, ...] = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Назначает request/correlation id и ведёт request-логирование."""

    async def dispatch(self, request: Request, call_next) -> Response:
        context = self._get_or_create_context(request)
        started_at = time.perf_counter()

        logger.info(
            "HTTP request started.",
            extra={
                "method": request.method,
                "path": request.url.path,
                "request_id": context.request_id,
                "correlation_id": context.correlation_id,
                "client_ip": context.client_ip,
                "user_agent": context.user_agent,
            },
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 3)
            logger.exception(
                "HTTP request failed.",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "request_id": context.request_id,
                    "correlation_id": context.correlation_id,
                    "duration_ms": duration_ms,
                    "error_type": exc.__class__.__name__,
                },
            )
            raise

        duration_ms = round((time.perf_counter() - started_at) * 1000, 3)
        response.headers[REQUEST_ID_HEADER] = context.request_id
        response.headers[CORRELATION_ID_HEADER] = context.correlation_id

        logger.info(
            "HTTP request finished.",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "request_id": context.request_id,
                "correlation_id": context.correlation_id,
                "duration_ms": duration_ms,
            },
        )
        return response

    @staticmethod
    def _get_or_create_context(request: Request) -> RequestContext:
        existing = getattr(request.state, "request_context", None)
        if isinstance(existing, RequestContext):
            return existing

        context = build_request_context(request)
        if not context.request_id:
            context = RequestContext(
                request_id=uuid4().hex,
                correlation_id=context.correlation_id or uuid4().hex,
                client_ip=context.client_ip,
                user_agent=context.user_agent,
            )
            request.state.request_context = context
            request.state.request_id = context.request_id
            request.state.correlation_id = context.correlation_id
        return context


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Добавляет базовые security headers к ответам."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
        return response


def install_middleware(app: FastAPI) -> None:
    """Подключает middleware backend-приложения."""

    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(DEFAULT_CORS_ORIGINS),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*", REQUEST_ID_HEADER, CORRELATION_ID_HEADER, USER_AGENT_HEADER],
        expose_headers=[REQUEST_ID_HEADER, CORRELATION_ID_HEADER],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware)


__all__ = [
    "DEFAULT_CORS_ORIGINS",
    "RequestContextMiddleware",
    "SecurityHeadersMiddleware",
    "install_middleware",
]
