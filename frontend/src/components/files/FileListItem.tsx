import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileIcon } from "./FileIcon";
import { ItemActions } from "./ItemActions";
import { getFolderColor, setFolderColor } from "./FolderColorDialog";
import { formatBytes } from "@/hooks/useQuota";
import type { NodeListItem } from "@/types/nodes";
import { cn } from "@/lib/utils";

interface Props {
  item: NodeListItem;
  mimeType?: string | null;
  sizeBytes?: number | null;
  folderQueryKey: unknown[];
  isSelected?: boolean;
  onSelect?: (item: NodeListItem) => void;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function FileListItem({
  item,
  mimeType,
  sizeBytes,
  folderQueryKey,
  isSelected,
  onSelect,
}: Props) {
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [folderColor, setFolderColorState] = useState<string | null>(
    () => (item.node_type === "folder" ? getFolderColor(item.id) : null),
  );

  function handleColorChange(color: string | null) {
    setFolderColor(item.id, color);
    setFolderColorState(color);
  }

  function handleClick(e: React.MouseEvent) {
    e.stopPropagation();
    onSelect?.(item);
  }

  function handleDoubleClick() {
    if (item.node_type === "folder") {
      navigate(`/files/folders/${item.id}`);
    }
  }

  return (
    <div
      className={cn(
        "group flex cursor-pointer select-none items-center gap-3 rounded-lg px-3 py-2",
        "transition-colors hover:bg-accent",
        isSelected && "bg-primary/10 ring-1 ring-inset ring-primary/40",
      )}
      onClick={handleClick}
      onDoubleClick={handleDoubleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") onSelect?.(item);
      }}
    >
      <FileIcon
        nodeType={item.node_type}
        mimeType={mimeType}
        className="h-4 w-4 shrink-0"
        color={folderColor}
      />

      <span className="min-w-0 flex-1 truncate text-sm font-medium" title={item.name}>
        {item.name}
      </span>

      <span className="shrink-0 text-xs text-muted-foreground">
        {item.node_type === "file" && sizeBytes != null ? formatBytes(sizeBytes) : ""}
      </span>

      <span className="w-24 shrink-0 text-right text-xs text-muted-foreground">
        {formatDate(item.updated_at)}
      </span>

      <div
        onClick={(e) => e.stopPropagation()}
        className={cn(!menuOpen && "opacity-0 group-hover:opacity-100")}
      >
        <ItemActions
          item={item}
          folderQueryKey={folderQueryKey}
          folderColor={folderColor}
          onColorChange={handleColorChange}
          onOpenChange={setMenuOpen}
        />
      </div>
    </div>
  );
}
