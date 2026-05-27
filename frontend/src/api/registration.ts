import api from "@/lib/api";
import type { PageResponse } from "@/types/common";
import type {
  RegistrationCreateRequest,
  RegistrationRead,
  RegistrationApproveRequest,
  RegistrationApproveResponse,
  RegistrationRejectRequest,
} from "@/types/registration";

export const registrationApi = {
  create: (data: RegistrationCreateRequest) =>
    api.post<RegistrationRead>("/registration/requests", data).then((r) => r.data),

  list: (params?: { limit?: number; offset?: number; status?: string }) =>
    api
      .get<PageResponse<RegistrationRead>>("/registration/requests", { params })
      .then((r) => r.data),

  approve: (id: string, data: RegistrationApproveRequest = {}) =>
    api
      .post<RegistrationApproveResponse>(`/registration/requests/${id}/approve`, data)
      .then((r) => r.data),

  reject: (id: string, data: RegistrationRejectRequest = {}) =>
    api.post(`/registration/requests/${id}/reject`, data).then((r) => r.data),
};
