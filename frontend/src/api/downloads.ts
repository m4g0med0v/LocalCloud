import api from "@/lib/api";
import type { FileDownloadResponse } from "@/types/files";

export const downloadsApi = {
  archiveUrl: (taskId: string, filename?: string) =>
    api
      .post<FileDownloadResponse>(`/downloads/archive/${taskId}`, null, {
        params: { force_download: true, ...(filename ? { filename } : {}) },
      })
      .then((r) => r.data),
};
