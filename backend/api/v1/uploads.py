from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request, status

from api.dependencies import get_uploads_service_dependency
from schemas.common import PageResponse
from schemas.uploads import (
    UploadAbortRequest,
    UploadCompleteRequest,
    UploadCompleteResponse,
    UploadPartCompleteRequest,
    UploadPartRead,
    UploadPresignedUrlsResponse,
    UploadProgressRead,
    UploadQueryParams,
    UploadSessionCreateRequest,
    UploadSessionListItem,
    UploadSessionRead,
)
from security import CurrentActiveUserDependency
from services import UploadsService

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post(
    "/",
    response_model=UploadSessionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_upload_session(
    data: UploadSessionCreateRequest,
    request: Request,
    current_user: CurrentActiveUserDependency,
    uploads_service: UploadsService = Depends(get_uploads_service_dependency),
) -> UploadSessionRead:
    """Создаёт upload-сессию multipart-загрузки."""

    client_ip = request.client.host if request.client is not None else None
    user_agent = request.headers.get("user-agent")
    upload_session, _ = await uploads_service.initiate_upload(
        data,
        user_id=current_user.id,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    return upload_session


@router.get(
    "/",
    response_model=PageResponse[UploadSessionListItem],
    status_code=status.HTTP_200_OK,
)
async def list_upload_sessions(
    current_user: CurrentActiveUserDependency,
    params: UploadQueryParams = Depends(),
    uploads_service: UploadsService = Depends(get_uploads_service_dependency),
) -> PageResponse[UploadSessionListItem]:
    """Возвращает список upload-сессий пользователя."""

    return await uploads_service.list_uploads(params, user_id=current_user.id)


@router.get(
    "/{upload_id}",
    response_model=UploadSessionRead,
    status_code=status.HTTP_200_OK,
)
async def get_upload_session(
    current_user: CurrentActiveUserDependency,
    upload_id: UUID = Path(...),
    uploads_service: UploadsService = Depends(get_uploads_service_dependency),
) -> UploadSessionRead:
    """Возвращает upload-сессию по идентификатору."""

    return await uploads_service.get_upload_session(upload_id, user_id=current_user.id)


@router.post(
    "/{upload_id}/parts/presigned",
    response_model=UploadPresignedUrlsResponse,
    status_code=status.HTTP_200_OK,
)
async def create_upload_part_presigned_urls(
    current_user: CurrentActiveUserDependency,
    upload_id: UUID = Path(...),
    uploads_service: UploadsService = Depends(get_uploads_service_dependency),
) -> UploadPresignedUrlsResponse:
    """Возвращает pre-signed URL для загрузки частей."""

    return await uploads_service.create_part_urls(upload_id, user_id=current_user.id)


@router.post(
    "/{upload_id}/parts/{part_number}/complete",
    response_model=UploadPartRead,
    status_code=status.HTTP_200_OK,
)
async def complete_upload_part(
    data: UploadPartCompleteRequest,
    current_user: CurrentActiveUserDependency,
    upload_id: UUID = Path(...),
    part_number: int = Path(..., ge=1),
    uploads_service: UploadsService = Depends(get_uploads_service_dependency),
) -> UploadPartRead:
    """Подтверждает успешную загрузку части multipart-сессии."""

    request_data = data.model_copy(update={"part_number": part_number})
    await uploads_service.confirm_part(
        upload_id,
        request_data,
        user_id=current_user.id,
    )
    parts = await uploads_service.get_upload_parts(upload_id, user_id=current_user.id)
    for part in parts:
        if part.part_number == part_number:
            return part
    raise ValueError("Не удалось получить подтверждённую часть загрузки.")


@router.post(
    "/{upload_id}/complete",
    response_model=UploadCompleteResponse,
    status_code=status.HTTP_200_OK,
)
async def complete_upload(
    data: UploadCompleteRequest,
    current_user: CurrentActiveUserDependency,
    upload_id: UUID = Path(...),
    uploads_service: UploadsService = Depends(get_uploads_service_dependency),
) -> UploadCompleteResponse:
    """Завершает multipart-загрузку файла."""

    request_data = data.model_copy(update={"upload_session_id": upload_id})
    return await uploads_service.complete_upload(
        request_data,
        user_id=current_user.id,
    )


@router.post(
    "/{upload_id}/abort",
    response_model=UploadSessionRead,
    status_code=status.HTTP_200_OK,
)
async def abort_upload(
    data: UploadAbortRequest,
    current_user: CurrentActiveUserDependency,
    upload_id: UUID = Path(...),
    uploads_service: UploadsService = Depends(get_uploads_service_dependency),
) -> UploadSessionRead:
    """Отменяет upload-сессию."""

    request_data = data.model_copy(update={"upload_session_id": upload_id})
    return await uploads_service.abort_upload(
        request_data,
        user_id=current_user.id,
    )


@router.get(
    "/{upload_id}/progress",
    response_model=UploadProgressRead,
    status_code=status.HTTP_200_OK,
)
async def get_upload_progress(
    current_user: CurrentActiveUserDependency,
    upload_id: UUID = Path(...),
    uploads_service: UploadsService = Depends(get_uploads_service_dependency),
) -> UploadProgressRead:
    """Возвращает прогресс upload-сессии."""

    return await uploads_service.get_progress(upload_id, user_id=current_user.id)


__all__ = ["router"]
