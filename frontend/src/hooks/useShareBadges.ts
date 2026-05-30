import { useQueries } from "@tanstack/react-query";
import { publicLinksApi } from "@/api/public-links";
import { permissionsApi } from "@/api/permissions";
import type { NodeListItem } from "@/types/nodes";

export interface ShareBadge {
  hasPublicLink: boolean;
  hasSharedAccess: boolean;
}

/**
 * Fetches share status for all items in parallel.
 * Query keys are aligned with ShareDialog so mutations there auto-refresh these badges.
 */
export function useShareBadges(items: NodeListItem[]): Map<string, ShareBadge> {
  const ids = items.map((i) => i.id);

  // Public links: same key as ShareDialog — invalidated automatically on create/revoke
  const linkQueries = useQueries({
    queries: ids.map((id) => ({
      queryKey: ["public-links", "node", id],
      queryFn: () => publicLinksApi.listForNode(id),
      staleTime: 10 * 60 * 1000,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
    })),
  });

  // Permissions: limit:1 just to check existence; separate key to avoid cache shape conflicts
  const permQueries = useQueries({
    queries: ids.map((id) => ({
      queryKey: ["permissions", "node", id, "badge"],
      queryFn: () => permissionsApi.listForNode(id, { active_only: true, limit: 1 }),
      staleTime: 10 * 60 * 1000,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
    })),
  });

  const map = new Map<string, ShareBadge>();
  ids.forEach((id, i) => {
    const hasPublicLink =
      (linkQueries[i].data?.items ?? []).some((l) => l.is_active);
    const hasSharedAccess =
      (permQueries[i].data?.meta.total ?? 0) > 0;

    if (hasPublicLink || hasSharedAccess) {
      map.set(id, { hasPublicLink, hasSharedAccess });
    }
  });

  return map;
}
