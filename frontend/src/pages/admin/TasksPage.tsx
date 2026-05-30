import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { XCircle, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { tasksApi } from "@/api/tasks";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { BackgroundTaskListItem, BackgroundTaskStatus } from "@/types/tasks";
import { cn } from "@/lib/utils";

const STATUS_LABELS: Record<BackgroundTaskStatus, string> = {
  pending: "Ожидает",
  running: "Выполняется",
  completed: "Завершена",
  failed: "Ошибка",
  cancelled: "Отменена",
};

const STATUS_COLORS: Record<BackgroundTaskStatus, string> = {
  pending: "bg-amber-500 text-white dark:bg-amber-600",
  running: "bg-blue-600 text-white dark:bg-blue-700",
  completed: "bg-green-600 text-white dark:bg-green-700",
  failed: "bg-red-600 text-white dark:bg-red-700",
  cancelled: "bg-zinc-500 text-white dark:bg-zinc-600",
};

function TaskRow({ task }: { task: BackgroundTaskListItem }) {
  const qc = useQueryClient();

  const cancel = useMutation({
    mutationFn: () => tasksApi.cancel(task.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-tasks"] });
      toast.success("Задача отменена");
    },
    onError: () => toast.error("Не удалось отменить задачу"),
  });

  const canCancel = task.status === "pending" || task.status === "running";

  return (
    <tr className="border-b last:border-0 hover:bg-muted/40 transition-colors">
      <td className="px-4 py-2 text-xs font-mono text-muted-foreground">{task.task_type}</td>
      <td className="px-4 py-2">
        <span className={cn("inline-flex rounded-full px-2 py-0.5 text-xs font-semibold", STATUS_COLORS[task.status])}>
          {STATUS_LABELS[task.status]}
        </span>
      </td>
      <td className="px-4 py-2 text-xs text-muted-foreground">{task.priority}</td>
      <td className="px-4 py-2 text-xs text-muted-foreground whitespace-nowrap">
        {new Date(task.created_at).toLocaleString("ru-RU")}
      </td>
      <td className="px-4 py-2 text-xs text-muted-foreground">
        {task.started_at ? new Date(task.started_at).toLocaleString("ru-RU") : "—"}
      </td>
      <td className="px-4 py-2">
        {canCancel && (
          <Button
            variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-destructive"
            title="Отменить"
            disabled={cancel.isPending}
            onClick={() => cancel.mutate()}
          >
            {cancel.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <XCircle className="h-3.5 w-3.5" />}
          </Button>
        )}
      </td>
    </tr>
  );
}

const STATUS_OPTIONS = [
  { value: "", label: "Все" },
  { value: "pending", label: "Ожидающие" },
  { value: "running", label: "Выполняются" },
  { value: "completed", label: "Завершённые" },
  { value: "failed", label: "С ошибкой" },
  { value: "cancelled", label: "Отменённые" },
];

export function TasksPage() {
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(0);
  const LIMIT = 20;

  const { data, isLoading } = useQuery({
    queryKey: ["admin-tasks", status, page],
    queryFn: () =>
      tasksApi.list({
        status: status || undefined,
        limit: LIMIT,
        offset: page * LIMIT,
      }),
    refetchInterval: 5000,
  });

  const tasks = data?.items ?? [];
  const total = data?.total ?? 0;
  const pageCount = Math.ceil(total / LIMIT);

  return (
    <div className="flex flex-col gap-4">
      {/* Status filter */}
      <div className="flex flex-wrap gap-1">
        {STATUS_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => { setStatus(opt.value); setPage(0); }}
            className={cn(
              "rounded-full border px-3 py-1 text-xs transition-colors",
              status === opt.value
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border hover:bg-muted",
            )}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="rounded-lg border overflow-auto">
        <table className="w-full text-left min-w-[700px]">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Тип</th>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Статус</th>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Приоритет</th>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Создана</th>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground">Запущена</th>
              <th className="px-4 py-2 text-xs font-medium text-muted-foreground"></th>
            </tr>
          </thead>
          <tbody>
            {isLoading
              ? Array.from({ length: 6 }).map((_, i) => (
                  <tr key={i} className="border-b last:border-0">
                    {Array.from({ length: 6 }).map((__, j) => (
                      <td key={j} className="px-4 py-2">
                        <Skeleton className="h-4 rounded" />
                      </td>
                    ))}
                  </tr>
                ))
              : tasks.length === 0
              ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-sm text-muted-foreground">
                    Задач нет.
                  </td>
                </tr>
              )
              : tasks.map((t) => <TaskRow key={t.id} task={t} />)}
          </tbody>
        </table>
      </div>

      {pageCount > 1 && (
        <div className="flex items-center gap-2 text-sm">
          <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(p => p - 1)}>
            ← Назад
          </Button>
          <span className="text-muted-foreground">Стр. {page + 1} / {pageCount}</span>
          <Button variant="outline" size="sm" disabled={page >= pageCount - 1} onClick={() => setPage(p => p + 1)}>
            Вперёд →
          </Button>
        </div>
      )}
    </div>
  );
}
