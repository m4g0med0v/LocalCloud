import api from "@/lib/api";
import type { FolderCreateRequest, FolderPatchRequest, FolderRead, FolderContent, FolderArchiveResponse } from "@/types/folders";

export const foldersApi = {
  create: (data: FolderCreateRequest) =>
    api.post<FolderRead>("/folders/", data).then((r) => r.data),

  get: (id: string) =>
    api.get<FolderRead>(`/folders/${id}`).then((r) => r.data),

  patch: (id: string, data: FolderPatchRequest) =>
    api.patch<FolderRead>(`/folders/${id}`, data).then((r) => r.data),

  content: (id: string, params?: { limit?: number; offset?: number }) =>
    api.get<FolderContent>(`/folders/${id}/content`, { params }).then((r) => r.data),

  archive: (folderId: string, archiveName?: string) =>
    api
      .post<FolderArchiveResponse>(`/folders/${folderId}/archive`, {
        folder_id: folderId,
        archive_name: archiveName ?? null,
        include_deleted: false,
      })
      .then((r) => r.data),
};
