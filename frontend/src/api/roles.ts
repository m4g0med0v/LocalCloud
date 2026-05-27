import api from "@/lib/api";
import type { Role } from "@/types/roles";

export const rolesApi = {
  list: () => api.get<Role[]>("/roles").then((r) => r.data),
};
