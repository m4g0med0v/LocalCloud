import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Link2, Users } from "lucide-react";
import { FileIcon } from "./FileIcon";
import { ItemActions } from "./ItemActions";
import { ItemContextMenu } from "./ItemContextMenu";
import { FilePreviewModal, detectPreviewKind } from "@/components/preview/FilePreviewModal";
import { getFolderColor, setFolderColor } from "./FolderColorDialog";
import { formatBytes } from "@/hooks/useQuota";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { NodeListItem } from "@/types/nodes";
import type { SelectOpts } from "./FileGrid";
import type { ShareBadge } from "@/hooks/useShareBadges";
import { cn } from "@/lib/utils";
import { queryClient } from "@/lib/query-client";
import { nodesApi } from "@/api/nodes";

function prefetchFolder(id: string) {
  queryClient.prefetchQuery({
    queryKey: ["nodes", id, "content"],
    queryFn: () =>
      nodesApi.content(id).then((c) => ({
        items: c.items,
        total: c.total,
        folder: c.folder,
        breadcrumbs: c.breadcrumbs,
      })),
    staleTime: 30_000,
  });
}

interface Props {
  item: NodeListItem;
  mimeType?: string | null;
  sizeBytes?: number | null;
  folderQueryKey: unknown[];
  isSelected?: boolean;
  selectedItems?: NodeListItem[];
  /** undefined = still loading | null = failed | string = presigned URL */
  thumbnailUrl?: string | null;
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

export function FileGridItem({
  item,
  mimeType,
  sizeBytes,
  folderQueryKey,
  isSelected,
  selectedItems,
  thumbnailUrl,
  badge,
  onSelect,
  onDrop,
}: Props) {
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [folderColor, setFolderColorState] = useState<string | null>(
    () => (item.node_type === "folder" ? getFolderColor(item.id) : null),
  );

  const isImage = item.node_type === "file" && !!mimeType?.startsWith("image/");
  const canPreview = item.node_type === "file" && !!detectPreviewKind(item.name, mimeType ?? item.file_mime_type);

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
    } else if (canPreview) {
      setPreviewOpen(true);
    }
  }

  return (
    <>
    <ItemContextMenu
      item={item}
      folderQueryKey={folderQueryKey}
      folderColor={folderColor}
      onColorChange={handleColorChange}
      isSelected={isSelected ?? false}
      selectedItems={selectedItems}
      onSelect={onSelect}
      onPreview={canPreview ? () => setPreviewOpen(true) : undefined}
    >
      <div
        className={cn(
          "group relative flex flex-col rounded-xl overflow-hidden text-center",
          "cursor-pointer select-none transition-all duration-150 hover:shadow-md",
          "border border-border",
          isSelected ? "bg-primary/10 ring-2 ring-primary/50" : "bg-card hover:bg-accent",
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
        onMouseEnter={() => {
          if (item.node_type === "folder") prefetchFolder(item.id);
        }}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") onSelect?.(item, { ctrl: false, shift: false });
        }}
      >
        {/* Preview / icon area */}
        <div className="relative flex h-24 w-full items-center justify-center bg-muted/30">
          {isImage ? (
            thumbnailUrl === undefined ? (
              <Skeleton className="h-full w-full rounded-none" />
            ) : thumbnailUrl ? (
              <img
                src={thumbnailUrl}
                alt={item.name}
                className="h-full w-full object-cover"
                draggable={false}
              />
            ) : (
              <FileIcon nodeType={item.node_type} mimeType={mimeType} className="h-10 w-10" color={folderColor} />
            )
          ) : (
            <FileIcon nodeType={item.node_type} mimeType={mimeType} className="h-10 w-10" color={folderColor} />
          )}

          {/* Share badges */}
          {(badge?.hasPublicLink || badge?.hasSharedAccess) && (
            <div className="absolute bottom-1 left-1 flex items-center gap-0.5">
              {badge.hasPublicLink && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-sky-500 shadow-sm">
                      <Link2 className="h-2.5 w-2.5 text-white" />
                    </span>
                  </TooltipTrigger>
                  <TooltipContent side="right">Публичная ссылка</TooltipContent>
                </Tooltip>
              )}
              {badge.hasSharedAccess && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-violet-500 shadow-sm">
                      <Users className="h-2.5 w-2.5 text-white" />
                    </span>
                  </TooltipTrigger>
                  <TooltipContent side="right">Доступ выдан</TooltipContent>
                </Tooltip>
              )}
            </div>
          )}
        </div>

        {/* Name + meta */}
        <div className="flex flex-col gap-0.5 px-2 py-2">
          <span className="line-clamp-2 break-words text-xs font-medium leading-tight" title={item.name}>
            {item.name}
          </span>
          <span className="text-[10px] text-muted-foreground">
            {item.node_type === "file" && sizeBytes != null
              ? formatBytes(sizeBytes)
              : formatDate(item.updated_at)}
          </span>
        </div>

        {/* Actions button */}
        <div
          className={cn(
            "absolute right-1 top-1 transition-opacity",
            menuOpen ? "opacity-100" : "opacity-0 group-hover:opacity-100",
          )}
          onClick={(e) => e.stopPropagation()}
        >
          <ItemActions
            item={item}
            folderQueryKey={folderQueryKey}
            folderColor={folderColor}
            onColorChange={handleColorChange}
            onOpenChange={setMenuOpen}
            onPreview={canPreview ? () => setPreviewOpen(true) : undefined}
          />
        </div>
      </div>
    </ItemContextMenu>

    {canPreview && (
      <FilePreviewModal
        item={item}
        mimeType={mimeType}
        open={previewOpen}
        onClose={() => setPreviewOpen(false)}
      />
    )}
    </>
  );
}
