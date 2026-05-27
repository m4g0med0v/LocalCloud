import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { foldersApi } from "@/api/folders";
import { useUpload } from "@/contexts/upload";

export function useFolderUpload() {
  const { enqueue } = useUpload();
  const queryClient = useQueryClient();

  const uploadFolder = useCallback(
    async (
      files: File[],
      parentNodeId: string,
      folderQueryKey: unknown[],
    ) => {
      const validFiles = files.filter((f) => f.size > 0 && f.webkitRelativePath);
      if (!validFiles.length) return;

      // Collect every unique directory path that must exist.
      // webkitRelativePath example: "myproject/src/utils/helper.ts"
      // → we need dirs: "myproject", "myproject/src", "myproject/src/utils"
      const dirSet = new Set<string>();
      for (const file of validFiles) {
        const parts = file.webkitRelativePath.split("/");
        for (let depth = 1; depth < parts.length; depth++) {
          dirSet.add(parts.slice(0, depth).join("/"));
        }
      }

      // Sort shallowest-first so every parent is created before its children
      const sortedDirs = Array.from(dirSet).sort(
        (a, b) => a.split("/").length - b.split("/").length,
      );

      // Map dirPath → node_id; root ("") is the upload destination
      const pathNodeId = new Map<string, string>();
      pathNodeId.set("", parentNodeId);

      if (sortedDirs.length > 0) {
        const toastId = toast.loading(
          `Создание структуры папок (0 / ${sortedDirs.length})…`,
        );
        let done = 0;

        for (const dirPath of sortedDirs) {
          const segments = dirPath.split("/");
          const name = segments[segments.length - 1];
          const parentPath = segments.slice(0, -1).join("/");
          const pid = pathNodeId.get(parentPath);

          if (!pid) {
            // parent failed — whole subtree is skipped
            done++;
            continue;
          }

          try {
            const folder = await foldersApi.create({ name, parent_id: pid });
            pathNodeId.set(dirPath, folder.node_id);
          } catch {
            toast.error(`Не удалось создать папку «${name}»`);
          }

          done++;
          toast.loading(
            `Создание структуры папок (${done} / ${sortedDirs.length})…`,
            { id: toastId },
          );
        }

        toast.dismiss(toastId);

        // Show new folders in the current view immediately
        queryClient.invalidateQueries({ queryKey: folderQueryKey });
      }

      // Group files by the node_id of their target folder
      const groups = new Map<string, File[]>();
      for (const file of validFiles) {
        const parts = file.webkitRelativePath.split("/");
        const dirPath = parts.slice(0, -1).join("/");
        const targetId = pathNodeId.get(dirPath);
        if (!targetId) continue;
        if (!groups.has(targetId)) groups.set(targetId, []);
        groups.get(targetId)!.push(file);
      }

      // Enqueue every group — each group uploads to its own folder
      for (const [targetId, groupFiles] of groups) {
        enqueue(groupFiles, targetId, folderQueryKey);
      }
    },
    [enqueue, queryClient],
  );

  return { uploadFolder };
}
