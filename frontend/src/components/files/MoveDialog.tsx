import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ChevronRight, Folder, Loader2 } from "lucide-react";
import { nodesApi } from "@/api/nodes";
import type { NodeListItem } from "@/types/nodes";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

interface StackEntry {
  id: string | null;
  name: string;
}

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  nodeId: string;
  nodeName: string;
  folderQueryKey: unknown[];
}

export function MoveDialog({ open, onOpenChange, nodeId, nodeName, folderQueryKey }: Props) {
  const queryClient = useQueryClient();
  const [stack, setStack] = useState<StackEntry[]>([{ id: null, name: "Файлы" }]);
  const [moving, setMoving] = useState(false);

  const currentEntry = stack[stack.length - 1];
  const currentFolderId = currentEntry.id;

  useEffect(() => {
    if (open) setStack([{ id: null, name: "Файлы" }]);
  }, [open]);

  const { data, isLoading } = useQuery({
    queryKey: ["move-browser", currentFolderId ?? "root"],
    queryFn: async (): Promise<NodeListItem[]> => {
      if (currentFolderId === null) {
        const page = await nodesApi.list();
        return page.items;
      }
      const content = await nodesApi.content(currentFolderId);
      return content.items;
    },
    enabled: open,
    staleTime: 10_000,
  });

  const folders = (data ?? [])
    .filter((i) => i.node_type === "folder" && i.id !== nodeId)
    .sort((a, b) => a.name.localeCompare(b.name, "ru"));

  function navigateInto(entry: StackEntry) {
    setStack((prev) => [...prev, entry]);
  }

  function goTo(index: number) {
    setStack((prev) => prev.slice(0, index + 1));
  }

  async function handleMove() {
    setMoving(true);
    try {
      await nodesApi.move(nodeId, { target_parent_id: currentFolderId });
      toast.success(`«${nodeName}» перемещено`);
      onOpenChange(false);
      queryClient.invalidateQueries({ queryKey: folderQueryKey });
    } catch {
      toast.error("Не удалось переместить");
    } finally {
      setMoving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Переместить «{nodeName}»</DialogTitle>
        </DialogHeader>

        {/* Breadcrumb path */}
        <div className="flex flex-wrap items-center gap-0.5 text-sm">
          {stack.map((entry, i) => (
            <span key={i} className="flex items-center gap-0.5">
              {i > 0 && <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />}
              <button
                className={cn(
                  "rounded px-1 py-0.5 hover:bg-accent",
                  i === stack.length - 1
                    ? "font-medium pointer-events-none"
                    : "text-muted-foreground",
                )}
                onClick={() => goTo(i)}
              >
                {entry.name}
              </button>
            </span>
          ))}
        </div>

        {/* Folder list */}
        <div className="flex min-h-[180px] max-h-[280px] flex-col overflow-y-auto rounded-lg border">
          {isLoading ? (
            <div className="flex flex-1 items-center justify-center py-10">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : folders.length === 0 ? (
            <div className="flex flex-1 items-center justify-center py-10 text-sm text-muted-foreground">
              Нет папок
            </div>
          ) : (
            <div className="flex flex-col gap-0.5 p-1">
              {folders.map((folder) => (
                <button
                  key={folder.id}
                  className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent"
                  onClick={() => navigateInto({ id: folder.id, name: folder.name })}
                >
                  <Folder className="h-4 w-4 shrink-0 text-yellow-500" />
                  <span className="min-w-0 flex-1 truncate text-left">{folder.name}</span>
                  <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                </button>
              ))}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" disabled={moving} onClick={() => onOpenChange(false)}>
            Отмена
          </Button>
          <Button disabled={moving} onClick={handleMove}>
            {moving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Переместить сюда
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
