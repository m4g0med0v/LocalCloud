import api from "@/lib/api";
import type { PageResponse } from "@/types/common";
import type {
  PermissionGrantRequest,
  NodePermissionRead,
  NodePermissionListItem,
  PermissionRevokeRequest,
} from "@/types/permissions";

export const permissionsApi = {
  grant: (data: PermissionGrantRequest) =>
    api.post<NodePermissionRead>("/permissions/grant", data).then((r) => r.data),

  listForNode: (nodeId: string, params?: { limit?: number; offset?: number; active_only?: boolean }) =>
    api
      .get<PageResponse<NodePermissionListItem>>(`/permissions/nodes/${nodeId}`, { params })
      .then((r) => r.data),

  revoke: (data: PermissionRevokeRequest) =>
    api.post<NodePermissionRead>("/permissions/revoke", data).then((r) => r.data),
};
