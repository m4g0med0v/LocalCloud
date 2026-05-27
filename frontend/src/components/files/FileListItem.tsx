import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Link2, Users } from "lucide-react";
import { FileIcon } from "./FileIcon";
import { ItemActions } from "./ItemActions";
import { ItemContextMenu } from "./ItemContextMenu";
import { getFolderColor, setFolderColor } from "./FolderColorDialog";
import { formatBytes } from "@/hooks/useQuota";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { NodeListItem } from "@/types/nodes";
import type { SelectOpts } from "./FileGrid";
import type { ShareBadge } from "@/hooks/useShareBadges";
import { cn } from "@/lib/utils";

interface Props {
  item: NodeListItem;
  mimeType?: string | null;
  sizeBytes?: number | null;
  folderQueryKey: unknown[];
  isSelected?: boolean;
  badge?: ShareBadge;
  onSelect?: (item: NodeListItem, opts: SelectOpts) => void;
  onDrop?: (draggedId: string, targetFolderId: string) => void;
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
  badge,
  onSelect,
  onDrop,
}: Props) {
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [folderColor, setFolderColorState] = useState<string | null>(
    () => (item.node_type === "folder" ? getFolderColor(item.id) : null),
  );

  function handleColorChange(color: string | null) {
    setFolderColor(item.id, color);
    setFolderColorState(color);
  }

  function handleClick(e: React.MouseEvent) {
    e.stopPropagation();
    onSelect?.(item, { ctrl: e.ctrlKey || e.metaKey, shift: e.shiftKey });
  }

  function handleDoubleClick() {
    if (item.node_type === "folder") {
      navigate(`/files/folders/${item.id}`);
    }
  }

  return (
    <ItemContextMenu
      item={item}
      folderQueryKey={folderQueryKey}
      folderColor={folderColor}
      onColorChange={handleColorChange}
      isSelected={isSelected ?? false}
      onSelect={onSelect}
    >
      <div
        className={cn(
          "group flex cursor-pointer select-none items-center gap-3 rounded-lg px-3 py-2",
          "transition-colors hover:bg-accent",
          isSelected && "bg-primary/10 ring-1 ring-inset ring-primary/40",
          isDragging && "opacity-40",
          isDragOver && "ring-2 ring-primary bg-primary/10",
        )}
        draggable
        onDragStart={(e) => {
          e.dataTransfer.setData("application/localcloud-node", item.id);
          e.dataTransfer.effectAllowed = "move";
          setIsDragging(true);
        }}
        onDragEnd={() => setIsDragging(false)}
        onDragOver={(e) => {
          if (item.node_type !== "folder") return;
          e.preventDefault();
          e.stopPropagation();
          e.dataTransfer.dropEffect = "move";
          if (!isDragOver) setIsDragOver(true);
        }}
        onDragLeave={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget as Node)) setIsDragOver(false);
        }}
        onDrop={(e) => {
          if (item.node_type !== "folder") return;
          e.preventDefault();
          e.stopPropagation();
          setIsDragOver(false);
          const draggedId = e.dataTransfer.getData("application/localcloud-node");
          if (draggedId && draggedId !== item.id) onDrop?.(draggedId, item.id);
        }}
        onClick={handleClick}
        onDoubleClick={handleDoubleClick}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") onSelect?.(item, { ctrl: false, shift: false });
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

        {/* Share badges */}
        {(badge?.hasPublicLink || badge?.hasSharedAccess) && (
          <div className="flex shrink-0 items-center gap-1">
            {badge.hasPublicLink && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="flex h-4 w-4 items-center justify-center rounded-full bg-sky-500">
                    <Link2 className="h-2 w-2 text-white" />
                  </span>
                </TooltipTrigger>
                <TooltipContent>Публичная ссылка</TooltipContent>
              </Tooltip>
            )}
            {badge.hasSharedAccess && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="flex h-4 w-4 items-center justify-center rounded-full bg-violet-500">
                    <Users className="h-2 w-2 text-white" />
                  </span>
                </TooltipTrigger>
                <TooltipContent>Доступ выдан</TooltipContent>
              </Tooltip>
            )}
          </div>
        )}

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
    </ItemContextMenu>
  );
}
