from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path, status

from api.dependencies import get_public_links_service_dependency
from schemas.common import PageResponse
from schemas.public_links import (
    PublicLinkAccessRequest,
    PublicLinkAccessResponse,
    PublicLinkCreateRequest,
    PublicLinkDownloadResponse,
    PublicLinkListItem,
    PublicLinkPublicRead,
    PublicLinkQueryParams,
    PublicLinkRead,
    PublicLinkRevokeRequest,
    PublicLinkUpdateRequest,
)
from security import CurrentActiveUserDependency
from services import PublicLinksService

router = APIRouter(prefix="/public-links", tags=["public-links"])


@router.post(
    "/",
    response_model=PublicLinkRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_public_link(
    data: PublicLinkCreateRequest,
    current_user: CurrentActiveUserDependency,
    public_links_service: PublicLinksService = Depends(get_public_links_service_dependency),
) -> PublicLinkRead:
    """Создаёт публичную ссылку на узел."""

    return await public_links_service.create_link(data, actor_id=current_user.id)


@router.get(
    "/",
    response_model=PageResponse[PublicLinkListItem],
    status_code=status.HTTP_200_OK,
)
async def list_public_links(
    current_user: CurrentActiveUserDependency,
    params: PublicLinkQueryParams = Depends(),
    public_links_service: PublicLinksService = Depends(get_public_links_service_dependency),
) -> PageResponse[PublicLinkListItem]:
    """Возвращает список публичных ссылок пользователя."""

    return await public_links_service.list_links(params, actor_id=current_user.id)


@router.get(
    "/{link_id}",
    response_model=PublicLinkRead,
    status_code=status.HTTP_200_OK,
)
async def get_public_link(
    current_user: CurrentActiveUserDependency,
    link_id: UUID = Path(...),
    public_links_service: PublicLinksService = Depends(get_public_links_service_dependency),
) -> PublicLinkRead:
    """Возвращает публичную ссылку по идентификатору."""

    return await public_links_service.get_link(link_id, actor_id=current_user.id)


@router.patch(
    "/{link_id}",
    response_model=PublicLinkRead,
    status_code=status.HTTP_200_OK,
)
async def update_public_link(
    data: PublicLinkUpdateRequest,
    current_user: CurrentActiveUserDependency,
    link_id: UUID = Path(...),
    public_links_service: PublicLinksService = Depends(get_public_links_service_dependency),
) -> PublicLinkRead:
    """Обновляет параметры публичной ссылки."""

    return await public_links_service.update_link(
        link_id,
        data,
        actor_id=current_user.id,
    )


@router.post(
    "/{link_id}/revoke",
    response_model=PublicLinkRead,
    status_code=status.HTTP_200_OK,
)
async def revoke_public_link(
    data: PublicLinkRevokeRequest,
    current_user: CurrentActiveUserDependency,
    link_id: UUID = Path(...),
    public_links_service: PublicLinksService = Depends(get_public_links_service_dependency),
) -> PublicLinkRead:
    """Отзывает публичную ссылку."""

    return await public_links_service.revoke_link(
        link_id,
        data,
        actor_id=current_user.id,
    )


@router.get(
    "/public/{token}",
    response_model=PublicLinkPublicRead,
    status_code=status.HTTP_200_OK,
)
async def get_public_link_by_token(
    token: str = Path(..., min_length=1, max_length=128),
    public_links_service: PublicLinksService = Depends(get_public_links_service_dependency),
) -> PublicLinkPublicRead:
    """Возвращает публичные данные ссылки по токену."""

    return await public_links_service.get_public_link(token)


@router.post(
    "/public/{token}/access",
    response_model=PublicLinkAccessResponse,
    status_code=status.HTTP_200_OK,
)
async def check_public_link_access(
    data: PublicLinkAccessRequest,
    token: str = Path(..., min_length=1, max_length=128),
    public_links_service: PublicLinksService = Depends(get_public_links_service_dependency),
) -> PublicLinkAccessResponse:
    """Проверяет доступ к публичной ссылке."""

    request_data = data.model_copy(update={"token": token})
    return await public_links_service.validate_access(request_data)


@router.post(
    "/public/{token}/download",
    response_model=PublicLinkDownloadResponse,
    status_code=status.HTTP_200_OK,
)
async def download_from_public_link(
    data: PublicLinkAccessRequest,
    token: str = Path(..., min_length=1, max_length=128),
    public_links_service: PublicLinksService = Depends(get_public_links_service_dependency),
) -> PublicLinkDownloadResponse:
    """Возвращает ссылку на скачивание по публичному токену."""

    request_data = data.model_copy(update={"token": token})
    return await public_links_service.create_public_download_url(request_data)


__all__ = ["router"]
