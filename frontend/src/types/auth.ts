import type { CurrentUser } from "./users";

export interface LoginRequest {
  email_or_username: string;
  password: string;
}

export interface LoginResponse {
  authenticated: boolean;
  user: CurrentUser;
  message: string;
}

export interface LogoutResponse {
  authenticated: boolean;
  message: string;
}

export interface RefreshResponse {
  authenticated: boolean;
  user: CurrentUser | null;
  message: string;
}

export interface AuthSession {
  id: string;
  user_id: string;
  status: string;
  expires_at: string;
  revoked_at: string | null;
  revoke_reason: string | null;
  ip_address: string | null;
  user_agent: string | null;
  device_name: string | null;
  is_active: boolean;
  created_at: string;
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
}

export interface PasswordResetRequest {
  email: string;
}

export interface PasswordResetRequestResponse {
  reset_token: string;
  expires_at: string;
  message: string;
}

export interface PasswordResetConfirmRequest {
  token: string;
  new_password: string;
}

export interface PasswordResetConfirmResponse {
  message: string;
}
