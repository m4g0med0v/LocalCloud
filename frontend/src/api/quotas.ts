import api from "@/lib/api";
import type {
  UserQuota,
  QuotaUsageRead,
  UserQuotaUpdate,
  QuotaIncreaseRequest,
  QuotaIncreaseRequestStatus,
  ServerStorage,
} from "@/types/quotas";

export const quotasApi = {
  me: () => api.get<QuotaUsageRead>("/quotas/me").then((r) => r.data),

  getByUserId: (userId: string) =>
    api.get<QuotaUsageRead>(`/quotas/users/${userId}`).then((r) => r.data),

  updateByUserId: (userId: string, data: UserQuotaUpdate) =>
    api.put<UserQuota>(`/quotas/users/${userId}`, data).then((r) => r.data),

  serverStorage: () =>
    api.get<ServerStorage>("/quotas/server-storage").then((r) => r.data),

  listIncreaseRequests: (params?: {
    status?: QuotaIncreaseRequestStatus | "";
    limit?: number;
    offset?: number;
  }) =>
    api
      .get<QuotaIncreaseRequest[]>("/quotas/increase-requests", { params })
      .then((r) => r.data),

  approveIncreaseRequest: (id: string) =>
    api.post<QuotaIncreaseRequest>(`/quotas/increase-requests/${id}/approve`).then((r) => r.data),

  rejectIncreaseRequest: (id: string, data: { admin_comment: string | null }) =>
    api
      .post<QuotaIncreaseRequest>(`/quotas/increase-requests/${id}/reject`, data)
      .then((r) => r.data),
};
