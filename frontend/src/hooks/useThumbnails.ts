import { useQueries } from "@tanstack/react-query";
import { nodesApi } from "@/api/nodes";
import type { NodeListItem } from "@/types/nodes";

/**
 * Prefetches presigned download URLs for all image items in parallel.
 * Returns a Map where:
 *   - key absent  → still loading  → show skeleton
 *   - value null  → fetch failed   → show icon fallback
 *   - value string → presigned URL → show <img>
 */
export function useThumbnails(items: NodeListItem[]): Map<string, string | null> {
  const imageItems = items.filter(
    (i) => i.node_type === "file" && i.file_mime_type?.startsWith("image/"),
  );

  const results = useQueries({
    queries: imageItems.map((item) => ({
      queryKey: ["thumbnail", item.id],
      queryFn: () => nodesApi.download(item.id).then((r) => r.presigned_url),
      staleTime: 4 * 60 * 1000,  // presigned URLs typically expire in 15 min+
      gcTime: 10 * 60 * 1000,
      retry: 1,
    })),
  });

  const map = new Map<string, string | null>();
  imageItems.forEach((item, i) => {
    const r = results[i];
    if (!r.isPending) {
      map.set(item.id, r.data ?? null);
    }
    // pending → key absent → caller shows skeleton
  });
  return map;
}
