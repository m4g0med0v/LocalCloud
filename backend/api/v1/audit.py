from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Response, status
from fastapi.responses import JSONResponse

from api.dependencies import get_audit_service_dependency
from schemas.audit import (
    AuditExportRequest,
    AuditLogListItem,
    AuditLogRead,
    AuditQueryParams,
    AuditSummaryRead,
)
from schemas.common import PageResponse
from security import CurrentAdminUserDependency
from services import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get(
    "/logs",
    response_model=PageResponse[AuditLogListItem],
    status_code=status.HTTP_200_OK,
)
async def list_audit_logs(
    _: CurrentAdminUserDependency,
    params: AuditQueryParams = Depends(),
    audit_service: AuditService = Depends(get_audit_service_dependency),
) -> PageResponse[AuditLogListItem]:
    """Возвращает журнал аудита с фильтрами и пагинацией."""

    return await audit_service.list_logs(params)


@router.get(
    "/logs/{log_id}",
    response_model=AuditLogRead,
    status_code=status.HTTP_200_OK,
)
async def get_audit_log(
    _: CurrentAdminUserDependency,
    log_id: UUID = Path(...),
    audit_service: AuditService = Depends(get_audit_service_dependency),
) -> AuditLogRead:
    """Возвращает одно событие аудита по идентификатору."""

    return await audit_service.get_log(log_id)


@router.get(
    "/summary",
    response_model=AuditSummaryRead,
    status_code=status.HTTP_200_OK,
)
async def get_audit_summary(
    _: CurrentAdminUserDependency,
    params: AuditQueryParams = Depends(),
    audit_service: AuditService = Depends(get_audit_service_dependency),
) -> AuditSummaryRead:
    """Возвращает агрегированную сводку по событиям аудита."""

    return await audit_service.get_summary(params)


@router.post(
    "/export",
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def export_audit_logs(
    data: AuditExportRequest,
    _: CurrentAdminUserDependency,
    audit_service: AuditService = Depends(get_audit_service_dependency),
) -> Response:
    """Экспортирует журнал аудита в JSON или CSV."""

    payload = await audit_service.export_logs(data)
    content = str(payload.get("content", ""))
    filename = str(payload.get("filename", "audit_logs.export"))
    content_type = str(payload.get("content_type", "application/octet-stream"))
    export_format = str(payload.get("format", "")).lower()

    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}

    if export_format == "json":
        parsed = json.loads(content) if content else []
        return JSONResponse(content=parsed, headers=headers)

    if export_format == "csv":
        return Response(content=content, media_type="text/csv", headers=headers)

    return Response(content=content, media_type=content_type, headers=headers)


@router.get(
    "/users/{user_id}/latest",
    response_model=list[AuditLogListItem],
    status_code=status.HTTP_200_OK,
)
async def get_latest_user_audit_logs(
    _: CurrentAdminUserDependency,
    user_id: UUID = Path(...),
    limit: int = 20,
    audit_service: AuditService = Depends(get_audit_service_dependency),
) -> list[AuditLogListItem]:
    """Возвращает последние события аудита указанного пользователя."""

    return await audit_service.get_latest_user_logs(user_id, limit=limit)


__all__ = ["router"]
