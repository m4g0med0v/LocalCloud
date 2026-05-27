import api from "@/lib/api";
import type { PageResponse } from "@/types/common";
import type { BackgroundTask, BackgroundTaskListItem } from "@/types/tasks";

export const tasksApi = {
  list: (params?: { limit?: number; offset?: number; status?: string; task_type?: string }) =>
    api.get<PageResponse<BackgroundTaskListItem>>("/tasks/", { params }).then((r) => r.data),

  get: (id: string) =>
    api.get<BackgroundTask>(`/tasks/${id}`).then((r) => r.data),

  cancel: (id: string, reason?: string) =>
    api.post<BackgroundTask>(`/tasks/${id}/cancel`, { reason: reason ?? null }).then((r) => r.data),
};
