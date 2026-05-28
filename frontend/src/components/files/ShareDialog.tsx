import { useEffect, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Copy, Check, Link2, UserPlus, X, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { publicLinksApi } from "@/api/public-links";
import { permissionsApi } from "@/api/permissions";
import { usersApi } from "@/api/users";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { NodeType } from "@/types/nodes";
import type { PublicLinkPermissionType } from "@/types/public-links";
import type { PermissionLevel } from "@/types/permissions";
import type { UserListItem } from "@/types/users";
import { cn } from "@/lib/utils";

// ── helpers ──────────────────────────────────────────────────────────────────

function useDebounce(value: string, ms: number) {
  const [d, setD] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setD(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return d;
}

function shareUrl(token: string) {
  return `${window.location.origin}/share/${token}`;
}

const PERM_LABELS: Record<PublicLinkPermissionType, string> = {
  view: "Просмотр",
  download: "Скачивание",
  upload: "Загрузка",
};

const PERM_FLAGS = [
  { key: "read",     label: "Чтение" },
  { key: "download", label: "Скачивание" },
  { key: "write",    label: "Редактирование" },
  { key: "delete",   label: "Удаление" },
] as const;

type PermKey = (typeof PERM_FLAGS)[number]["key"];

function permSummary(p: { can_read: boolean; can_download: boolean; can_write: boolean; can_delete: boolean }): string {
  const parts: string[] = [];
  if (p.can_read)     parts.push("чтение");
  if (p.can_download) parts.push("скачивание");
  if (p.can_write)    parts.push("редактирование");
  if (p.can_delete)   parts.push("удаление");
  return parts.join(" · ");
}

// ── Tab: Public link ──────────────────────────────────────────────────────────

function PublicLinkTab({ nodeId, nodeType }: { nodeId: string; nodeType: NodeType }) {
  const qc = useQueryClient();
  const [copied, setCopied] = useState(false);
  const [permType, setPermType] = useState<PublicLinkPermissionType>("download");

  const QUERY_KEY = ["public-links", "node", nodeId];

  const { data, isLoading } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: () => publicLinksApi.listForNode(nodeId),
  });

  const links = data?.items ?? [];
  const activeLink = links.find((l) => l.is_active) ?? null;

  const create = useMutation({
    mutationFn: () =>
      publicLinksApi.create({ node_id: nodeId, permission_type: permType }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEY });
      toast.success("Ссылка создана");
    },
    onError: () => toast.error("Не удалось создать ссылку"),
  });

  const revoke = useMutation({
    mutationFn: (id: string) => publicLinksApi.revoke(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEY });
      toast.success("Ссылка отозвана");
    },
    onError: () => toast.error("Не удалось отозвать ссылку"),
  });

  function handleCopy(token: string) {
    navigator.clipboard.writeText(shareUrl(token)).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (isLoading) {
    return (
      <div className="flex flex-col gap-3 pt-2">
        <Skeleton className="h-9 rounded-md" />
        <Skeleton className="h-9 rounded-md" />
      </div>
    );
  }

  if (activeLink) {
    const url = shareUrl(activeLink.token);
    return (
      <div className="flex flex-col gap-3 pt-2">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800 dark:bg-green-900/30 dark:text-green-400">
            {PERM_LABELS[activeLink.permission_type]}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Input readOnly value={url} className="h-8 text-xs" />
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8 shrink-0"
            onClick={() => handleCopy(activeLink.token)}
            title="Копировать ссылку"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-green-600" /> : <Copy className="h-3.5 w-3.5" />}
          </Button>
        </div>

        <Button
          variant="outline"
          size="sm"
          className="self-start text-destructive hover:text-destructive"
          disabled={revoke.isPending}
          onClick={() => revoke.mutate(activeLink.id)}
        >
          <X className="mr-1.5 h-3.5 w-3.5" />
          Отозвать ссылку
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 pt-2">
      <p className="text-sm text-muted-foreground">Публичная ссылка не создана.</p>

      <div className="flex flex-wrap gap-2">
        {(nodeType === "folder" ? ["download"] : ["view", "download"] as PublicLinkPermissionType[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setPermType(t)}
            className={cn(
              "rounded-full border px-3 py-1 text-xs transition-colors",
              permType === t
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border hover:bg-muted",
            )}
          >
            {PERM_LABELS[t]}
          </button>
        ))}
      </div>

      <Button
        size="sm"
        className="self-start"
        disabled={create.isPending}
        onClick={() => create.mutate()}
      >
        {create.isPending ? (
          <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
        ) : (
          <Link2 className="mr-2 h-3.5 w-3.5" />
        )}
        Создать ссылку
      </Button>
    </div>
  );
}

// ── User search combobox ──────────────────────────────────────────────────────

function UserCombobox({
  value,
  onChange,
}: {
  value: UserListItem | null;
  onChange: (u: UserListItem | null) => void;
}) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const dq = useDebounce(q, 300);
  const ref = useRef<HTMLDivElement>(null);

  const { data } = useQuery({
    queryKey: ["users-search", dq],
    queryFn: () => usersApi.list({ search: dq, limit: 8 }),
    enabled: dq.length >= 1,
    staleTime: 10_000,
  });

  const users = data?.items ?? [];

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  if (value) {
    return (
      <div className="flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm">
        <span className="flex-1 truncate">{value.email}</span>
        <button
          type="button"
          onClick={() => { onChange(null); setQ(""); }}
          className="text-muted-foreground hover:text-foreground"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
    );
  }

  return (
    <div className="relative" ref={ref}>
      <Input
        placeholder="Поиск пользователя по email…"
        value={q}
        className="h-8 text-sm"
        onChange={(e) => { setQ(e.target.value); setOpen(true); }}
        onFocus={() => { if (q) setOpen(true); }}
      />
      {open && users.length > 0 && (
        <ul className="absolute left-0 right-0 top-full z-50 mt-1 max-h-48 overflow-auto rounded-md border bg-popover shadow-lg">
          {users.map((u) => (
            <li
              key={u.id}
              className="cursor-pointer px-3 py-2 text-sm hover:bg-accent"
              onMouseDown={(e) => {
                e.preventDefault();
                onChange(u);
                setOpen(false);
              }}
            >
              <span className="font-medium">{u.email}</span>
              <span className="ml-2 text-xs text-muted-foreground">@{u.username}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ── Tab: User permissions ─────────────────────────────────────────────────────

function AccessTab({ nodeId }: { nodeId: string }) {
  const qc = useQueryClient();
  const [selectedUser, setSelectedUser] = useState<UserListItem | null>(null);
  const [selectedPerms, setSelectedPerms] = useState<Set<PermKey>>(new Set(["read"]));

  function togglePerm(key: PermKey) {
    setSelectedPerms((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  const QUERY_KEY = ["permissions", "node", nodeId];

  const { data, isLoading } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: () => permissionsApi.listForNode(nodeId, { active_only: true, limit: 50 }),
  });

  const perms = (data?.items ?? []).filter((p) => p.revoked_at == null);

  const grant = useMutation({
    mutationFn: () =>
      permissionsApi.grant({
        node_id: nodeId,
        user_id: selectedUser!.id,
        can_read:     selectedPerms.has("read"),
        can_download: selectedPerms.has("download"),
        can_write:    selectedPerms.has("write"),
        can_delete:   selectedPerms.has("delete"),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEY });
      qc.invalidateQueries({ queryKey: ["permissions", "node", nodeId, "badge"] });
      toast.success("Доступ выдан");
      setSelectedUser(null);
    },
    onError: () => toast.error("Не удалось выдать доступ"),
  });

  const revoke = useMutation({
    mutationFn: (permId: string) =>
      permissionsApi.revoke({ permission_id: permId }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEY });
      qc.invalidateQueries({ queryKey: ["permissions", "node", nodeId, "badge"] });
      toast.success("Доступ отозван");
    },
    onError: () => toast.error("Не удалось отозвать доступ"),
  });

  return (
    <div className="flex flex-col gap-4 pt-2">
      {/* Grant form */}
      <div className="flex flex-col gap-2 rounded-lg border p-3">
        <p className="text-xs font-medium text-muted-foreground">Выдать доступ</p>
        <UserCombobox value={selectedUser} onChange={setSelectedUser} />
        <div className="flex flex-wrap gap-1.5">
          {PERM_FLAGS.map(({ key, label }) => (
            <button
              key={key}
              type="button"
              onClick={() => togglePerm(key)}
              className={cn(
                "rounded-full border px-2.5 py-0.5 text-xs transition-colors",
                selectedPerms.has(key)
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border hover:bg-muted",
              )}
            >
              {label}
            </button>
          ))}
        </div>
        <Button
          size="sm"
          className="self-start"
          disabled={!selectedUser || selectedPerms.size === 0 || grant.isPending}
          onClick={() => grant.mutate()}
        >
          {grant.isPending ? (
            <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
          ) : (
            <UserPlus className="mr-2 h-3.5 w-3.5" />
          )}
          Выдать
        </Button>
      </div>

      {/* Existing permissions */}
      {isLoading ? (
        <div className="flex flex-col gap-2">
          {[0, 1].map((i) => <Skeleton key={i} className="h-10 rounded-md" />)}
        </div>
      ) : perms.length === 0 ? (
        <p className="text-sm text-muted-foreground">Нет выданных прав.</p>
      ) : (
        <ul className="flex flex-col gap-1.5">
          {perms.map((p) => (
            <li
              key={p.id}
              className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm"
            >
              <span className="min-w-0 flex-1 truncate font-mono text-xs text-muted-foreground">
                {p.user_id.slice(0, 8)}…
              </span>
              <span className="shrink-0 text-xs text-muted-foreground">
                {permSummary(p) || p.permission_level}
              </span>
              <button
                type="button"
                disabled={revoke.isPending}
                onClick={() => revoke.mutate(p.id)}
                className="shrink-0 text-muted-foreground hover:text-destructive disabled:opacity-50"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ── Main dialog ───────────────────────────────────────────────────────────────

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  nodeId: string;
  nodeName: string;
  nodeType: NodeType;
}

export function ShareDialog({ open, onOpenChange, nodeId, nodeName, nodeType }: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader className="pr-6">
          <DialogTitle>Поделиться</DialogTitle>
          <p className="truncate text-sm text-muted-foreground" title={nodeName}>{nodeName}</p>
        </DialogHeader>

        <PublicLinkTab nodeId={nodeId} nodeType={nodeType} />
      </DialogContent>
    </Dialog>
  );
}
