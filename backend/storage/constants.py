from re import Pattern, compile
from typing import Final


class StorageConstants:
    """Значения по умолчанию для настроек MinIO."""

    MINIO_HOST: Final[str] = "localhost"
    MINIO_PORT: Final[int] = 9000
    MINIO_PUBLIC_HOST: Final[str] = "localhost"
    MINIO_PUBLIC_PORT: Final[int] = 9000
    MINIO_ACCESS_KEY: Final[str] = "localcloud"
    MINIO_SECRET_KEY: Final[str] = "localcloud_password"
    MINIO_SECURE: Final[bool] = False
    MINIO_REGION: Final[str] = "us-east-1"

    MINIO_BUCKET_FILES: Final[str] = "localcloud-files"
    MINIO_BUCKET_TEMP: Final[str] = "localcloud-temp"
    MINIO_BUCKET_ARCHIVES: Final[str] = "localcloud-archives"
    STORAGE_HEALTHCHECK_OBJECT_PREFIX: Final[str] = "health-check"
    STORAGE_HEALTHCHECK_OBJECT_CONTENT_TYPE: Final[str] = "text/plain"
    STORAGE_HEALTHCHECK_OBJECT_PAYLOAD: Final[bytes] = (
        b"localcloud-storage-health-check"
    )

    MULTIPART_MAX_PARTS: Final[int] = 10_000
    S3_BUCKET_NAME_MIN_LENGTH: Final[int] = 3
    S3_BUCKET_NAME_MAX_LENGTH: Final[int] = 63
    S3_OBJECT_KEY_MAX_LENGTH: Final[int] = 1024
    S3_MULTIPART_MIN_PART_NUMBER: Final[int] = 1
    STORAGE_EXTENSION_MAX_LENGTH: Final[int] = 32
    STORAGE_METADATA_KEY_MAX_LENGTH: Final[int] = 64
    S3_MULTIPART_MIN_PART_SIZE_BYTES: Final[int] = 1
    S3_MULTIPART_MAX_PART_NUMBER: Final[int] = 10_000
    S3_PRESIGNED_MIN_EXPIRES_IN_SECONDS: Final[int] = 1
    STORAGE_METADATA_VALUE_MAX_LENGTH: Final[int] = 2048
    PRESIGNED_UPLOAD_EXPIRE_SECONDS: Final[int] = 60 * 15
    STORAGE_METADATA_TOTAL_MAX_SIZE: Final[int] = 8 * 1024
    STORAGE_FILENAME_METADATA_MAX_LENGTH: Final[int] = 255
    PRESIGNED_DOWNLOAD_EXPIRE_SECONDS: Final[int] = 60 * 15
    MULTIPART_PART_SIZE_BYTES: Final[int] = 8 * 1024 * 1024
    STORAGE_DEFAULT_LATENCY_THRESHOLD_MS: Final[float] = 500.0
    STORAGE_DEFAULT_CHECKSUM_CHUNK_SIZE: Final[int] = 1024 * 1024
    S3_PRESIGNED_MAX_EXPIRES_IN_SECONDS: Final[int] = 7 * 24 * 60 * 60
    S3_MULTIPART_MIN_NON_LAST_PART_SIZE_BYTES: Final[int] = 5 * 1024 * 1024
    S3_POST_POLICY_MAX_OBJECT_SIZE_BYTES: Final[int] = 5 * 1024 * 1024 * 1024

    SYSTEM_PATH_PREFIX_PATTERN: Final[Pattern] = compile(r"^[a-zA-Z]:/")
    UNSAFE_EXTENSION_CHARS_PATTERN: Final[Pattern] = compile(r"[^a-z0-9]+")
    FORBIDDEN_METADATA_VALUE_CHARS_PATTERN: Final[Pattern] = compile(r"[\r\n]")
    IP_ADDRESS_LIKE_PATTERN: Final[Pattern] = compile(r"^\d{1,3}(\.\d{1,3}){3}$")
    BUCKET_NAME_PATTERN: Final[Pattern] = compile(r"^[a-z0-9][a-z0-9.-]*[a-z0-9]$")
    UNSAFE_FILENAME_CHARS_PATTERN: Final[Pattern] = compile(r"[\x00-\x1f\x7f/\\]+")
    ALLOWED_METADATA_KEY_PATTERN: Final[Pattern] = compile(r"^[a-z0-9][a-z0-9_-]*$")

    FORBIDDEN_OBJECT_KEY_PARTS: Final[set[str]] = {"", ".", ".."}
    RESERVED_METADATA_KEYS: Final[set[str]] = {
        "user_id",
        "file_id",
        "version_id",
        "upload_session_id",
        "task_id",
        "checksum",
        "checksum_algorithm",
        "original_filename",
        "content_type",
        "created_by",
    }
