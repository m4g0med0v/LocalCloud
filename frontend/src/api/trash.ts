import api from "@/lib/api";
import type { PageResponse } from "@/types/common";
import type {
  TrashItemListItem,
  TrashRestoreRequest,
  TrashRestoreResponse,
  TrashPurgeResponse,
} from "@/types/trash";

export const trashApi = {
  list: (params?: { limit?: number; offset?: number }) =>
    api.get<PageResponse<TrashItemListItem>>("/trash/", { params }).then((r) => r.data),

  restore: (trashItemId: string, data?: Omit<TrashRestoreRequest, "trash_item_id">) =>
    api
      .post<TrashRestoreResponse>(`/trash/${trashItemId}/restore`, {
        trash_item_id: trashItemId,
        ...data,
      })
      .then((r) => r.data),

  purge: (trashItemId: string) =>
    api.post<TrashPurgeResponse>(`/trash/${trashItemId}/purge`, {}).then((r) => r.data),

  empty: () =>
    api.post<TrashPurgeResponse>("/trash/empty", {}).then((r) => r.data),
};
