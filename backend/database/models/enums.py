from __future__ import annotations

from enum import StrEnum


class UserStatus(StrEnum):
    """Статус учётной записи пользователя."""

    PENDING = "pending"
    ACTIVE = "active"
    BLOCKED = "blocked"
    REJECTED = "rejected"
    DELETED = "deleted"


class SystemRole(StrEnum):
    """Системная роль пользователя."""

    ADMIN = "admin"
    USER = "user"


class RegistrationRequestStatus(StrEnum):
    """Статус запроса на регистрацию."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class TokenType(StrEnum):
    """Тип токена безопасности."""

    ACCESS = "access"
    REFRESH = "refresh"
    REGISTRATION_APPROVAL = "registration_approval"
    PASSWORD_RESET = "password_reset"
    PUBLIC_LINK = "public_link"


class SessionStatus(StrEnum):
    """Статус пользовательской сессии."""

    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class NodeType(StrEnum):
    """Тип узла в файловой системе."""

    FILE = "file"
    FOLDER = "folder"


class NodeVisibility(StrEnum):
    """Уровень видимости файлового узла."""

    PRIVATE = "private"
    SHARED = "shared"
    PUBLIC = "public"


class FileProcessingStatus(StrEnum):
    """Статус обработки файла после загрузки."""

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class FilePreviewStatus(StrEnum):
    """Статус генерации предпросмотра файла."""

    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class FileVersionStatus(StrEnum):
    """Статус версии файла."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class UploadSessionStatus(StrEnum):
    """Статус сессии многокомпонентной загрузки."""

    CREATED = "created"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"
    EXPIRED = "expired"


class UploadPartStatus(StrEnum):
    """Статус части многокомпонентной загрузки файла."""

    PENDING = "pending"
    UPLOADED = "uploaded"
    FAILED = "failed"


class StorageObjectStatus(StrEnum):
    """Статус физического объекта в MinIO/S3."""

    PENDING = "pending"
    AVAILABLE = "available"
    MISSING = "missing"
    CORRUPTED = "corrupted"
    DELETING = "deleting"
    DELETED = "deleted"


class PermissionLevel(StrEnum):
    """Уровень доступа к ресурсу."""

    READ = "read"
    DOWNLOAD = "download"
    WRITE = "write"
    DELETE = "delete"
    OWNER = "owner"


class PermissionSubjectType(StrEnum):
    """Тип субъекта, которому выдано разрешение."""

    USER = "user"
    ROLE = "role"
    PUBLIC_LINK = "public_link"


class PublicLinkPermissionType(StrEnum):
    """Тип доступа публичной ссылки."""

    VIEW = "view"
    DOWNLOAD = "download"
    UPLOAD = "upload"


class PublicLinkStatus(StrEnum):
    """Статус публичной ссылки."""

    ACTIVE = "active"
    DISABLED = "disabled"
    EXPIRED = "expired"
    REVOKED = "revoked"


class TrashItemStatus(StrEnum):
    """Статус элемента корзины."""

    IN_TRASH = "in_trash"
    RESTORED = "restored"
    PURGED = "purged"


class ArchiveStatus(StrEnum):
    """Статус подготовки ZIP-архива папки."""

    PENDING = "pending"
    BUILDING = "building"
    READY = "ready"
    FAILED = "failed"
    EXPIRED = "expired"
    DELETED = "deleted"


class QuotaResourceType(StrEnum):
    """Тип ресурса, на который действует квота."""

    STORAGE_BYTES = "storage_bytes"
    FILE_COUNT = "file_count"
    PUBLIC_LINK_COUNT = "public_link_count"
    UPLOAD_SESSION_COUNT = "upload_session_count"


class BackgroundTaskStatus(StrEnum):
    """Статус выполнения фоновой задачи."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BackgroundTaskType(StrEnum):
    """Тип фоновой задачи."""

    CREATE_FOLDER_ARCHIVE = "create_folder_archive"
    CLEAN_TRASH = "clean_trash"
    CLEAN_EXPIRED_UPLOADS = "clean_expired_uploads"
    CLEAN_EXPIRED_PUBLIC_LINKS = "clean_expired_public_links"
    DELETE_OBJECT_FROM_STORAGE = "delete_object_from_storage"
    CHECK_STORAGE_INTEGRITY = "check_storage_integrity"
    GENERATE_FILE_PREVIEW = "generate_file_preview"
    RECALCULATE_USER_QUOTA = "recalculate_user_quota"
    BACKUP_DATABASE = "backup_database"
    BACKUP_STORAGE = "backup_storage"


class TaskPriority(StrEnum):
    """Приоритет фоновой задачи."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class BackupStatus(StrEnum):
    """Статус резервного копирования."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class HealthStatus(StrEnum):
    """Статус состояния компонента системы."""

    OK = "ok"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class AuditAction(StrEnum):
    """Тип действия в журнале аудита."""

    # Аутентификация
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_LOGIN_FAILED = "user.login_failed"
    USER_REFRESH_TOKEN_ROTATED = "user.refresh_token_rotated"
    USER_SESSION_REVOKED = "user.session_revoked"

    # Пользователи и администрирование
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_BLOCKED = "user.blocked"
    USER_UNBLOCKED = "user.unblocked"
    USER_DELETED = "user.deleted"
    USER_ROLE_ASSIGNED = "user.role_assigned"
    USER_ROLE_REMOVED = "user.role_removed"

    # Регистрация
    REGISTRATION_REQUEST_CREATED = "registration.request_created"
    REGISTRATION_REQUEST_APPROVED = "registration.request_approved"
    REGISTRATION_REQUEST_REJECTED = "registration.request_rejected"
    REGISTRATION_REQUEST_CANCELLED = "registration.request_cancelled"

    # Папки
    FOLDER_CREATED = "folder.created"
    FOLDER_RENAMED = "folder.renamed"
    FOLDER_MOVED = "folder.moved"
    FOLDER_DELETED = "folder.deleted"
    FOLDER_RESTORED = "folder.restored"
    FOLDER_PURGED = "folder.purged"
    FOLDER_ARCHIVE_REQUESTED = "folder.archive_requested"
    FOLDER_ARCHIVE_CREATED = "folder.archive_created"

    # Файлы
    FILE_UPLOAD_STARTED = "file.upload_started"
    FILE_UPLOADED = "file.uploaded"
    FILE_UPLOAD_FAILED = "file.upload_failed"
    FILE_DOWNLOADED = "file.downloaded"
    FILE_RENAMED = "file.renamed"
    FILE_MOVED = "file.moved"
    FILE_UPDATED = "file.updated"
    FILE_DELETED = "file.deleted"
    FILE_RESTORED = "file.restored"
    FILE_PURGED = "file.purged"
    FILE_VERSION_CREATED = "file.version_created"
    FILE_VERSION_RESTORED = "file.version_restored"
    FILE_PREVIEW_GENERATED = "file.preview_generated"

    # Общие узлы файловой системы
    NODE_CREATED = "node.created"
    NODE_RENAMED = "node.renamed"
    NODE_MOVED = "node.moved"
    NODE_DELETED = "node.deleted"
    NODE_RESTORED = "node.restored"
    NODE_PURGED = "node.purged"

    # Разрешения
    PERMISSION_GRANTED = "permission.granted"
    PERMISSION_UPDATED = "permission.updated"
    PERMISSION_REVOKED = "permission.revoked"

    # Публичные ссылки
    PUBLIC_LINK_CREATED = "public_link.created"
    PUBLIC_LINK_OPENED = "public_link.opened"
    PUBLIC_LINK_DOWNLOADED = "public_link.downloaded"
    PUBLIC_LINK_REVOKED = "public_link.revoked"
    PUBLIC_LINK_EXPIRED = "public_link.expired"

    # Сеансы загрузки
    UPLOAD_SESSION_CREATED = "upload_session.created"
    UPLOAD_SESSION_COMPLETED = "upload_session.completed"
    UPLOAD_SESSION_FAILED = "upload_session.failed"
    UPLOAD_SESSION_ABORTED = "upload_session.aborted"
    UPLOAD_SESSION_EXPIRED = "upload_session.expired"

    # Квоты
    QUOTA_CREATED = "quota.created"
    QUOTA_UPDATED = "quota.updated"
    QUOTA_EXCEEDED = "quota.exceeded"
    QUOTA_RECALCULATED = "quota.recalculated"

    # Фоновые задачи
    BACKGROUND_TASK_CREATED = "background_task.created"
    BACKGROUND_TASK_STARTED = "background_task.started"
    BACKGROUND_TASK_COMPLETED = "background_task.completed"
    BACKGROUND_TASK_FAILED = "background_task.failed"
    BACKGROUND_TASK_CANCELLED = "background_task.cancelled"

    # Хранение и целостность
    STORAGE_OBJECT_DELETED = "storage.object_deleted"
    STORAGE_OBJECT_DELETE_FAILED = "storage.object_delete_failed"
    STORAGE_INTEGRITY_CHECK_STARTED = "storage.integrity_check_started"
    STORAGE_INTEGRITY_CHECK_COMPLETED = "storage.integrity_check_completed"
    STORAGE_INTEGRITY_PROBLEM_FOUND = "storage.integrity_problem_found"

    # Резервное копирование
    BACKUP_STARTED = "backup.started"
    BACKUP_COMPLETED = "backup.completed"
    BACKUP_FAILED = "backup.failed"

    # Безопасность
    SECURITY_PERMISSION_DENIED = "security.permission_denied"
    SECURITY_SUSPICIOUS_ACTIVITY = "security.suspicious_activity"
    SECURITY_PUBLIC_LINK_PASSWORD_FAILED = "security.public_link_password_failed"


class AuditResourceType(StrEnum):
    """Тип ресурса, к которому относится запись журнала аудита."""

    USER = "user"
    ROLE = "role"
    REGISTRATION_REQUEST = "registration_request"
    SESSION = "session"
    FILE = "file"
    FOLDER = "folder"
    NODE = "node"
    UPLOAD_SESSION = "upload_session"
    PUBLIC_LINK = "public_link"
    PERMISSION = "permission"
    QUOTA = "quota"
    BACKGROUND_TASK = "background_task"
    STORAGE_OBJECT = "storage_object"
    SYSTEM = "system"


class AuditResult(StrEnum):
    """Результат действия, зафиксированного в журнале аудита."""

    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"
    WARNING = "warning"
