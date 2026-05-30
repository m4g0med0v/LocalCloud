import { useQuery, useQueryClient } from "@tanstack/react-query";
import { nodesApi } from "@/api/nodes";
import type { NodeListItem } from "@/types/nodes";

const STALE_MS = 4 * 60 * 1000;
const GC_MS = 10 * 60 * 1000;

/**
 * Fetches presigned thumbnail URLs for all image items in ONE batch request.
 * Individual results are stored in per-item cache entries so they survive
 * folder re-fetches without re-downloading from the server.
 *
 * Returns a Map where:
 *   - key absent  → still loading  → show skeleton
 *   - value null  → failed/not image → show icon fallback
 *   - value string → presigned URL → show <img>
 */
export function useThumbnails(items: NodeListItem[]): Map<string, string | null> {
  const qc = useQueryClient();

  const imageItems = items.filter(
    (i) => i.node_type === "file" && i.file_mime_type?.startsWith("image/"),
  );

  // Only batch-fetch IDs whose individual cache entry is missing.
  const uncachedIds = imageItems
    .map((i) => i.id)
    .filter((id) => qc.getQueryData(["thumbnail", id]) === undefined);

  // One request for all uncached thumbnails.
  useQuery({
    queryKey: ["thumbnails-batch", uncachedIds.join(",")],
    queryFn: async () => {
      const batch = await nodesApi.thumbnailsBatch(uncachedIds);
      // Populate individual cache entries so the grid renders immediately.
      for (const [id, url] of Object.entries(batch)) {
        qc.setQueryData(["thumbnail", id], url ?? null);
      }
      return batch;
    },
    enabled: uncachedIds.length > 0,
    staleTime: STALE_MS,
    gcTime: GC_MS,
  });

  // Build the result map from per-item cache (populated above).
  const map = new Map<string, string | null>();
  for (const item of imageItems) {
    const cached = qc.getQueryData<string | null>(["thumbnail", item.id]);
    if (cached !== undefined) {
      map.set(item.id, cached);
    }
  }
  return map;
}
