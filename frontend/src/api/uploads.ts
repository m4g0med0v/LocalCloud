import api from "@/lib/api";
import type {
  UploadSessionCreateRequest,
  UploadSessionRead,
  PresignedPartsResponse,
  UploadPartCompleteRequest,
  UploadCompleteRequest,
  UploadCompleteResponse,
} from "@/types/uploads";

export const uploadsApi = {
  create: (data: UploadSessionCreateRequest) =>
    api.post<UploadSessionRead>("/uploads/", data).then((r) => r.data),

  get: (id: string) =>
    api.get<UploadSessionRead>(`/uploads/${id}`).then((r) => r.data),

  getPresignedParts: (id: string) =>
    api.post<PresignedPartsResponse>(`/uploads/${id}/parts/presigned`).then((r) => r.data),

  completePart: (id: string, partNumber: number, data: UploadPartCompleteRequest) =>
    api
      .post(`/uploads/${id}/parts/${partNumber}/complete`, data)
      .then((r) => r.data),

  complete: (id: string, data: UploadCompleteRequest) =>
    api.post<UploadCompleteResponse>(`/uploads/${id}/complete`, data).then((r) => r.data),

  abort: (id: string) =>
    api.post(`/uploads/${id}/abort`).then((r) => r.data),
};
