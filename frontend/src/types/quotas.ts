export interface UserQuota {
  id: string;
  user_id: string;
  storage_limit_bytes: number;
  storage_used_bytes: number;
  max_file_size_bytes: number;
  files_limit: number | null;
  files_used: number;
  public_links_limit: number | null;
  public_links_used: number;
  active_upload_sessions_limit: number | null;
  active_upload_sessions_used: number;
  created_at: string;
  updated_at: string;
}

export interface QuotaUsageRead {
  user_id: string;
  storage_limit_bytes: number;
  storage_used_bytes: number;
  max_file_size_bytes: number;
  files_limit: number | null;
  files_used: number;
  public_links_limit: number | null;
  public_links_used: number;
  active_upload_sessions_limit: number | null;
  active_upload_sessions_used: number;
  available_storage_bytes: number;
  usage_percent: number;
  is_storage_full: boolean;
  is_files_limit_reached: boolean;
  is_public_links_limit_reached: boolean;
  is_active_upload_sessions_limit_reached: boolean;
}

export interface UserQuotaUpdate {
  storage_limit_bytes?: number | null;
  max_file_size_bytes?: number | null;
  files_limit?: number | null;
  public_links_limit?: number | null;
  active_upload_sessions_limit?: number | null;
}
