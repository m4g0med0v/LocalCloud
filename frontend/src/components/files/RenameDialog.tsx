import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { nodesApi } from "@/api/nodes";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  nodeId: string;
  currentName: string;
  folderQueryKey: unknown[];
}

export function RenameDialog({ open, onOpenChange, nodeId, currentName, folderQueryKey }: Props) {
  const [name, setName] = useState(currentName);
  const [error, setError] = useState("");
  const queryClient = useQueryClient();

  useEffect(() => {
    if (open) setName(currentName);
  }, [open, currentName]);

  const mutation = useMutation({
    mutationFn: () => nodesApi.rename(nodeId, name.trim()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: folderQueryKey });
      toast.success("Переименовано");
      setError("");
      onOpenChange(false);
    },
    onError: () => {
      setError("Не удалось переименовать. Попробуйте ещё раз.");
      toast.error("Не удалось переименовать");
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) { setError("Введите название"); return; }
    if (name.trim() === currentName) { onOpenChange(false); return; }
    setError("");
    mutation.mutate();
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Переименовать</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="rename-input">Новое название</Label>
            <Input
              id="rename-input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
              onFocus={(e) => e.target.select()}
            />
            {error && <p className="text-xs text-destructive">{error}</p>}
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Отмена
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Сохранение…" : "Сохранить"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
