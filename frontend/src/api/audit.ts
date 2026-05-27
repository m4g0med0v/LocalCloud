import api from "@/lib/api";
import type { PageResponse } from "@/types/common";
import type { AuditLog, AuditLogQueryParams } from "@/types/audit";

export const auditApi = {
  list: (params?: AuditLogQueryParams) =>
    api.get<PageResponse<AuditLog>>("/audit/logs", { params }).then((r) => r.data),
};
