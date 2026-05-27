import api from "@/lib/api";
import type { PageResponse } from "@/types/common";
import type { NodeRead, NodeListItem, NodeMoveRequest } from "@/types/nodes";
import type { FolderContent } from "@/types/folders";
import type { FileDownloadResponse } from "@/types/files";

export const nodesApi = {
  list: (params?: { parent_id?: string | null; limit?: number; offset?: number }) =>
    api.get<PageResponse<NodeListItem>>("/nodes/", { params }).then((r) => r.data),

  get: (id: string) =>
    api.get<NodeRead>(`/nodes/${id}`).then((r) => r.data),

  content: (nodeId: string) =>
    api.get<FolderContent>(`/nodes/${nodeId}/content`).then((r) => r.data),

  rename: (id: string, name: string) =>
    api.post(`/nodes/${id}/rename`, { name }).then((r) => r.data),

  download: (id: string) =>
    api.post<FileDownloadResponse>(`/nodes/${id}/download`, {}).then((r) => r.data),

  softDelete: (id: string) =>
    api.delete(`/nodes/${id}`).then((r) => r.data),

  search: (query: string, params?: { limit?: number; offset?: number }) =>
    api
      .get<PageResponse<NodeListItem>>("/nodes/search", { params: { query, ...params } })
      .then((r) => r.data),

  tree: (rootNodeId: string, params?: { depth?: number }) =>
    api
      .get<NodeRead[]>("/nodes/tree", { params: { root_node_id: rootNodeId, ...params } })
      .then((r) => r.data),

  move: (id: string, data: NodeMoveRequest) =>
    api.post(`/nodes/${id}/move`, data).then((r) => r.data),
};
