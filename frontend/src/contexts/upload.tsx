import {
  createContext,
  useCallback,
  useContext,
  useReducer,
  useRef,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import { uploadsApi } from "@/api/uploads";

const PART_SIZE = 8 * 1024 * 1024; // 8 MB — matches backend default

export type UploadStatus = "pending" | "uploading" | "done" | "error";

export interface UploadTask {
  id: string;
  filename: string;
  progress: number;
  status: UploadStatus;
  error: string | null;
}

type Action =
  | { type: "ADD"; tasks: UploadTask[] }
  | { type: "PROGRESS"; id: string; progress: number }
  | { type: "DONE"; id: string }
  | { type: "ERROR"; id: string; error: string }
  | { type: "DISMISS"; id: string };

function reducer(state: UploadTask[], action: Action): UploadTask[] {
  switch (action.type) {
    case "ADD":
      return [...state, ...action.tasks];
    case "PROGRESS":
      return state.map((t) =>
        t.id === action.id ? { ...t, progress: action.progress, status: "uploading" } : t,
      );
    case "DONE":
      return state.map((t) =>
        t.id === action.id ? { ...t, progress: 100, status: "done" } : t,
      );
    case "ERROR":
      return state.map((t) =>
        t.id === action.id ? { ...t, status: "error", error: action.error } : t,
      );
    case "DISMISS":
      return state.filter((t) => t.id !== action.id);
    default:
      return state;
  }
}

interface UploadContextValue {
  tasks: UploadTask[];
  enqueue: (files: File[], parentNodeId: string | null, folderQueryKey: unknown[]) => void;
  dismiss: (id: string) => void;
}

const UploadContext = createContext<UploadContextValue | null>(null);

export function UploadProvider({ children }: { children: ReactNode }) {
  const [tasks, dispatch] = useReducer(reducer, []);
  const queryClient = useQueryClient();
  const idRef = useRef(0);

  const runUpload = useCallback(
    async (task: UploadTask, file: File, parentNodeId: string | null, qKey: unknown[]) => {
      try {
        if (!parentNodeId) {
          throw new Error("Выберите папку для загрузки файлов");
        }

        const partsCount = Math.max(1, Math.ceil(file.size / PART_SIZE));
        const partSizeBytes = partsCount === 1 ? file.size : PART_SIZE;

        // 1. Create session
        const session = await uploadsApi.create({
          parent_node_id: parentNodeId,
          filename: file.name,
          file_size_bytes: file.size,
          parts_count: partsCount,
          mime_type: file.type || null,
          part_size_bytes: partSizeBytes,
        });

        // 2. Get presigned parts
        const { parts } = await uploadsApi.getPresignedParts(session.id);

        const completedParts: { part_number: number; etag: string; size_bytes: number }[] = [];

        // 3. Upload each part
        for (const part of parts) {
          const start = (part.part_number - 1) * partSizeBytes;
          const end = Math.min(start + partSizeBytes, file.size);
          const blob = file.slice(start, end);
          const actualSize = end - start;

          // Filter out browser-restricted headers
          const restricted = new Set([
            "content-length",
            "host",
            "connection",
            "transfer-encoding",
          ]);
          const safeHeaders: Record<string, string> = {};
          for (const [k, v] of Object.entries(part.headers ?? {})) {
            if (!restricted.has(k.toLowerCase())) safeHeaders[k] = v;
          }

          const resp = await fetch(part.url, {
            method: "PUT",
            body: blob,
            headers: safeHeaders,
          });

          if (!resp.ok) {
            throw new Error(`Part ${part.part_number} upload failed: ${resp.status}`);
          }

          const rawEtag = resp.headers.get("ETag") ?? resp.headers.get("etag") ?? "";
          const etag = rawEtag.replace(/"/g, "");

          // 4. Confirm part
          await uploadsApi.completePart(session.id, part.part_number, {
            part_number: part.part_number,
            etag,
            size_bytes: actualSize,
          });

          completedParts.push({ part_number: part.part_number, etag, size_bytes: actualSize });

          const progress = Math.round((part.part_number / partsCount) * 95);
          dispatch({ type: "PROGRESS", id: task.id, progress });
        }

        // 5. Complete upload
        await uploadsApi.complete(session.id, {
          upload_session_id: session.id,
          parts: completedParts,
        });

        dispatch({ type: "DONE", id: task.id });
        queryClient.invalidateQueries({ queryKey: qKey });
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Ошибка загрузки";
        dispatch({ type: "ERROR", id: task.id, error: msg });
      }
    },
    [queryClient],
  );

  const enqueue = useCallback(
    (files: File[], parentNodeId: string | null, folderQueryKey: unknown[]) => {
      const newTasks: UploadTask[] = files.map((file) => ({
        id: String(++idRef.current),
        filename: file.name,
        progress: 0,
        status: "pending" as UploadStatus,
        error: null,
      }));
      dispatch({ type: "ADD", tasks: newTasks });
      newTasks.forEach((task, i) =>
        runUpload(task, files[i], parentNodeId, folderQueryKey),
      );
    },
    [runUpload],
  );

  const dismiss = useCallback((id: string) => {
    dispatch({ type: "DISMISS", id });
  }, []);

  return (
    <UploadContext.Provider value={{ tasks, enqueue, dismiss }}>
      {children}
    </UploadContext.Provider>
  );
}

export function useUpload() {
  const ctx = useContext(UploadContext);
  if (!ctx) throw new Error("useUpload must be used inside <UploadProvider>");
  return ctx;
}
