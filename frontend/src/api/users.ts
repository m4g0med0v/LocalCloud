import api from "@/lib/api";
import type { PageResponse } from "@/types/common";
import type { UserRead, UserListItem } from "@/types/users";

export const usersApi = {
  list: (params?: { limit?: number; offset?: number; status?: string; search?: string }) =>
    api.get<PageResponse<UserListItem>>("/users", { params }).then((r) => r.data),

  get: (id: string) =>
    api.get<UserRead>(`/users/${id}`).then((r) => r.data),

  block: (id: string, block_reason?: string) =>
    api.post<UserRead>(`/users/${id}/block`, { block_reason: block_reason ?? null }).then((r) => r.data),

  unblock: (id: string) =>
    api.post<UserRead>(`/users/${id}/unblock`).then((r) => r.data),

  approve: (id: string, is_email_verified = true) =>
    api.post<UserRead>(`/users/${id}/approve`, { is_email_verified }).then((r) => r.data),

  reject: (id: string, rejection_reason: string) =>
    api.post<UserRead>(`/users/${id}/reject`, { rejection_reason }).then((r) => r.data),

  delete: (id: string) =>
    api.delete<UserRead>(`/users/${id}`).then((r) => r.data),
};
