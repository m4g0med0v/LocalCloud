export type UploadSessionStatus =
  | "created"
  | "uploading"
  | "completed"
  | "failed"
  | "aborted"
  | "expired";

export type UploadPartStatus = "pending" | "uploaded" | "failed";

export interface UploadSessionCreateRequest {
  parent_node_id: string;
  filename: string;
  file_size_bytes: number;
  parts_count: number;
  mime_type?: string | null;
  part_size_bytes?: number | null;
  checksum?: string | null;
  checksum_algorithm?: string | null;
}

export interface UploadSessionRead {
  id: string;
  user_id: string;
  parent_node_id: string;
  file_name: string;
  file_size_bytes: number;
  part_size_bytes: number;
  mime_type: string | null;
  status: UploadSessionStatus;
  parts_count: number;
  uploaded_parts_count: number;
  uploaded_bytes: number;
  expires_at: string;
  completed_at: string | null;
  created_at: string;
  progress_percent: number;
  is_completed: boolean;
  is_terminal: boolean;
}

export interface PresignedPart {
  part_number: number;
  url: string;
  headers: Record<string, string>;
}

export interface PresignedPartsResponse {
  parts: PresignedPart[];
}

export interface UploadPartCompleteRequest {
  part_number: number;
  etag: string;
  size_bytes: number;
}

export interface UploadCompletePart {
  part_number: number;
  etag: string;
  size_bytes: number;
}

export interface UploadCompleteRequest {
  upload_session_id: string;
  parts: UploadCompletePart[];
}

export interface UploadCompleteResponse {
  status: UploadSessionStatus;
  file_id: string | null;
  upload_session_id: string;
}
