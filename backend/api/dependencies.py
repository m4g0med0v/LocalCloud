from __future__ import annotations

from fastapi import Request

from services import (
    AuditService,
    AuthService,
    DownloadsService,
    FilesService,
    FoldersService,
    HealthService,
    NodesService,
    PermissionsService,
    PublicLinksService,
    QuotasService,
    RegistrationService,
    RolesService,
    TasksService,
    TrashService,
    UploadsService,
    UsersService,
)
from services.audit import get_audit_service
from services.auth import get_auth_service
from services.downloads import get_downloads_service
from services.files import get_files_service
from services.folders import get_folders_service
from services.health import get_health_service
from services.nodes import get_nodes_service
from services.permissions import get_permissions_service
from services.public_links import get_public_links_service
from services.quotas import get_quotas_service
from services.registration import get_registration_service
from services.roles import get_roles_service
from services.tasks import get_tasks_service
from services.trash import get_trash_service
from services.uploads import get_uploads_service
from services.users import get_users_service


def get_auth_service_dependency() -> AuthService:
    return get_auth_service()


def get_registration_service_dependency() -> RegistrationService:
    return get_registration_service()


def get_users_service_dependency() -> UsersService:
    return get_users_service()


def get_roles_service_dependency() -> RolesService:
    return get_roles_service()


def get_quotas_service_dependency() -> QuotasService:
    return get_quotas_service()


def get_nodes_service_dependency() -> NodesService:
    return get_nodes_service()


def get_folders_service_dependency() -> FoldersService:
    return get_folders_service()


def get_files_service_dependency() -> FilesService:
    return get_files_service()


def get_uploads_service_dependency() -> UploadsService:
    return get_uploads_service()


def get_downloads_service_dependency() -> DownloadsService:
    return get_downloads_service()


def get_trash_service_dependency() -> TrashService:
    return get_trash_service()


def get_permissions_service_dependency() -> PermissionsService:
    return get_permissions_service()


def get_public_links_service_dependency() -> PublicLinksService:
    return get_public_links_service()


def get_audit_service_dependency() -> AuditService:
    return get_audit_service()


def get_tasks_service_dependency() -> TasksService:
    return get_tasks_service()


def get_health_service_dependency() -> HealthService:
    return get_health_service()


def get_health_service_from_request_dependency(request: Request) -> HealthService:
    health_service = getattr(request.app.state, "health_service", None)
    if isinstance(health_service, HealthService):
        return health_service
    return get_health_service()


__all__ = [
    "get_auth_service_dependency",
    "get_registration_service_dependency",
    "get_users_service_dependency",
    "get_roles_service_dependency",
    "get_quotas_service_dependency",
    "get_nodes_service_dependency",
    "get_folders_service_dependency",
    "get_files_service_dependency",
    "get_uploads_service_dependency",
    "get_downloads_service_dependency",
    "get_trash_service_dependency",
    "get_permissions_service_dependency",
    "get_public_links_service_dependency",
    "get_audit_service_dependency",
    "get_tasks_service_dependency",
    "get_health_service_dependency",
    "get_health_service_from_request_dependency",
]
