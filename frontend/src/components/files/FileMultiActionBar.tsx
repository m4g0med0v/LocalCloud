import { useState } from "react";
import { Loader2, X, Trash2 } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { nodesApi } from "@/api/nodes";
import { useInfoPanel } from "@/contexts/infoPanel";
import type { NodeListItem } from "@/types/nodes";

interface Props {
  items: NodeListItem[];
  folderQueryKey: unknown[];
  onDeselect: () => void;
}

export function FileMultiActionBar({ items, folderQueryKey, onDeselect }: Props) {
  const queryClient = useQueryClient();
  const { selectedItem: infoPanelItem, closeInfo } = useInfoPanel();
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const count = items.length;

  function pluralCount(n: number) {
    if (n === 1) return "1 элемент";
    if (n < 5) return `${n} элемента`;
    return `${n} элементов`;
  }

  async function handleDeleteAll() {
    setDeleting(true);
    const results = await Promise.allSettled(
      items.map((item) => nodesApi.softDelete(item.id)),
    );
    const deletedIds = new Set(items.map((i) => i.id));
    const failed = results.filter((r) => r.status === "rejected").length;
    setDeleting(false);
    setDeleteOpen(false);
    onDeselect();
    if (infoPanelItem && deletedIds.has(infoPanelItem.id)) closeInfo();
    await queryClient.invalidateQueries({ queryKey: folderQueryKey });
    queryClient.invalidateQueries({ queryKey: ["trash"] });
    if (failed > 0) {
      toast.error(`Не удалось переместить ${failed} из ${count} элементов в корзину`);
    } else {
      toast.success(`${pluralCount(count)} перемещено в корзину`);
    }
  }

  return (
    <>
      <div className="flex items-center gap-2 rounded-lg border bg-muted/40 px-3 py-1.5">
        <Button
          size="icon"
          variant="ghost"
          className="h-7 w-7 shrink-0"
          onClick={onDeselect}
          aria-label="Снять выделение"
        >
          <X className="h-3.5 w-3.5" />
        </Button>

        <span className="flex-1 text-sm font-medium">
          {pluralCount(count)} выбрано
        </span>

        <Button
          size="sm"
          variant="destructive"
          onClick={() => setDeleteOpen(true)}
        >
          <Trash2 className="mr-2 h-3.5 w-3.5" />
          Удалить
        </Button>
      </div>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Удалить {pluralCount(count)}?</DialogTitle>
            <DialogDescription>
              Выбранные элементы будут перемещены в корзину. Вы сможете восстановить их позже.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" disabled={deleting} onClick={() => setDeleteOpen(false)}>
              Отмена
            </Button>
            <Button
              variant="destructive"
              disabled={deleting}
              onClick={handleDeleteAll}
            >
              {deleting ? (
                <>
                  <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                  Удаление…
                </>
              ) : (
                "Удалить"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
