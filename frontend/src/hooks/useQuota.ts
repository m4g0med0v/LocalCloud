import { useQuery } from "@tanstack/react-query";
import { quotasApi } from "@/api/quotas";

export function useMyQuota() {
  return useQuery({
    queryKey: ["quota", "me"],
    queryFn: quotasApi.me,
    staleTime: 1000 * 60,
  });
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 Б";
  const units = ["Б", "КБ", "МБ", "ГБ", "ТБ"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}
