import api from "@/lib/api";
import type { UserQuota, QuotaUsageRead, UserQuotaUpdate } from "@/types/quotas";

export const quotasApi = {
  me: () => api.get<QuotaUsageRead>("/quotas/me").then((r) => r.data),

  getByUserId: (userId: string) =>
    api.get<QuotaUsageRead>(`/quotas/users/${userId}`).then((r) => r.data),

  updateByUserId: (userId: string, data: UserQuotaUpdate) =>
    api.put<UserQuota>(`/quotas/users/${userId}`, data).then((r) => r.data),
};
