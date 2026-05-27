import { useState } from "react";
import { toast } from "sonner";
import { nodesApi } from "@/api/nodes";
import { foldersApi } from "@/api/folders";
import { tasksApi } from "@/api/tasks";
import { downloadsApi } from "@/api/downloads";

const POLL_INTERVAL_MS = 2000;
const TIMEOUT_MS = 15 * 60 * 1000; // 15 minutes

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

const STATUS_LABELS: Record<string, string> = {
  pending:   "В очереди…",
  running:   "Архивируется…",
  completed: "Готово",
  failed:    "Ошибка",
  cancelled: "Отменено",
};

export function useFolderDownload() {
  const [downloading, setDownloading] = useState<string | null>(null);

  async function downloadFolder(nodeId: string, folderName: string) {
    if (downloading) return;
    setDownloading(nodeId);

    const toastId = toast.loading(`Подготовка «${folderName}»… В очереди`);
    const deadline = Date.now() + TIMEOUT_MS;

    try {
      // 1. Resolve folder metadata id from node
      const content = await nodesApi.content(nodeId);
      const folderId = content.folder.id;

      // 2. Request archive task
      const archiveResp = await foldersApi.archive(folderId, folderName);
      const taskId = archiveResp.task_id;

      // 3. Poll until done
      let task = await tasksApi.get(taskId);
      while (task.status !== "completed" && task.status !== "failed" && task.status !== "cancelled") {
        if (Date.now() > deadline) throw new Error("Превышено время ожидания (15 мин)");
        await sleep(POLL_INTERVAL_MS);
        task = await tasksApi.get(taskId);
        const label = STATUS_LABELS[task.status] ?? task.status;
        toast.loading(`Подготовка «${folderName}»… ${label}`, { id: toastId });
      }

      if (task.status !== "completed") {
        throw new Error(task.error_message ?? "Архивация завершилась с ошибкой");
      }

      // 4. Get presigned download URL
      toast.loading(`Получение ссылки…`, { id: toastId });
      const downloadResp = await downloadsApi.archiveUrl(taskId, `${folderName}.zip`);

      // 5. Trigger browser download
      const a = document.createElement("a");
      a.href = downloadResp.presigned_url;
      a.download = downloadResp.filename ?? `${folderName}.zip`;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);

      toast.success(`«${folderName}» скачивается`, { id: toastId });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Неизвестная ошибка";
      toast.error(`Не удалось скачать «${folderName}»: ${message}`, { id: toastId });
    } finally {
      setDownloading(null);
    }
  }

  return { downloadFolder, downloading };
}
