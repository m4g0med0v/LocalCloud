import type { NodeListItem } from "./nodes";

export type PublicLinkPermissionType = "view" | "download" | "upload";
export type PublicLinkStatus = "active" | "disabled" | "expired" | "revoked";

export interface PublicLinkCreateRequest {
  node_id: string;
  permission_type?: PublicLinkPermissionType;
  expires_at?: string | null;
  max_downloads?: number | null;
  password?: string | null;
  description?: string | null;
}

export interface PublicLinkRead {
  id: string;
  node_id: string;
  created_by: string | null;
  token: string;
  permission_type: PublicLinkPermissionType;
  status: PublicLinkStatus;
  expires_at: string | null;
  max_downloads: number | null;
  download_count: number;
  view_count: number;
  is_active: boolean;
  revoked_at: string | null;
  revoke_reason: string | null;
  last_accessed_at: string | null;
  description: string | null;
  created_at: string;
  has_password: boolean;
  node: NodeListItem | null;
  is_download_limit_reached: boolean;
  is_revoked: boolean;
}

export interface PublicLinkListItem {
  id: string;
  node_id: string;
  token: string;
  permission_type: PublicLinkPermissionType;
  status: PublicLinkStatus;
  expires_at: string | null;
  download_count: number;
  is_active: boolean;
  created_at: string;
  has_password: boolean;
  node: NodeListItem | null;
}

export interface PublicLinkRevokeRequest {
  revoke_reason?: string | null;
}

export interface PublicLinkPublicRead {
  id: string;
  node_id: string;
  permission_type: PublicLinkPermissionType;
  status: PublicLinkStatus;
  expires_at: string | null;
  has_password: boolean;
  description: string | null;
  node: import("./nodes").NodeListItem | null;
}

export interface PublicLinkDownloadResponse {
  presigned_url: string;
  expires_at: string;
  method: string;
  headers: Record<string, string>;
  filename: string | null;
  size_bytes: number | null;
  mime_type: string | null;
}

export type BackgroundTaskStatus = "pending" | "in_progress" | "completed" | "failed";

export interface PublicLinkFolderArchiveResponse {
  task_id: string;
  status: BackgroundTaskStatus;
  presigned_url: string | null;
  expires_at: string | null;
  filename: string | null;
  size_bytes: number | null;
}
