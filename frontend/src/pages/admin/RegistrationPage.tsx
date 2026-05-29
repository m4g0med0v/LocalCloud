import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, X, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { registrationApi } from "@/api/registration";
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
import type { RegistrationRead, RegistrationStatus } from "@/types/registration";
import { cn } from "@/lib/utils";

const STATUS_LABELS: Record<RegistrationStatus, string> = {
  pending: "Ожидает",
  approved: "Одобрена",
  rejected: "Отклонена",
  cancelled: "Отменена",
};

const STATUS_COLORS: Record<RegistrationStatus, string> = {
  pending: "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-600/20 dark:bg-amber-900/30 dark:text-amber-400 dark:ring-amber-500/20",
  approved: "bg-green-50 text-green-700 ring-1 ring-inset ring-green-600/20 dark:bg-green-900/30 dark:text-green-400 dark:ring-green-500/20",
  rejected: "bg-red-50 text-red-700 ring-1 ring-inset ring-red-600/20 dark:bg-red-900/30 dark:text-red-400 dark:ring-red-500/20",
  cancelled: "bg-zinc-100 text-zinc-600 ring-1 ring-inset ring-zinc-500/20 dark:bg-zinc-800 dark:text-zinc-400 dark:ring-zinc-500/20",
};

// ── Reject dialog ─────────────────────────────────────────────────────────────

function RejectDialog({ req, onClose }: { req: RegistrationRead; onClose: () => void }) {
  const qc = useQueryClient();
  const [reason, setReason] = useState("");

  const reject = useMutation({
    mutationFn: () => registrationApi.reject(req.id, { rejection_reason: reason }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-registration"] });
      toast.success("Заявка отклонена");
      onClose();
    },
    onError: () => toast.error("Не удалось отклонить заявку"),
  });

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Отклонить заявку — {req.email}</DialogTitle>
        </DialogHeader>
        <Input
          placeholder="Причина отклонения*"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          className="h-8 text-sm"
        />
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={onClose}>Отмена</Button>
          <Button
            size="sm"
            variant="destructive"
            disabled={!reason.trim() || reject.isPending}
            onClick={() => reject.mutate()}
          >
            {reject.isPending ? <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" /> : null}
            Отклонить
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── Row ───────────────────────────────────────────────────────────────────────

function RegRow({ req }: { req: RegistrationRead }) {
  const qc = useQueryClient();
  const [rejectOpen, setRejectOpen] = useState(false);

  const approve = useMutation({
    mutationFn: () => registrationApi.approve(req.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-registration"] });
      toast.success("Заявка одобрена");
    },
    onError: () => toast.error("Не удалось одобрить заявку"),
  });

  return (
    <>
      <tr className="border-b last:border-0 hover:bg-muted/40 transition-colors">
        <td className="px-4 py-2 text-sm font-medium">{req.email}</td>
        <td className="px-4 py-2 text-sm text-muted-foreground">@{req.username}</td>
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
                variant="ghost" size="icon" className="h-7 w-7 text-green-600 hover:text-green-700"
                title="Одобрить"
                disabled={approve.isPending}
                onClick={() => approve.mutate()}
              >
                {approve.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
              </Button>
              <Button
                variant="ghost" size="icon" className="h-7 w-7 text-destructive hover:text-destructive"
                title="Отклонить"
                onClick={() => setRejectOpen(true)}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
          )}
        </td>
      </tr>
      {rejectOpen && <RejectDialog req={req} onClose={() => setRejectOpen(false)} />}
    </>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

const STATUS_FILTER_OPTIONS = [
  { value: "", label: "Все" },
  { value: "pending", label: "Ожидающие" },
  { value: "approved", label: "Одобренные" },
  { value: "rejected", label: "Отклонённые" },
];

export function RegistrationPage() {
  const [status, setStatus] = useState("pending");
  const [page, setPage] = useState(0);
  const LIMIT = 20;

  const { data, isLoading } = useQuery({
    queryKey: ["admin-registration", status, page],
    queryFn: () =>
      registrationApi.list({
        status: status || undefined,
        limit: LIMIT,
        offset: page * LIMIT,
      }),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pageCount = Math.ceil(total / LIMIT);

  return (
    <div className="flex flex-col gap-4">
      {/* Filters */}
      <div className="flex gap-1">
        {STATUS_FILTER_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => { setStatus(opt.value); setPage(0); }}
            className={cn(
              "rounded-full border px-3 py-1 text-xs transition-colors",
              status === opt.value
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
        <table className="w-full text-left min-w-[600px]">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Email</th>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Логин</th>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Статус</th>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Создана</th>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground text-right">Действия</th>
            </tr>
          </thead>
          <tbody>
            {isLoading
              ? Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b last:border-0">
                    {Array.from({ length: 5 }).map((__, j) => (
                      <td key={j} className="px-4 py-2">
                        <Skeleton className="h-4 rounded" />
                      </td>
                    ))}
                  </tr>
                ))
              : items.length === 0
              ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-sm text-muted-foreground">
                    Заявок нет.
                  </td>
                </tr>
              )
              : items.map((r) => <RegRow key={r.id} req={r as RegistrationRead} />)}
          </tbody>
        </table>
      </div>

      {pageCount > 1 && (
        <div className="flex items-center gap-2 text-sm">
          <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(p => p - 1)}>
            ← Назад
          </Button>
          <span className="text-muted-foreground">Стр. {page + 1} / {pageCount}</span>
          <Button variant="outline" size="sm" disabled={page >= pageCount - 1} onClick={() => setPage(p => p + 1)}>
            Вперёд →
          </Button>
        </div>
      )}
    </div>
  );
}
