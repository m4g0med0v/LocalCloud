import { useParams } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useState, useEffect, useRef } from "react";
import { Download, FileText, Folder, Loader2, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { publicLinksApi } from "@/api/public-links";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { BackgroundTaskStatus } from "@/types/public-links";


export function SharePage() {
  const { token } = useParams<{ token: string }>();

  const { data: link, isLoading, isError } = useQuery({
    queryKey: ["share", token],
    queryFn: () => publicLinksApi.getPublic(token!),
    enabled: !!token,
    retry: false,
  });

  const download = useMutation({
    mutationFn: () => publicLinksApi.download(token!),
    onSuccess: (resp) => {
      const a = document.createElement("a");
      a.href = resp.presigned_url;
      a.download = resp.filename ?? "download";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    },
    onError: () => toast.error("Не удалось скачать файл"),
  });

  const [folderStatus, setFolderStatus] = useState<BackgroundTaskStatus | null>(null);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function stopPolling() {
    if (pollRef.current !== null) {
      clearTimeout(pollRef.current);
      pollRef.current = null;
    }
  }

  useEffect(() => {
    return stopPolling;
  }, []);

  const startFolderArchive = useMutation({
    mutationFn: () => publicLinksApi.startFolderArchive(token!),
    onSuccess: (resp) => {
      setFolderStatus(resp.status);
      if (resp.status === "completed" && resp.presigned_url) {
        triggerDownload(resp.presigned_url, resp.filename ?? "archive.zip");
        return;
      }

      function schedulePoll() {
        pollRef.current = setTimeout(async () => {
          try {
            const status = await publicLinksApi.pollFolderArchive(token!, resp.task_id);
            setFolderStatus(status.status);
            if (status.status === "completed" && status.presigned_url) {
              pollRef.current = null;
              triggerDownload(status.presigned_url, status.filename ?? "archive.zip");
            } else if (status.status === "failed") {
              pollRef.current = null;
              toast.error("Не удалось создать архив папки");
            } else {
              schedulePoll();
            }
          } catch {
            pollRef.current = null;
            toast.error("Не удалось получить статус архива");
          }
        }, 2000);
      }

      schedulePoll();
    },
    onError: () => toast.error("Не удалось начать создание архива"),
  });

  function triggerDownload(url: string, filename: string) {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  const isFolderArchiving = startFolderArchive.isPending ||
    (folderStatus !== null && folderStatus !== "completed" && folderStatus !== "failed");

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-6">
        <div className="w-full max-w-sm space-y-4">
          <Skeleton className="h-16 w-16 rounded-full mx-auto" />
          <Skeleton className="h-6 w-48 mx-auto" />
          <Skeleton className="h-4 w-32 mx-auto" />
          <Skeleton className="h-9 w-full" />
        </div>
      </div>
    );
  }

  if (isError || !link || link.status !== "active") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-6">
        <div className="flex flex-col items-center gap-4 text-center">
          <AlertTriangle className="h-12 w-12 text-muted-foreground" />
          <h1 className="text-xl font-semibold">Ссылка недоступна</h1>
          <p className="text-sm text-muted-foreground max-w-xs">
            Эта ссылка устарела, была отозвана или не существует.
          </p>
        </div>
      </div>
    );
  }

  const node = link.node;
  const isFolder = node?.node_type === "folder";
  const canDownload = link.permission_type === "download";

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <div className="flex w-full max-w-sm flex-col items-center gap-6 rounded-xl border p-8 shadow-sm">
        {/* Icon */}
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
          {isFolder ? (
            <Folder className="h-8 w-8 text-muted-foreground" />
          ) : (
            <FileText className="h-8 w-8 text-muted-foreground" />
          )}
        </div>

        {/* Info */}
        <div className="flex flex-col items-center gap-1 text-center">
          <h1 className="text-lg font-semibold leading-tight break-all">
            {node?.name ?? "Файл"}
          </h1>
          {link.description && (
            <p className="mt-1 text-sm text-muted-foreground">{link.description}</p>
          )}
        </div>

        {/* Action */}
        {canDownload ? (
          isFolder ? (
            <Button
              className="w-full"
              disabled={isFolderArchiving}
              onClick={() => { setFolderStatus(null); stopPolling(); startFolderArchive.mutate(); }}
            >
              {isFolderArchiving ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {folderStatus === "in_progress" ? "Создаётся архив…" : "Подготовка…"}
                </>
              ) : (
                <>
                  <Download className="mr-2 h-4 w-4" />
                  Скачать как ZIP
                </>
              )}
            </Button>
          ) : (
            <Button
              className="w-full"
              disabled={download.isPending}
              onClick={() => download.mutate()}
            >
              {download.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Download className="mr-2 h-4 w-4" />
              )}
              Скачать
            </Button>
          )
        ) : (
          <p className="text-sm text-muted-foreground">Доступ только для просмотра.</p>
        )}

        <p className="text-xs text-muted-foreground">
          Доступ: {link.permission_type === "view" ? "Просмотр" : link.permission_type === "download" ? "Скачивание" : "Загрузка"}
          {link.expires_at && (
            <> · до {new Date(link.expires_at).toLocaleDateString("ru-RU")}</>
          )}
        </p>
      </div>
    </div>
  );
}
