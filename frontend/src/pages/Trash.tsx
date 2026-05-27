import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2, RotateCcw, X } from "lucide-react";
import { toast } from "sonner";
import { trashApi } from "@/api/trash";
import { useBreadcrumb } from "@/contexts/breadcrumb";
import { FileIcon } from "@/components/files/FileIcon";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { TrashItemListItem } from "@/types/trash";

const QUERY_KEY = ["trash"];

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

// ── Single row ────────────────────────────────────────────────────────────────

interface RowProps {
  item: TrashItemListItem;
  selected: boolean;
  onToggle: (id: string) => void;
}

function TrashRow({ item, selected, onToggle }: RowProps) {
  const queryClient = useQueryClient();
  const [purgeOpen, setPurgeOpen] = useState(false);

  const restore = useMutation({
    mutationFn: () => trashApi.restore(item.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: ["nodes"] });
      toast.success("Восстановлено");
    },
    onError: () => toast.error("Не удалось восстановить"),
  });

  const purge = useMutation({
    mutationFn: () => trashApi.purge(item.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: ["quota", "me"] });
      toast.success("Удалено навсегда");
      setPurgeOpen(false);
    },
    onError: () => toast.error("Не удалось удалить"),
  });

  const node = item.node;

  return (
    <>
      <div className="flex items-center gap-3 rounded-lg border px-4 py-3 hover:bg-muted/40">
        <Checkbox
          checked={selected}
          onCheckedChange={() => onToggle(item.id)}
          aria-label={`Выбрать ${node?.name ?? item.original_path}`}
        />

        <FileIcon
          nodeType={node?.node_type ?? "file"}
          className="h-5 w-5 shrink-0"
        />

        <div className="flex min-w-0 flex-1 flex-col">
          <span className="truncate text-sm font-medium">
            {node?.name ?? item.original_path.split("/").pop() ?? "—"}
          </span>
          <span className="truncate text-xs text-muted-foreground">
            {item.original_path}
          </span>
        </div>

        <span className="shrink-0 text-xs text-muted-foreground">
          {formatDate(item.deleted_at)}
        </span>

        <div className="flex shrink-0 items-center gap-1">
          {item.restore_available && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              disabled={restore.isPending}
              onClick={() => restore.mutate()}
              title="Восстановить"
            >
              <RotateCcw className="h-4 w-4" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-destructive hover:text-destructive"
            onClick={() => setPurgeOpen(true)}
            title="Удалить навсегда"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <Dialog open={purgeOpen} onOpenChange={setPurgeOpen}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Удалить навсегда?</DialogTitle>
            <DialogDescription>
              «{node?.name ?? item.original_path}» будет удалён без возможности восстановления.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPurgeOpen(false)}>
              Отмена
            </Button>
            <Button
              variant="destructive"
              disabled={purge.isPending}
              onClick={() => purge.mutate()}
            >
              {purge.isPending ? "Удаление…" : "Удалить навсегда"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function TrashPage() {
  const { setCrumbs } = useBreadcrumb();
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [emptyOpen, setEmptyOpen] = useState(false);

  useEffect(() => {
    setCrumbs([{ label: "Корзина" }]);
  }, [setCrumbs]);

  const { data, isLoading } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: () => trashApi.list({ limit: 100 }),
    staleTime: 30_000,
  });

  const items = data?.items ?? [];

  // ── Bulk restore ──
  const bulkRestore = useMutation({
    mutationFn: async () => {
      for (const id of selected) {
        await trashApi.restore(id);
      }
    },
    onSuccess: () => {
      toast.success("Файлы восстановлены");
      setSelected(new Set());
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: ["nodes"] });
    },
    onError: () => toast.error("Не удалось восстановить файлы"),
  });

  // ── Bulk purge ──
  const bulkPurge = useMutation({
    mutationFn: async () => {
      for (const id of selected) {
        await trashApi.purge(id);
      }
    },
    onSuccess: () => {
      toast.success("Файлы удалены навсегда");
      setSelected(new Set());
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: ["quota", "me"] });
    },
    onError: () => toast.error("Не удалось удалить файлы"),
  });

  // ── Empty trash ──
  const emptyTrash = useMutation({
    mutationFn: () => trashApi.empty(),
    onSuccess: () => {
      toast.success("Корзина очищена");
      setSelected(new Set());
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: ["quota", "me"] });
      setEmptyOpen(false);
    },
    onError: () => toast.error("Не удалось очистить корзину"),
  });

  function toggleItem(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function toggleAll() {
    if (selected.size === items.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(items.map((i) => i.id)));
    }
  }

  const allSelected = items.length > 0 && selected.size === items.length;
  const someSelected = selected.size > 0;
  const restorable = items
    .filter((i) => selected.has(i.id) && i.restore_available)
    .length;

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Корзина</h1>
        {items.length > 0 && (
          <Button
            size="sm"
            variant="outline"
            className="text-destructive hover:text-destructive"
            onClick={() => setEmptyOpen(true)}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Очистить корзину
          </Button>
        )}
      </div>

      {/* Bulk action bar */}
      {someSelected && (
        <div className="flex items-center gap-2 rounded-lg border bg-muted/50 px-4 py-2">
          <span className="flex-1 text-sm text-muted-foreground">
            Выбрано: {selected.size}
          </span>
          {restorable > 0 && (
            <Button
              size="sm"
              variant="outline"
              disabled={bulkRestore.isPending}
              onClick={() => bulkRestore.mutate()}
            >
              <RotateCcw className="mr-2 h-3.5 w-3.5" />
              Восстановить ({restorable})
            </Button>
          )}
          <Button
            size="sm"
            variant="outline"
            className="text-destructive hover:text-destructive"
            disabled={bulkPurge.isPending}
            onClick={() => bulkPurge.mutate()}
          >
            <X className="mr-2 h-3.5 w-3.5" />
            Удалить навсегда ({selected.size})
          </Button>
        </div>
      )}

      {/* List */}
      {isLoading ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-14 rounded-lg" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 py-20 text-muted-foreground">
          <Trash2 className="h-12 w-12 opacity-30" />
          <p className="text-sm">Корзина пуста</p>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {/* Select-all header */}
          <div className="flex items-center gap-3 px-4 py-1">
            <Checkbox
              checked={allSelected}
              onCheckedChange={toggleAll}
              aria-label="Выбрать все"
            />
            <span className="text-xs text-muted-foreground">
              {items.length} элем.
            </span>
          </div>

          {items.map((item) => (
            <TrashRow
              key={item.id}
              item={item}
              selected={selected.has(item.id)}
              onToggle={toggleItem}
            />
          ))}
        </div>
      )}

      {/* Empty-all confirm */}
      <Dialog open={emptyOpen} onOpenChange={setEmptyOpen}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Очистить корзину?</DialogTitle>
            <DialogDescription>
              Все {items.length} элем. будут удалены навсегда без возможности восстановления.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEmptyOpen(false)}>
              Отмена
            </Button>
            <Button
              variant="destructive"
              disabled={emptyTrash.isPending}
              onClick={() => emptyTrash.mutate()}
            >
              {emptyTrash.isPending ? "Очистка…" : "Очистить всё"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
