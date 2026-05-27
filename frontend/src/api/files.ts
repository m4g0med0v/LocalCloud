import api from "@/lib/api";
import type { PageResponse } from "@/types/common";
import type { FileRead, FileListItem, FileRenameRequest, FileDownloadResponse } from "@/types/files";

export const filesApi = {
  list: (params?: { limit?: number; offset?: number }) =>
    api.get<PageResponse<FileListItem>>("/files/", { params }).then((r) => r.data),

  get: (id: string) =>
    api.get<FileRead>(`/files/${id}`).then((r) => r.data),

  rename: (id: string, data: FileRenameRequest) =>
    api.post<FileRead>(`/files/${id}/rename`, data).then((r) => r.data),

  download: (id: string, forceDownload = true) =>
    api
      .post<FileDownloadResponse>(`/files/${id}/download`, {
        file_id: id,
        force_download: forceDownload,
      })
      .then((r) => r.data),
};
