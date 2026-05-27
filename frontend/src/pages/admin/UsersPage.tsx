import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Search, ShieldCheck, ShieldOff, Check, X, Trash2, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { usersApi } from "@/api/users";
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
import type { UserListItem, UserStatus } from "@/types/users";
import { cn } from "@/lib/utils";

const STATUS_LABELS: Record<UserStatus, string> = {
  pending: "Ожидает",
  active: "Активен",
  blocked: "Заблокирован",
  rejected: "Отклонён",
  deleted: "Удалён",
};

const STATUS_COLORS: Record<UserStatus, string> = {
  pending: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  active: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  blocked: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  rejected: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400",
  deleted: "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-500",
};

function formatBytes(bytes: number) {
  if (bytes === 0) return "0 Б";
  const k = 1024;
  const sizes = ["Б", "КБ", "МБ", "ГБ", "ТБ"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

// ── Quota dialog ─────────────────────────────────────────────────────────────

function QuotaDialog({ user, onClose }: { user: UserListItem; onClose: () => void }) {
  const qc = useQueryClient();
  const { data: quota, isLoading } = useQuery({
    queryKey: ["quota", user.id],
    queryFn: () => quotasApi.getByUserId(user.id),
  });

  const [limitGb, setLimitGb] = useState<string>("");

  const update = useMutation({
    mutationFn: () =>
      quotasApi.updateByUserId(user.id, {
        storage_limit_bytes: limitGb ? Math.round(parseFloat(limitGb) * 1024 ** 3) : undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["quota", user.id] });
      toast.success("Квота обновлена");
      setLimitGb("");
    },
    onError: () => toast.error("Не удалось обновить квоту"),
  });

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Квота — {user.email}</DialogTitle>
        </DialogHeader>
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        ) : quota ? (
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Использовано</span>
              <span>{formatBytes(quota.storage_used_bytes)} / {formatBytes(quota.storage_limit_bytes)}</span>
            </div>
            <div className="h-2 rounded-full bg-muted overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full transition-all",
                  quota.usage_percent >= 90 ? "bg-destructive" : "bg-primary",
                )}
                style={{ width: `${Math.min(quota.usage_percent, 100)}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground">{quota.usage_percent.toFixed(1)}% занято</p>

            <div className="flex gap-2 items-center pt-1">
              <Input
                placeholder="Лимит (ГБ)"
                value={limitGb}
                onChange={(e) => setLimitGb(e.target.value)}
                className="h-8 text-sm"
                type="number"
                min="0"
                step="1"
              />
              <Button
                size="sm"
                className="shrink-0"
                disabled={!limitGb || update.isPending}
                onClick={() => update.mutate()}
              >
                {update.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Сохранить"}
              </Button>
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Квота не настроена.</p>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ── Block dialog ─────────────────────────────────────────────────────────────

function BlockDialog({ user, onClose }: { user: UserListItem; onClose: () => void }) {
  const qc = useQueryClient();
  const [reason, setReason] = useState("");

  const block = useMutation({
    mutationFn: () => usersApi.block(user.id, reason || undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      toast.success("Пользователь заблокирован");
      onClose();
    },
    onError: () => toast.error("Не удалось заблокировать"),
  });

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Заблокировать — {user.email}</DialogTitle>
        </DialogHeader>
        <Input
          placeholder="Причина блокировки (необязательно)"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          className="h-8 text-sm"
        />
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={onClose}>Отмена</Button>
          <Button
            size="sm"
            variant="destructive"
            disabled={block.isPending}
            onClick={() => block.mutate()}
          >
            {block.isPending ? <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" /> : null}
            Заблокировать
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── User row ─────────────────────────────────────────────────────────────────

function UserRow({ user }: { user: UserListItem }) {
  const qc = useQueryClient();
  const [quotaOpen, setQuotaOpen] = useState(false);
  const [blockOpen, setBlockOpen] = useState(false);

  const approve = useMutation({
    mutationFn: () => usersApi.approve(user.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      toast.success("Пользователь одобрен");
    },
    onError: () => toast.error("Не удалось одобрить"),
  });

  const unblock = useMutation({
    mutationFn: () => usersApi.unblock(user.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      toast.success("Пользователь разблокирован");
    },
    onError: () => toast.error("Не удалось разблокировать"),
  });

  const deleteUser = useMutation({
    mutationFn: () => usersApi.delete(user.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      toast.success("Пользователь удалён");
    },
    onError: () => toast.error("Не удалось удалить пользователя"),
  });

  return (
    <>
      <tr className="border-b last:border-0 hover:bg-muted/40 transition-colors">
        <td className="px-4 py-2 text-sm font-medium">{user.email}</td>
        <td className="px-4 py-2 text-sm text-muted-foreground">@{user.username}</td>
        <td className="px-4 py-2">
          <span className={cn("inline-flex rounded-full px-2 py-0.5 text-xs font-medium", STATUS_COLORS[user.status])}>
            {STATUS_LABELS[user.status]}
          </span>
        </td>
        <td className="px-4 py-2 text-xs text-muted-foreground">
          {new Date(user.created_at).toLocaleDateString("ru-RU")}
        </td>
        <td className="px-4 py-2">
          <div className="flex items-center gap-1 justify-end">
            <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => setQuotaOpen(true)}>
              Квота
            </Button>
            {user.status === "pending" && (
              <Button
                variant="ghost" size="icon" className="h-7 w-7 text-green-600 hover:text-green-700"
                title="Одобрить"
                disabled={approve.isPending}
                onClick={() => approve.mutate()}
              >
                {approve.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
              </Button>
            )}
            {user.status === "active" && (
              <Button
                variant="ghost" size="icon" className="h-7 w-7 text-orange-600 hover:text-orange-700"
                title="Заблокировать"
                onClick={() => setBlockOpen(true)}
              >
                <ShieldOff className="h-3.5 w-3.5" />
              </Button>
            )}
            {user.status === "blocked" && (
              <Button
                variant="ghost" size="icon" className="h-7 w-7 text-green-600 hover:text-green-700"
                title="Разблокировать"
                disabled={unblock.isPending}
                onClick={() => unblock.mutate()}
              >
                {unblock.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ShieldCheck className="h-3.5 w-3.5" />}
              </Button>
            )}
            {user.status !== "deleted" && (
              <Button
                variant="ghost" size="icon" className="h-7 w-7 text-destructive hover:text-destructive"
                title="Удалить"
                disabled={deleteUser.isPending}
                onClick={() => {
                  if (confirm(`Удалить пользователя ${user.email}?`)) deleteUser.mutate();
                }}
              >
                {deleteUser.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
              </Button>
            )}
          </div>
        </td>
      </tr>
      {quotaOpen && <QuotaDialog user={user} onClose={() => setQuotaOpen(false)} />}
      {blockOpen && <BlockDialog user={user} onClose={() => setBlockOpen(false)} />}
    </>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "Все" },
  { value: "pending", label: "Ожидающие" },
  { value: "active", label: "Активные" },
  { value: "blocked", label: "Заблокированные" },
  { value: "rejected", label: "Отклонённые" },
];

export function UsersPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(0);
  const LIMIT = 20;

  const { data, isLoading } = useQuery({
    queryKey: ["admin-users", search, status, page],
    queryFn: () =>
      usersApi.list({
        search: search || undefined,
        status: status || undefined,
        limit: LIMIT,
        offset: page * LIMIT,
      }),
  });

  const users = data?.items ?? [];
  const total = data?.total ?? 0;
  const pageCount = Math.ceil(total / LIMIT);

  return (
    <div className="flex flex-col gap-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Поиск по email или имени…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(0); }}
            className="h-8 pl-7 text-sm w-64"
          />
        </div>
        <div className="flex gap-1">
          {STATUS_OPTIONS.map((opt) => (
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
      </div>

      {/* Table */}
      <div className="rounded-lg border overflow-auto">
        <table className="w-full text-left min-w-[700px]">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Email</th>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Логин</th>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Статус</th>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Создан</th>
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
              : users.length === 0
              ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-sm text-muted-foreground">
                    Пользователи не найдены.
                  </td>
                </tr>
              )
              : users.map((u) => <UserRow key={u.id} user={u} />)}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
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
