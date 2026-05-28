import { useQueries } from "@tanstack/react-query";
import { nodesApi } from "@/api/nodes";
import type { NodeListItem } from "@/types/nodes";

const THUMBNAIL_CONCURRENCY = 5;

class Semaphore {
  private running = 0;
  private readonly queue: Array<() => void> = [];

  constructor(private readonly limit: number) {}

  acquire(): Promise<void> {
    if (this.running < this.limit) {
      this.running++;
      return Promise.resolve();
    }
    return new Promise<void>((resolve) => {
      this.queue.push(() => {
        this.running++;
        resolve();
      });
    });
  }

  release(): void {
    this.running--;
    const next = this.queue.shift();
    if (next) next();
  }
}

const thumbnailSemaphore = new Semaphore(THUMBNAIL_CONCURRENCY);

/**
 * Prefetches presigned download URLs for all image items in parallel.
 * At most THUMBNAIL_CONCURRENCY requests run concurrently; the rest queue.
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
      queryFn: async () => {
        await thumbnailSemaphore.acquire();
        try {
          return await nodesApi.thumbnail(item.id).then((r) => r.presigned_url);
        } finally {
          thumbnailSemaphore.release();
        }
      },
      staleTime: 4 * 60 * 1000,
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
  });
  return map;
}
