import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { nodesApi } from "@/api/nodes";
import type { NodeListItem } from "@/types/nodes";
import type { FolderRead } from "@/types/folders";

export interface FileBrowserData {
  items: NodeListItem[];
  total: number;
  folder: FolderRead | null;
  breadcrumbs: NodeListItem[];
}

export function useFileBrowser(nodeId?: string) {
  const rootQuery = useQuery({
    queryKey: ["nodes", "root"],
    queryFn: async (): Promise<FileBrowserData> => {
      const page = await nodesApi.list();
      return { items: page.items, total: page.meta.total, folder: null, breadcrumbs: [] };
    },
    enabled: !nodeId,
    placeholderData: keepPreviousData,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });

  const folderQuery = useQuery({
    queryKey: ["nodes", nodeId, "content"],
    queryFn: async (): Promise<FileBrowserData> => {
      const content = await nodesApi.content(nodeId!);
      return {
        items: content.items,
        total: content.total,
        folder: content.folder,
        breadcrumbs: content.breadcrumbs,
      };
    },
    enabled: !!nodeId,
    placeholderData: keepPreviousData,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });

  return nodeId ? folderQuery : rootQuery;
}
