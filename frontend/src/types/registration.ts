export type RegistrationStatus = "pending" | "approved" | "rejected" | "cancelled";

export interface RegistrationCreateRequest {
  email: string;
  username: string;
  password: string;
}

export interface RegistrationRead {
  id: string;
  email: string;
  username: string;
  status: RegistrationStatus;
  comment: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
}

export interface RegistrationApproveRequest {
  is_email_verified?: boolean;
  comment?: string | null;
}

export interface RegistrationApproveResponse {
  request: RegistrationRead;
  created_user_id: string | null;
}

export interface RegistrationRejectRequest {
  rejection_reason: string;
  comment?: string | null;
}
