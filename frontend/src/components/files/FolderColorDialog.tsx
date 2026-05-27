import { Folder } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

export const FOLDER_COLORS: { label: string; value: string }[] = [
  { label: "Жёлтый", value: "#eab308" },
  { label: "Оранжевый", value: "#f97316" },
  { label: "Красный", value: "#ef4444" },
  { label: "Розовый", value: "#ec4899" },
  { label: "Фиолетовый", value: "#a855f7" },
  { label: "Синий", value: "#3b82f6" },
  { label: "Голубой", value: "#06b6d4" },
  { label: "Зелёный", value: "#22c55e" },
  { label: "Серый", value: "#6b7280" },
];

const STORAGE_KEY = "folder-colors";

export function getFolderColor(nodeId: string): string | null {
  try {
    const map = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}") as Record<string, string>;
    return map[nodeId] ?? null;
  } catch {
    return null;
  }
}

export function setFolderColor(nodeId: string, color: string | null) {
  try {
    const map = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}") as Record<string, string>;
    if (color === null) {
      delete map[nodeId];
    } else {
      map[nodeId] = color;
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  } catch {
    // ignore
  }
}

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  nodeId: string;
  currentColor: string | null;
  onColorChange: (color: string | null) => void;
}

export function FolderColorDialog({ open, onOpenChange, currentColor, onColorChange }: Props) {
  function handleSelect(color: string) {
    onColorChange(color);
    onOpenChange(false);
  }

  function handleReset() {
    onColorChange(null);
    onOpenChange(false);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xs">
        <DialogHeader>
          <DialogTitle>Цвет папки</DialogTitle>
        </DialogHeader>

        <div className="grid grid-cols-5 gap-2 py-2">
          {FOLDER_COLORS.map((c) => (
            <button
              key={c.value}
              title={c.label}
              onClick={() => handleSelect(c.value)}
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-lg transition-all hover:scale-110",
                currentColor === c.value && "ring-2 ring-ring ring-offset-2 ring-offset-background",
              )}
            >
              <Folder className="h-6 w-6" style={{ color: c.value }} />
            </button>
          ))}
        </div>

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={handleReset}>
            Сбросить
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
