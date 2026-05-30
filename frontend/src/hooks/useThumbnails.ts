import { useQuery, useQueryClient } from "@tanstack/react-query";
import { nodesApi } from "@/api/nodes";
import { getThumbnailCache, setThumbnailCache } from "@/lib/thumbnailCache";
import type { NodeListItem } from "@/types/nodes";

const STALE_MS = 4 * 60 * 1000;
const GC_MS = 10 * 60 * 1000;

/**
 * Fetches presigned thumbnail URLs for all image items in ONE batch request.
 *
 * Cache hierarchy (checked in order, both survive page refresh via sessionStorage):
 *   1. React Query in-memory cache  — instant, lost on refresh
 *   2. sessionStorage               — survives refresh, cleared on tab close
 *   3. Batch API request            — only for IDs missing from both caches
 *
 * Returns a Map where:
 *   - key absent  → still loading  → show skeleton
 *   - value null  → no thumbnail   → show icon fallback
 *   - value string → presigned URL → show <img>
 */
export function useThumbnails(items: NodeListItem[]): Map<string, string | null> {
  const qc = useQueryClient();

  const imageItems = items.filter(
    (i) => i.node_type === "file" && i.file_mime_type?.startsWith("image/"),
  );

  // Skip IDs that are in RQ cache OR sessionStorage.
  const uncachedIds = imageItems
    .map((i) => i.id)
    .filter((id) => {
      if (qc.getQueryData(["thumbnail", id]) !== undefined) return false;
      if (getThumbnailCache(id) !== undefined) return false;
      return true;
    });

  useQuery({
    queryKey: ["thumbnails-batch", uncachedIds.join(",")],
    queryFn: async () => {
      const batch = await nodesApi.thumbnailsBatch(uncachedIds);
      for (const [id, url] of Object.entries(batch)) {
        const value = url ?? null;
        qc.setQueryData(["thumbnail", id], value);
        setThumbnailCache(id, value);
      }
      return batch;
    },
    enabled: uncachedIds.length > 0,
    staleTime: STALE_MS,
    gcTime: GC_MS,
  });

  // Build result map: RQ cache first, sessionStorage fallback.
  const map = new Map<string, string | null>();
  for (const item of imageItems) {
    const rq = qc.getQueryData<string | null>(["thumbnail", item.id]);
    if (rq !== undefined) {
      map.set(item.id, rq);
      continue;
    }
    const stored = getThumbnailCache(item.id);
    if (stored !== undefined) {
      map.set(item.id, stored);
    }
  }
  return map;
}
