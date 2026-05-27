import api from "@/lib/api";
import type {
  LoginRequest,
  LoginResponse,
  LogoutResponse,
  RefreshResponse,
  AuthSession,
  PasswordChangeRequest,
  PasswordResetRequest,
  PasswordResetRequestResponse,
  PasswordResetConfirmRequest,
  PasswordResetConfirmResponse,
  CurrentUser,
} from "@/types";

export const authApi = {
  login: (data: LoginRequest) =>
    api.post<LoginResponse>("/auth/login", data).then((r) => r.data),

  logout: () =>
    api.post<LogoutResponse>("/auth/logout").then((r) => r.data),

  refresh: () =>
    api.post<RefreshResponse>("/auth/refresh").then((r) => r.data),

  me: () =>
    api.get<CurrentUser>("/auth/me").then((r) => r.data),

  sessions: () =>
    api.get<AuthSession[]>("/auth/sessions").then((r) => r.data),

  changePassword: (data: PasswordChangeRequest) =>
    api.post("/auth/password/change", data).then((r) => r.data),

  requestPasswordReset: (data: PasswordResetRequest) =>
    api
      .post<PasswordResetRequestResponse>("/auth/password/reset/request", data)
      .then((r) => r.data),

  confirmPasswordReset: (data: PasswordResetConfirmRequest) =>
    api
      .post<PasswordResetConfirmResponse>("/auth/password/reset/confirm", data)
      .then((r) => r.data),
};
