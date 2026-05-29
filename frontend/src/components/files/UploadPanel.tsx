import { CheckCircle2, Loader2, X, XCircle } from "lucide-react";
import { useUpload, type UploadTask } from "@/contexts/upload";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

function TaskRow({ task }: { task: UploadTask }) {
  const { dismiss } = useUpload();
  const isDone = task.status === "done";
  const isError = task.status === "error";

  return (
    <div className="flex items-center gap-2 py-1">
      <div className="flex-1 min-w-0">
        <p className="truncate text-xs font-medium" title={task.filename}>
          {task.filename}
        </p>
        {isError ? (
          <p className="truncate text-[10px] text-destructive">{task.error}</p>
        ) : (
          <Progress
            value={task.progress}
            className={cn("mt-1 h-1", isDone && "opacity-50")}
          />
        )}
      </div>

      <div className="flex shrink-0 items-center gap-1">
        {isDone && <CheckCircle2 className="h-4 w-4 text-green-500" />}
        {isError && <XCircle className="h-4 w-4 text-destructive" />}
        {task.status === "uploading" && (
          <Loader2 className="h-4 w-4 animate-spin text-primary" />
        )}
        {(isDone || isError) && (
          <Button
            variant="ghost"
            size="icon"
            className="h-5 w-5"
            onClick={() => dismiss(task.id)}
            aria-label="Убрать"
          >
            <X className="h-3 w-3" />
          </Button>
        )}
      </div>
    </div>
  );
}

export function UploadPanel() {
  const { tasks, dismissAllDone } = useUpload();
  if (!tasks.length) return null;

  const active = tasks.filter((t) => t.status === "uploading" || t.status === "pending").length;
  const finished = tasks.filter((t) => t.status === "done" || t.status === "error").length;

  return (
    <div className="fixed bottom-4 right-4 z-50 w-72 rounded-xl border bg-card shadow-xl">
      <div className="flex items-center justify-between border-b px-3 py-2">
        <p className="text-xs font-semibold">
          {active > 0 ? `Загрузка файлов (${active})` : "Загрузки"}
        </p>
        {finished > 1 && (
          <button
            type="button"
            onClick={dismissAllDone}
            className="text-[10px] text-muted-foreground hover:text-foreground transition-colors"
          >
            Закрыть завершённые
          </button>
        )}
      </div>
      <div className="max-h-52 overflow-y-auto px-3 pb-2 pt-1">
        {tasks.map((t) => (
          <TaskRow key={t.id} task={t} />
        ))}
      </div>
    </div>
  );
}
