import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { FileIcon } from "./FileIcon";
import { getFolderColor } from "./FolderColorDialog";
import { formatBytes } from "@/hooks/useQuota";
import { nodesApi } from "@/api/nodes";
import { queryClient } from "@/lib/query-client";
import type { NodeListItem } from "@/types/nodes";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

const VISIBILITY_LABELS: Record<string, string> = {
  private: "Приватный",
  shared: "Общий доступ",
  public: "Публичный",
};

function formatDateFull(iso: string) {
  return new Date(iso).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="break-all text-sm">{value}</span>
    </div>
  );
}

interface Props {
  item: NodeListItem;
  onClose: () => void;
}

export function NodeInfoPanel({ item, onClose }: Props) {
  const isImage = item.node_type === "file" && !!item.file_mime_type?.startsWith("image/");
  const folderColor = item.node_type === "folder" ? getFolderColor(item.id) : null;

  // Initialise from the grid thumbnail cache — instant display when the item
  // was already visible in the file grid.
  const [previewUrl, setPreviewUrl] = useState<string | null>(() => {
    if (!isImage) return null;
    return queryClient.getQueryData<string | null>(["thumbnail", item.id]) ?? null;
  });
  const [previewLoading, setPreviewLoading] = useState(!previewUrl && isImage);

  useEffect(() => {
    // Cache hit — already shown via useState initialiser, nothing to do.
    const cached = queryClient.getQueryData<string | null>(["thumbnail", item.id]);
    if (cached !== undefined) {
      setPreviewUrl(cached);
      setPreviewLoading(false);
      return;
    }

    setPreviewUrl(null);
    if (!isImage) return;

    // Cache miss — fetch the compressed WebP thumbnail (not the full file).
    setPreviewLoading(true);
    nodesApi
      .thumbnail(item.id)
      .then((resp) => {
        const url = resp.presigned_url;
        queryClient.setQueryData(["thumbnail", item.id], url);
        setPreviewUrl(url);
      })
      .catch(() => setPreviewUrl(null))
      .finally(() => setPreviewLoading(false));
  }, [item.id, isImage]);

  return (
    <div className="flex h-full w-72 shrink-0 flex-col border-l bg-card">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-4 py-3">
        <span className="text-sm font-semibold">Информация</span>
        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Preview */}
      <div className="flex min-h-36 items-center justify-center border-b bg-muted/20 p-6">
        {isImage ? (
          previewLoading ? (
            <Skeleton className="h-32 w-full rounded-lg" />
          ) : previewUrl ? (
            <img
              src={previewUrl}
              alt={item.name}
              className="max-h-36 max-w-full rounded-lg object-contain shadow"
            />
          ) : (
            <FileIcon
              nodeType={item.node_type}
              mimeType={item.file_mime_type}
              className="h-16 w-16"
              color={folderColor}
            />
          )
        ) : (
          <FileIcon
            nodeType={item.node_type}
            mimeType={item.file_mime_type}
            className="h-16 w-16"
            color={folderColor}
          />
        )}
      </div>

      {/* Name */}
      <div className="border-b px-4 py-3">
        <p className="break-words text-sm font-semibold leading-snug" title={item.name}>
          {item.name}
        </p>
      </div>

      {/* Details */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="flex flex-col gap-4">
          <InfoRow
            label="Тип"
            value={item.node_type === "folder" ? "Папка" : "Файл"}
          />
          {item.file_mime_type && (
            <InfoRow label="MIME-тип" value={item.file_mime_type} />
          )}
          {item.file_size_bytes != null && (
            <InfoRow label="Размер" value={formatBytes(item.file_size_bytes)} />
          )}
          <InfoRow
            label="Видимость"
            value={VISIBILITY_LABELS[item.visibility] ?? item.visibility}
          />
          <InfoRow label="Путь" value={item.path} />
          <InfoRow label="Изменён" value={formatDateFull(item.updated_at)} />
          <InfoRow label="Создан" value={formatDateFull(item.created_at)} />
        </div>
      </div>
    </div>
  );
}
