import type { NodeListItem } from "@/types/nodes";
import { cn } from "@/lib/utils";

export type FileFilter =
  | "all"
  | "folder"
  | "image"
  | "document"
  | "video"
  | "audio"
  | "archive";

const FILTERS: { value: FileFilter; label: string }[] = [
  { value: "all", label: "Все" },
  { value: "folder", label: "Папки" },
  { value: "image", label: "Изображения" },
  { value: "document", label: "Документы" },
  { value: "video", label: "Видео" },
  { value: "audio", label: "Аудио" },
  { value: "archive", label: "Архивы" },
];

interface Props {
  active: FileFilter;
  onChange: (filter: FileFilter) => void;
}

export function FileFilterBar({ active, onChange }: Props) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {FILTERS.map((f) => (
        <button
          key={f.value}
          onClick={() => onChange(f.value)}
          className={cn(
            "rounded-full px-3 py-1 text-xs font-medium transition-colors",
            active === f.value
              ? "bg-primary text-primary-foreground"
              : "bg-muted text-muted-foreground hover:bg-accent hover:text-foreground",
          )}
        >
          {f.label}
        </button>
      ))}
    </div>
  );
}

export function applyFilter(items: NodeListItem[], filter: FileFilter): NodeListItem[] {
  if (filter === "all") return items;
  if (filter === "folder") return items.filter((i) => i.node_type === "folder");
  if (filter === "image")
    return items.filter((i) => i.file_mime_type?.startsWith("image/"));
  if (filter === "document") {
    return items.filter((i) => {
      const m = i.file_mime_type ?? "";
      return (
        m.startsWith("text/") ||
        m === "application/pdf" ||
        m.includes("msword") ||
        m.includes("ms-excel") ||
        m.includes("ms-powerpoint") ||
        m.includes("officedocument")
      );
    });
  }
  if (filter === "video")
    return items.filter((i) => i.file_mime_type?.startsWith("video/"));
  if (filter === "audio")
    return items.filter((i) => i.file_mime_type?.startsWith("audio/"));
  if (filter === "archive") {
    return items.filter((i) => {
      const m = i.file_mime_type ?? "";
      return (
        m.includes("zip") ||
        m.includes("rar") ||
        m.includes("7z") ||
        m.includes("gzip") ||
        m.includes("tar")
      );
    });
  }
  return items;
}
