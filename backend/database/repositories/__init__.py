"""
Пакет репозиториев базы данных.

Модуль экспортирует репозитории слоя доступа к данным.

Репозитории инкапсулируют SQLAlchemy-запросы и операции над ORM-моделями,
но не выполняют commit и rollback самостоятельно. Управление транзакциями
должно находиться на уровне сервисов или Unit of Work.
"""

from __future__ import annotations

from database.repositories.audit import (
    AuditLogRepository,
    AuditSortField,
)
from database.repositories.audit import (
    SortDirection as AuditSortDirection,
)
from database.repositories.base import BaseRepository
from database.repositories.files import (
    FileRepository,
    FileStorageInfo,
)
from database.repositories.folders import (
    FolderRepository,
    FolderSortField,
)
from database.repositories.links import (
    PublicLinkSortField,
    PublicLinksRepository,
)
from database.repositories.links import (
    SortDirection as PublicLinkSortDirection,
)
from database.repositories.nodes import (
    FileSystemNodeRepository,
    NodeSortDirection,
    NodeSortField,
)
from database.repositories.parts import (
    UploadedPartCompletionInfo,
    UploadPartsRepository,
)
from database.repositories.permissions import NodePermissionsRepository
from database.repositories.quotas import UserQuotaRepository
from database.repositories.registration import RegistrationRequestsRepository
from database.repositories.roles import RolesRepository
from database.repositories.sessions import UploadSessionsRepository
from database.repositories.tasks import (
    BackgroundTasksRepository,
    TaskSortField,
)
from database.repositories.tasks import (
    SortDirection as BackgroundTaskSortDirection,
)
from database.repositories.tokens import RefreshTokensRepository
from database.repositories.trash import (
    TrashItemRepository,
    TrashItemSortField,
    TrashSortDirection,
)
from database.repositories.users import UsersRepository
from database.repositories.versions import (
    FileVersionRepository,
    FileVersionStorageInfo,
)

__all__ = [
    # Base
    "BaseRepository",
    # Audit
    "AuditLogRepository",
    "AuditSortField",
    "AuditSortDirection",
    # Roles
    "RolesRepository",
    # Users
    "UsersRepository",
    # Registration
    "RegistrationRequestsRepository",
    # Tokens
    "RefreshTokensRepository",
    # Upload sessions
    "UploadSessionsRepository",
    # Quotas
    "UserQuotaRepository",
    # File system nodes
    "FileSystemNodeRepository",
    "NodeSortField",
    "NodeSortDirection",
    # Folders
    "FolderRepository",
    "FolderSortField",
    # Files
    "FileRepository",
    "FileStorageInfo",
    # Versions
    "FileVersionRepository",
    "FileVersionStorageInfo",
    # Upload parts
    "UploadPartsRepository",
    "UploadedPartCompletionInfo",
    # Permissions
    "NodePermissionsRepository",
    # Trash
    "TrashItemRepository",
    "TrashItemSortField",
    "TrashSortDirection",
    # Public links
    "PublicLinksRepository",
    "PublicLinkSortField",
    "PublicLinkSortDirection",
    # Background tasks
    "BackgroundTasksRepository",
    "TaskSortField",
    "BackgroundTaskSortDirection",
]
