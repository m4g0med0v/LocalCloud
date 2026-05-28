import { Folder as FolderIcon } from "lucide-react";
import { FileGridItem } from "./FileGridItem";
import { FileListItem } from "./FileListItem";
import { Skeleton } from "@/components/ui/skeleton";
import { useThumbnails } from "@/hooks/useThumbnails";
import { useShareBadges } from "@/hooks/useShareBadges";
import type { NodeListItem } from "@/types/nodes";

export type ViewMode = "grid" | "list";

export interface SelectOpts {
  ctrl: boolean;
  shift: boolean;
}

interface Props {
  items: NodeListItem[];
  isLoading: boolean;
  folderQueryKey: unknown[];
  view: ViewMode;
  selectedIds?: Set<string>;
  onSelectItem?: (item: NodeListItem, opts: SelectOpts) => void;
  onDeselect?: () => void;
  onDrop?: (draggedId: string, targetFolderId: string) => void;
}

export function sortItems(items: NodeListItem[]): NodeListItem[] {
  return [...items].sort((a, b) => {
    if (a.node_type !== b.node_type) return a.node_type === "folder" ? -1 : 1;
    return a.name.localeCompare(b.name, "ru");
  });
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-20 text-muted-foreground">
      <FolderIcon className="h-12 w-12 opacity-30" />
      <p className="text-sm">Папка пуста</p>
    </div>
  );
}

function LoadingGrid({ view }: { view: ViewMode }) {
  if (view === "list") {
    return (
      <div className="flex flex-col gap-1">
        {Array.from({ length: 10 }).map((_, i) => (
          <Skeleton key={i} className="h-9 rounded-lg" />
        ))}
      </div>
    );
  }
  return (
    <div
      className="grid gap-3"
      style={{ gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))" }}
    >
      {Array.from({ length: 12 }).map((_, i) => (
        <Skeleton key={i} className="h-[108px] rounded-xl" />
      ))}
    </div>
  );
}

export function FileGrid({
  items,
  isLoading,
  folderQueryKey,
  view,
  selectedIds,
  onSelectItem,
  onDeselect,
  onDrop,
}: Props) {
  // Prefetch all image thumbnails in parallel as soon as items are known.
  const thumbnails = useThumbnails(items);
  const badges = useShareBadges(items);

  if (isLoading) return <LoadingGrid view={view} />;
  if (!items.length) return <EmptyState />;

  const sorted = sortItems(items);
  const selectedItems = selectedIds ? items.filter((i) => selectedIds.has(i.id)) : [];

  if (view === "list") {
    return (
      <div className="flex flex-col" onClick={onDeselect}>
        {/* Header row */}
        <div className="flex items-center gap-3 border-b px-3 pb-1.5 text-xs text-muted-foreground">
          <span className="h-4 w-4 shrink-0" />
          <span className="flex-1">Название</span>
          <span className="shrink-0">Размер</span>
          <span className="w-24 shrink-0 text-right">Изменён</span>
          <span className="h-6 w-6 shrink-0" />
        </div>
        <div className="flex flex-col gap-0.5 px-1 pt-1 pb-1">
          {sorted.map((item) => (
            <FileListItem
              key={item.id}
              item={item}
              folderQueryKey={folderQueryKey}
              mimeType={item.file_mime_type}
              sizeBytes={item.file_size_bytes}
              isSelected={selectedIds?.has(item.id) ?? false}
              selectedItems={selectedItems}
              badge={badges.get(item.id)}
              onSelect={onSelectItem}
              onDrop={onDrop}
            />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div
      className="grid gap-3 p-1"
      style={{ gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))" }}
      onClick={onDeselect}
    >
      {sorted.map((item) => (
        <FileGridItem
          key={item.id}
          item={item}
          folderQueryKey={folderQueryKey}
          mimeType={item.file_mime_type}
          sizeBytes={item.file_size_bytes}
          isSelected={selectedIds?.has(item.id) ?? false}
          selectedItems={selectedItems}
          thumbnailUrl={thumbnails.get(item.id)}
          badge={badges.get(item.id)}
          onSelect={onSelectItem}
          onDrop={onDrop}
        />
      ))}
    </div>
  );
}
