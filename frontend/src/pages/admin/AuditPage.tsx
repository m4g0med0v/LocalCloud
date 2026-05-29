import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { auditApi } from "@/api/audit";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import type { AuditLog } from "@/types/audit";
import { cn } from "@/lib/utils";

const RESULT_COLORS: Record<string, string> = {
  success: "bg-green-50 text-green-700 ring-1 ring-inset ring-green-600/20 dark:bg-green-900/30 dark:text-green-400 dark:ring-green-500/20",
  failure: "bg-red-50 text-red-700 ring-1 ring-inset ring-red-600/20 dark:bg-red-900/30 dark:text-red-400 dark:ring-red-500/20",
  denied: "bg-orange-50 text-orange-700 ring-1 ring-inset ring-orange-600/20 dark:bg-orange-900/30 dark:text-orange-400 dark:ring-orange-500/20",
  warning: "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-600/20 dark:bg-amber-900/30 dark:text-amber-400 dark:ring-amber-500/20",
};

const RESULT_LABELS: Record<string, string> = {
  success: "Успех",
  failure: "Ошибка",
  denied: "Отказ",
  warning: "Предупреждение",
};

function AuditRow({ log }: { log: AuditLog }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <tr
        className="border-b last:border-0 hover:bg-muted/40 cursor-pointer transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        <td className="px-4 py-2 text-xs text-muted-foreground whitespace-nowrap">
          {new Date(log.created_at).toLocaleString("ru-RU")}
        </td>
        <td className="px-4 py-2 text-xs font-mono">{log.action}</td>
        <td className="px-4 py-2">
          <span className={cn(
            "inline-flex rounded-full px-2 py-0.5 text-xs font-medium",
            RESULT_COLORS[log.result] ?? "bg-muted text-muted-foreground"
          )}>
            {RESULT_LABELS[log.result] ?? log.result}
          </span>
        </td>
        <td className="px-4 py-2 text-xs text-muted-foreground">{log.resource_type ?? "—"}</td>
        <td className="px-4 py-2 text-xs max-w-xs truncate">{log.message ?? "—"}</td>
        <td className="px-4 py-2 text-xs text-muted-foreground">{log.ip_address ?? "—"}</td>
      </tr>
      {expanded && (
        <tr className="border-b bg-muted/20">
          <td colSpan={6} className="px-4 py-2">
            <div className="text-xs space-y-1 font-mono text-muted-foreground">
              {log.user_id && <p><span className="font-semibold">user_id:</span> {log.user_id}</p>}
              {log.entity_type && <p><span className="font-semibold">entity:</span> {log.entity_type} {log.entity_id}</p>}
              {log.error_code && <p><span className="font-semibold">error_code:</span> {log.error_code}</p>}
              {log.request_id && <p><span className="font-semibold">request_id:</span> {log.request_id}</p>}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

const RESULT_OPTIONS = [
  { value: "", label: "Все" },
  { value: "success", label: "Успех" },
  { value: "failure", label: "Ошибка" },
  { value: "denied", label: "Отказ" },
];

export function AuditPage() {
  const [result, setResult] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const LIMIT = 25;

  const { data, isLoading } = useQuery({
    queryKey: ["admin-audit", result, query, page],
    queryFn: () =>
      auditApi.list({
        result: result || undefined,
        query: query || undefined,
        limit: LIMIT,
        offset: page * LIMIT,
      } as Parameters<typeof auditApi.list>[0]),
  });

  const logs = data?.items ?? [];
  const total = data?.total ?? 0;
  const pageCount = Math.ceil(total / LIMIT);

  return (
    <div className="flex flex-col gap-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <Input
          placeholder="Поиск по сообщению…"
          value={query}
          onChange={(e) => { setQuery(e.target.value); setPage(0); }}
          className="h-8 text-sm w-64"
        />
        <div className="flex gap-1">
          {RESULT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => { setResult(opt.value); setPage(0); }}
              className={cn(
                "rounded-full border px-3 py-1 text-xs transition-colors",
                result === opt.value
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border hover:bg-muted",
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="rounded-lg border overflow-auto">
        <table className="w-full text-left min-w-[700px]">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground whitespace-nowrap">Время</th>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Действие</th>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Результат</th>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Ресурс</th>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Сообщение</th>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground">IP</th>
            </tr>
          </thead>
          <tbody>
            {isLoading
              ? Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i} className="border-b last:border-0">
                    {Array.from({ length: 6 }).map((__, j) => (
                      <td key={j} className="px-4 py-2">
                        <Skeleton className="h-4 rounded" />
                      </td>
                    ))}
                  </tr>
                ))
              : logs.length === 0
              ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-sm text-muted-foreground">
                    Записей нет.
                  </td>
                </tr>
              )
              : logs.map((log) => <AuditRow key={log.id} log={log} />)}
          </tbody>
        </table>
      </div>

      {pageCount > 1 && (
        <div className="flex items-center gap-2 text-sm">
          <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(p => p - 1)}>
            ← Назад
          </Button>
          <span className="text-muted-foreground">Стр. {page + 1} / {pageCount} · {total} записей</span>
          <Button variant="outline" size="sm" disabled={page >= pageCount - 1} onClick={() => setPage(p => p + 1)}>
            Вперёд →
          </Button>
        </div>
      )}
    </div>
  );
}
