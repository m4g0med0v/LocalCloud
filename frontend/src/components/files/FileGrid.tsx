import { Folder as FolderIcon } from "lucide-react";
import { FileGridItem } from "./FileGridItem";
import { Skeleton } from "@/components/ui/skeleton";
import type { NodeListItem } from "@/types/nodes";

interface Props {
  items: NodeListItem[];
  isLoading: boolean;
  folderQueryKey: unknown[];
}

function sortItems(items: NodeListItem[]): NodeListItem[] {
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

function LoadingGrid() {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
      {Array.from({ length: 12 }).map((_, i) => (
        <Skeleton key={i} className="h-[108px] rounded-xl" />
      ))}
    </div>
  );
}

export function FileGrid({ items, isLoading, folderQueryKey }: Props) {
  if (isLoading) return <LoadingGrid />;
  if (!items.length) return <EmptyState />;

  const sorted = sortItems(items);

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
      {sorted.map((item) => (
        <FileGridItem key={item.id} item={item} folderQueryKey={folderQueryKey} />
      ))}
    </div>
  );
}
