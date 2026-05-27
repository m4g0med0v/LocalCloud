import api from "@/lib/api";
import type { PageResponse } from "@/types/common";
import type {
  PublicLinkCreateRequest,
  PublicLinkRead,
  PublicLinkListItem,
  PublicLinkRevokeRequest,
  PublicLinkPublicRead,
  PublicLinkDownloadResponse,
} from "@/types/public-links";

export const publicLinksApi = {
  create: (data: PublicLinkCreateRequest) =>
    api.post<PublicLinkRead>("/public-links/", data).then((r) => r.data),

  list: (params?: { limit?: number; offset?: number; node_id?: string; is_active?: boolean }) =>
    api
      .get<PageResponse<PublicLinkListItem>>("/public-links/", { params })
      .then((r) => r.data),

  listForNode: (nodeId: string) =>
    api
      .get<PageResponse<PublicLinkListItem>>("/public-links/", {
        params: { node_id: nodeId, is_active: true, limit: 10 },
      })
      .then((r) => r.data),

  get: (id: string) =>
    api.get<PublicLinkRead>(`/public-links/${id}`).then((r) => r.data),

  getPublic: (token: string) =>
    api.get<PublicLinkPublicRead>(`/public-links/public/${token}`).then((r) => r.data),

  download: (token: string) =>
    api
      .post<PublicLinkDownloadResponse>(`/public-links/public/${token}/download`, { token })
      .then((r) => r.data),

  revoke: (id: string, data: PublicLinkRevokeRequest = {}) =>
    api.post<PublicLinkRead>(`/public-links/${id}/revoke`, data).then((r) => r.data),
};
