import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { quotasApi } from "@/api/quotas";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { formatBytes } from "@/hooks/useQuota";

interface Props {
  open: boolean;
  onClose: () => void;
  currentLimitBytes: number;
}

const GB = 1024 * 1024 * 1024;

export function RequestStorageDialog({ open, onClose, currentLimitBytes }: Props) {
  const qc = useQueryClient();
  const [gbValue, setGbValue] = useState("10");
  const [reason, setReason] = useState("");

  const requestedBytes = Math.round(parseFloat(gbValue || "0") * GB);
  const isValid = requestedBytes > 0 && !isNaN(requestedBytes);

  const submit = useMutation({
    mutationFn: () =>
      quotasApi.submitIncreaseRequest({
        requested_bytes: requestedBytes,
        reason: reason.trim() || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["quota", "increase-requests", "my"] });
      toast.success("Запрос отправлен администратору");
      onClose();
      setGbValue("10");
      setReason("");
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail;
      if (typeof detail === "string") {
        toast.error(detail);
      } else {
        toast.error("Не удалось отправить запрос");
      }
    },
  });

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Запросить увеличение хранилища</DialogTitle>
          <DialogDescription>
            Текущий лимит: <strong>{formatBytes(currentLimitBytes)}</strong>.
            Запрос будет рассмотрен администратором.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3">
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">
              Запросить дополнительно (ГБ)
            </label>
            <Input
              type="number"
              min="1"
              step="1"
              value={gbValue}
              onChange={(e) => setGbValue(e.target.value)}
              className="h-8 text-sm"
              placeholder="Например: 10"
            />
            {isValid && (
              <p className="mt-1 text-xs text-muted-foreground">
                +{formatBytes(requestedBytes)} → новый лимит: {formatBytes(currentLimitBytes + requestedBytes)}
              </p>
            )}
          </div>

          <div>
            <label className="mb-1 block text-xs text-muted-foreground">
              Причина (необязательно)
            </label>
            <Textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Укажите причину запроса..."
              className="h-20 resize-none text-sm"
              maxLength={1024}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={onClose}>
            Отмена
          </Button>
          <Button
            size="sm"
            disabled={!isValid || submit.isPending}
            onClick={() => submit.mutate()}
          >
            {submit.isPending && <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />}
            Отправить запрос
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
