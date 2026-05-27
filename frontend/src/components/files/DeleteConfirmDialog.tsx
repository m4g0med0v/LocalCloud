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
  nodeId: string;
  name: string;
  folderQueryKey: unknown[];
}

export function DeleteConfirmDialog({ open, onOpenChange, nodeId, name, folderQueryKey }: Props) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => nodesApi.softDelete(nodeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: folderQueryKey });
      toast.success("Перемещено в корзину");
      onOpenChange(false);
    },
    onError: () => toast.error("Не удалось удалить"),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Удалить?</DialogTitle>
          <DialogDescription>
            «{name}» будет перемещён в корзину. Вы сможете восстановить его позже.
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
