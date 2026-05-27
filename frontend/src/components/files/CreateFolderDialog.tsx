import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { foldersApi } from "@/api/folders";
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
  parentNodeId?: string | null;
  currentNodeId?: string | null;
}

export function CreateFolderDialog({ open, onOpenChange, parentNodeId, currentNodeId }: Props) {
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () =>
      foldersApi.create({ name: name.trim(), parent_id: parentNodeId ?? null }),
    onSuccess: () => {
      const key = currentNodeId
        ? ["nodes", currentNodeId, "content"]
        : ["nodes", "root"];
      queryClient.invalidateQueries({ queryKey: key });
      toast.success("Папка создана");
      setName("");
      setError("");
      onOpenChange(false);
    },
    onError: () => {
      setError("Не удалось создать папку. Попробуйте ещё раз.");
      toast.error("Не удалось создать папку");
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) { setError("Введите название папки"); return; }
    setError("");
    mutation.mutate();
  }

  function handleOpenChange(val: boolean) {
    if (!val) { setName(""); setError(""); }
    onOpenChange(val);
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Новая папка</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="folder-name">Название</Label>
            <Input
              id="folder-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Моя папка"
              autoFocus
            />
            {error && <p className="text-xs text-destructive">{error}</p>}
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
              Отмена
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Создание…" : "Создать"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
