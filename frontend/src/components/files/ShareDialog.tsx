import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Copy, Check, Link2, X, Loader2, Globe } from "lucide-react";
import { toast } from "sonner";
import { publicLinksApi } from "@/api/public-links";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { NodeType } from "@/types/nodes";
import { cn } from "@/lib/utils";

function useDebounce(value: string, ms: number) {
  const [d, setD] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setD(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return d;
}

function shareUrl(token: string) {
  return `${window.location.origin}/share/${token}`;
}

// ── Public link tab ───────────────────────────────────────────────────────────

function PublicLinkTab({ nodeId }: { nodeId: string }) {
  const qc = useQueryClient();
  const [copied, setCopied] = useState(false);

  const QUERY_KEY = ["public-links", "node", nodeId];

  const { data, isLoading } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: () => publicLinksApi.listForNode(nodeId),
  });

  const activeLink = (data?.items ?? []).find((l) => l.is_active) ?? null;

  const create = useMutation({
    mutationFn: () =>
      publicLinksApi.create({ node_id: nodeId, permission_type: "download" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEY });
      toast.success("Ссылка создана");
    },
    onError: () => toast.error("Не удалось создать ссылку"),
  });

  const revoke = useMutation({
    mutationFn: (id: string) => publicLinksApi.revoke(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEY });
      toast.success("Ссылка отозвана");
    },
    onError: () => toast.error("Не удалось отозвать ссылку"),
  });

  function handleCopy(token: string) {
    navigator.clipboard.writeText(shareUrl(token)).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (isLoading) {
    return (
      <div className="flex flex-col gap-3">
        <Skeleton className="h-20 rounded-xl" />
        <Skeleton className="h-9 rounded-lg" />
      </div>
    );
  }

  if (activeLink) {
    const url = shareUrl(activeLink.token);
    return (
      <div className="flex flex-col gap-4">
        {/* Active link card */}
        <div className="flex flex-col gap-3 rounded-xl border bg-muted/30 p-4">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-green-500 shadow-sm shadow-green-500/50" />
            <span className="text-sm font-medium">Ссылка активна</span>
          </div>

          <div className="flex gap-2">
            <Input
              readOnly
              value={url}
              className="h-8 flex-1 font-mono text-xs"
              onFocus={(e) => e.target.select()}
            />
            <Button
              variant="outline"
              size="icon"
              className={cn(
                "h-8 w-8 shrink-0 transition-colors",
                copied && "border-green-500 text-green-600",
              )}
              onClick={() => handleCopy(activeLink.token)}
              title="Скопировать ссылку"
            >
              {copied ? (
                <Check className="h-3.5 w-3.5" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
            </Button>
          </div>
        </div>

        <button
          type="button"
          disabled={revoke.isPending}
          onClick={() => revoke.mutate(activeLink.id)}
          className="flex items-center gap-1.5 self-start text-xs text-muted-foreground transition-colors hover:text-destructive disabled:opacity-50"
        >
          {revoke.isPending ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <X className="h-3 w-3" />
          )}
          Отозвать ссылку
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed py-6 text-center">
        <Globe className="h-8 w-8 text-muted-foreground/50" />
        <p className="text-sm text-muted-foreground">
          Поделитесь файлом с любым человеком по ссылке
        </p>
      </div>

      <Button
        disabled={create.isPending}
        onClick={() => create.mutate()}
      >
        {create.isPending ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          <Link2 className="mr-2 h-4 w-4" />
        )}
        Создать ссылку
      </Button>
    </div>
  );
}

// ── Main dialog ───────────────────────────────────────────────────────────────

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  nodeId: string;
  nodeName: string;
  nodeType: NodeType;
}

export function ShareDialog({ open, onOpenChange, nodeId, nodeName }: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader className="pr-6">
          <DialogTitle className="flex items-center gap-2">
            <Link2 className="h-4 w-4 text-muted-foreground" />
            Публичная ссылка
          </DialogTitle>
          <p
            className="truncate text-sm text-muted-foreground"
            title={nodeName}
          >
            {nodeName}
          </p>
        </DialogHeader>

        <PublicLinkTab nodeId={nodeId} />
      </DialogContent>
    </Dialog>
  );
}
