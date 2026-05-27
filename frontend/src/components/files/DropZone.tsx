import { useCallback, useRef, useState, type ReactNode } from "react";
import { Upload } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  onDrop: (files: File[]) => void;
  disabled?: boolean;
  children: ReactNode;
}

export function DropZone({ onDrop, disabled, children }: Props) {
  const [isDragging, setIsDragging] = useState(false);
  const dragCounter = useRef(0);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current++;
    if (e.dataTransfer.items.length > 0) setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current--;
    if (dragCounter.current === 0) setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = "copy";
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      dragCounter.current = 0;
      setIsDragging(false);
      if (disabled) return;
      const files = Array.from(e.dataTransfer.files).filter((f) => f.size > 0);
      if (files.length) onDrop(files);
    },
    [onDrop, disabled],
  );

  return (
    <div
      className="relative min-h-0 flex-1"
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {children}

      {isDragging && (
        <div
          className={cn(
            "pointer-events-none absolute inset-0 z-20 flex flex-col items-center justify-center gap-3",
            "rounded-xl border-2 border-dashed border-primary bg-primary/5",
          )}
        >
          <Upload className="h-10 w-10 text-primary" />
          <p className="text-sm font-medium text-primary">Отпустите файлы для загрузки</p>
        </div>
      )}
    </div>
  );
}
