import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { nodesApi } from "@/api/nodes";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  items: Array<{ id: string; name: string }>;
  folderQueryKey: unknown[];
}

export function DeleteConfirmDialog({ open, onOpenChange, items, folderQueryKey }: Props) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => Promise.allSettled(items.map((i) => nodesApi.softDelete(i.id))),
    onSuccess: (results) => {
      const failed = results.filter((r) => r.status === "rejected").length;
      queryClient.invalidateQueries({ queryKey: folderQueryKey });
      queryClient.invalidateQueries({ queryKey: ["trash"] });
      if (failed === 0) {
        toast.success(
          items.length === 1
            ? "Перемещено в корзину"
            : `${items.length} элементов перемещено в корзину`,
        );
      } else {
        toast.error(`Не удалось удалить ${failed} из ${items.length}`);
      }
      onOpenChange(false);
    },
    onError: () => toast.error("Не удалось удалить"),
  });

  const label =
    items.length === 1
      ? `«${items[0]?.name}»`
      : `${items.length} выбранных элемента(ов)`;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Удалить?</DialogTitle>
          <DialogDescription>
            {label} будет перемещено в корзину. Вы сможете восстановить позже.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Отмена
          </Button>
          <Button
            variant="destructive"
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? "Удаление…" : "Удалить"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
