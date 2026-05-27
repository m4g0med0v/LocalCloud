import type { NodeRead, NodeListItem } from "./nodes";

export type FileProcessingStatus = "pending" | "processing" | "ready" | "failed";
export type FilePreviewStatus = "not_required" | "pending" | "generating" | "ready" | "failed";
export type StorageObjectStatus = string;

export interface FileRead {
  id: string;
  node_id: string;
  size_bytes: number;
  mime_type: string | null;
  extension: string | null;
  checksum: string | null;
  checksum_algorithm: string | null;
  storage_status: StorageObjectStatus;
  processing_status: FileProcessingStatus;
  preview_status: FilePreviewStatus;
  current_version_id: string | null;
  created_at: string;
  updated_at: string;
  node: NodeRead | null;
  name?: string;
}

export interface FileListItem {
  id: string;
  node_id: string;
  size_bytes: number;
  mime_type: string | null;
  extension: string | null;
  storage_status: StorageObjectStatus;
  processing_status: FileProcessingStatus;
  preview_status: FilePreviewStatus;
  created_at: string;
  updated_at: string;
  node: NodeListItem | null;
}

export interface FileRenameRequest {
  name: string;
}

export interface FileDownloadRequest {
  file_id: string;
  force_download?: boolean;
  version_id?: string;
  filename?: string;
}

export interface FileDownloadResponse {
  url?: string;
  download_url?: string;
  expires_at?: string;
  filename?: string;
}
