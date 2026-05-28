import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, X, Loader2, HardDrive, Server } from "lucide-react";
import { toast } from "sonner";
import { quotasApi } from "@/api/quotas";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { formatBytes } from "@/hooks/useQuota";
import type { QuotaIncreaseRequest, QuotaIncreaseRequestStatus } from "@/types/quotas";
import { cn } from "@/lib/utils";

const STATUS_LABELS: Record<QuotaIncreaseRequestStatus, string> = {
  pending: "Ожидает",
  approved: "Одобрена",
  rejected: "Отклонена",
};

const STATUS_COLORS: Record<QuotaIncreaseRequestStatus, string> = {
  pending: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  approved: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  rejected: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
};

// ── Server storage info ────────────────────────────────────────────────────────

function ServerStorageCard() {
  const { data, isLoading } = useQuery({
    queryKey: ["admin", "server-storage"],
    queryFn: quotasApi.serverStorage,
    staleTime: 30_000,
  });

  if (isLoading) {
    return (
      <div className="flex gap-3 rounded-lg border p-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-32 rounded" />
        ))}
      </div>
    );
  }
  if (!data) return null;

  const usedPct = Math.round((data.used_bytes / data.total_bytes) * 100);
  const allocatedPct = Math.round((data.allocated_quota_bytes / data.total_bytes) * 100);

  return (
    <div className="rounded-lg border p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-medium">
        <Server className="h-4 w-4 text-muted-foreground" />
        Дисковое пространство сервера
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StorageStat label="Всего" value={formatBytes(data.total_bytes)} />
        <StorageStat label="Занято (ОС)" value={formatBytes(data.used_bytes)} sub={`${usedPct}%`} />
        <StorageStat label="Свободно" value={formatBytes(data.free_bytes)} highlight />
        <StorageStat
          label="Выдано квот"
          value={formatBytes(data.allocated_quota_bytes)}
          sub={`${allocatedPct}% от диска`}
          warn={data.allocated_quota_bytes > data.free_bytes}
        />
      </div>
    </div>
  );
}

function StorageStat({
  label,
  value,
  sub,
  highlight,
  warn,
}: {
  label: string;
  value: string;
  sub?: string;
  highlight?: boolean;
  warn?: boolean;
}) {
  return (
    <div className="flex flex-col gap-0.5 rounded-md bg-muted/40 px-3 py-2">
      <span className="text-[11px] text-muted-foreground">{label}</span>
      <span
        className={cn(
          "text-sm font-semibold",
          highlight && "text-green-600 dark:text-green-400",
          warn && "text-red-600 dark:text-red-400",
        )}
      >
        {value}
      </span>
      {sub && <span className="text-[10px] text-muted-foreground">{sub}</span>}
    </div>
  );
}

// ── Reject dialog ─────────────────────────────────────────────────────────────

function RejectDialog({
  req,
  onClose,
}: {
  req: QuotaIncreaseRequest;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [comment, setComment] = useState("");

  const reject = useMutation({
    mutationFn: () => quotasApi.rejectIncreaseRequest(req.id, { admin_comment: comment.trim() || null }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "quota-requests"] });
      toast.success("Запрос отклонён");
      onClose();
    },
    onError: () => toast.error("Не удалось отклонить запрос"),
  });

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Отклонить запрос — @{req.username ?? req.user_id}</DialogTitle>
        </DialogHeader>
        <Input
          placeholder="Комментарий (необязательно)"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          className="h-8 text-sm"
        />
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={onClose}>
            Отмена
          </Button>
          <Button
            size="sm"
            variant="destructive"
            disabled={reject.isPending}
            onClick={() => reject.mutate()}
          >
            {reject.isPending && <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />}
            Отклонить
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── Row ───────────────────────────────────────────────────────────────────────

function RequestRow({ req }: { req: QuotaIncreaseRequest }) {
  const qc = useQueryClient();
  const [rejectOpen, setRejectOpen] = useState(false);

  const approve = useMutation({
    mutationFn: () => quotasApi.approveIncreaseRequest(req.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "quota-requests"] });
      qc.invalidateQueries({ queryKey: ["admin", "server-storage"] });
      toast.success("Запрос одобрен, квота увеличена");
    },
    onError: () => toast.error("Не удалось одобрить запрос"),
  });

  return (
    <>
      <tr className="border-b last:border-0 hover:bg-muted/40 transition-colors">
        <td className="px-4 py-2 text-sm font-medium">
          @{req.username ?? "—"}
          {req.email && (
            <div className="text-xs text-muted-foreground">{req.email}</div>
          )}
        </td>
        <td className="px-4 py-2 text-sm text-muted-foreground">
          <div className="flex items-center gap-1">
            <HardDrive className="h-3 w-3 shrink-0" />
            +{formatBytes(req.requested_bytes)}
          </div>
          <div className="text-xs text-muted-foreground">
            {formatBytes(req.current_limit_bytes)} → {formatBytes(req.current_limit_bytes + req.requested_bytes)}
          </div>
        </td>
        <td className="px-4 py-2 text-sm text-muted-foreground max-w-[200px]">
          <span className="line-clamp-2">{req.reason || "—"}</span>
        </td>
        <td className="px-4 py-2">
          <span className={cn("inline-flex rounded-full px-2 py-0.5 text-xs font-medium", STATUS_COLORS[req.status])}>
            {STATUS_LABELS[req.status]}
          </span>
        </td>
        <td className="px-4 py-2 text-xs text-muted-foreground">
          {new Date(req.created_at).toLocaleDateString("ru-RU")}
        </td>
        <td className="px-4 py-2">
          {req.status === "pending" && (
            <div className="flex items-center gap-1 justify-end">
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-green-600 hover:text-green-700"
                title="Одобрить"
                disabled={approve.isPending}
                onClick={() => approve.mutate()}
              >
                {approve.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Check className="h-3.5 w-3.5" />
                )}
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-destructive hover:text-destructive"
                title="Отклонить"
                onClick={() => setRejectOpen(true)}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
          )}
          {req.status !== "pending" && req.admin_comment && (
            <span className="text-xs text-muted-foreground line-clamp-1" title={req.admin_comment}>
              {req.admin_comment}
            </span>
          )}
        </td>
      </tr>
      {rejectOpen && <RejectDialog req={req} onClose={() => setRejectOpen(false)} />}
    </>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

const STATUS_FILTER_OPTIONS: Array<{ value: QuotaIncreaseRequestStatus | ""; label: string }> = [
  { value: "", label: "Все" },
  { value: "pending", label: "Ожидающие" },
  { value: "approved", label: "Одобренные" },
  { value: "rejected", label: "Отклонённые" },
];

const LIMIT = 50;

export function QuotaRequestsPage() {
  const [statusFilter, setStatusFilter] = useState<QuotaIncreaseRequestStatus | "">( "pending");
  const [page, setPage] = useState(0);

  const { data: items = [], isLoading } = useQuery({
    queryKey: ["admin", "quota-requests", statusFilter, page],
    queryFn: () =>
      quotasApi.listIncreaseRequests({
        status: statusFilter || undefined,
        offset: page * LIMIT,
        limit: LIMIT,
      }),
  });

  return (
    <div className="flex flex-col gap-4">
      <ServerStorageCard />

      {/* Filters */}
      <div className="flex gap-1">
        {STATUS_FILTER_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => {
              setStatusFilter(opt.value as QuotaIncreaseRequestStatus | "");
              setPage(0);
            }}
            className={cn(
              "rounded-full border px-3 py-1 text-xs transition-colors",
              statusFilter === opt.value
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border hover:bg-muted",
            )}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="rounded-lg border overflow-auto">
        <table className="w-full text-left min-w-[700px]">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Пользователь</th>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Запрос</th>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Причина</th>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Статус</th>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Дата</th>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground text-right">Действия</th>
            </tr>
          </thead>
          <tbody>
            {isLoading
              ? Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b last:border-0">
                    {Array.from({ length: 6 }).map((__, j) => (
                      <td key={j} className="px-4 py-2">
                        <Skeleton className="h-4 rounded" />
                      </td>
                    ))}
                  </tr>
                ))
              : items.length === 0
              ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-sm text-muted-foreground">
                    Запросов нет.
                  </td>
                </tr>
              )
              : items.map((r) => <RequestRow key={r.id} req={r} />)}
          </tbody>
        </table>
      </div>

      {items.length === LIMIT && (
        <div className="flex items-center gap-2 text-sm">
          <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
            ← Назад
          </Button>
          <span className="text-muted-foreground">Стр. {page + 1}</span>
          <Button variant="outline" size="sm" onClick={() => setPage((p) => p + 1)}>
            Вперёд →
          </Button>
        </div>
      )}
    </div>
  );
}
