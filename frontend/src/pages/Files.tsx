import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { FolderPlus, Upload } from "lucide-react";
import { useFileBrowser } from "@/hooks/useFileBrowser";
import { useBreadcrumb } from "@/contexts/breadcrumb";
import { useUpload } from "@/contexts/upload";
import { FileGrid } from "@/components/files/FileGrid";
import { DropZone } from "@/components/files/DropZone";
import { CreateFolderDialog } from "@/components/files/CreateFolderDialog";
import { Button } from "@/components/ui/button";

export function FilesPage() {
  const { nodeId } = useParams<{ nodeId?: string }>();
  const { data, isLoading, error } = useFileBrowser(nodeId);
  const { setCrumbs } = useBreadcrumb();
  const { enqueue } = useUpload();
  const [createOpen, setCreateOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const folderQueryKey = nodeId
    ? ["nodes", nodeId, "content"]
    : ["nodes", "root"];

  const parentNodeId = data?.folder?.node_id ?? null;

  useEffect(() => {
    if (!data?.folder) {
      setCrumbs([{ label: "Файлы" }]);
      return;
    }
    setCrumbs([
      { label: "Файлы", href: "/files" },
      ...data.breadcrumbs.map((b) => ({
        label: b.name,
        href: `/files/folders/${b.id}`,
      })),
      { label: data.folder.node?.name ?? data.folder.node_id },
    ]);
  }, [data, setCrumbs]);

  const handleFiles = useCallback(
    (files: File[]) => {
      enqueue(files, parentNodeId, folderQueryKey);
    },
    [enqueue, parentNodeId, folderQueryKey],
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files ?? []).filter((f) => f.size > 0);
      if (files.length) handleFiles(files);
      e.target.value = "";
    },
    [handleFiles],
  );

  if (error) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-destructive">Не удалось загрузить файлы.</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">
          {data?.folder?.node?.name ?? "Файлы"}
        </h1>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={() => setCreateOpen(true)}>
            <FolderPlus className="mr-2 h-4 w-4" />
            Новая папка
          </Button>
          <Button
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            disabled={!parentNodeId}
            title={!parentNodeId ? "Перейдите в папку для загрузки файлов" : undefined}
          >
            <Upload className="mr-2 h-4 w-4" />
            Загрузить
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={handleInputChange}
          />
        </div>
      </div>

      {/* Drop zone wraps grid */}
      <DropZone onDrop={handleFiles} disabled={!parentNodeId}>
        <FileGrid items={data?.items ?? []} isLoading={isLoading} folderQueryKey={folderQueryKey} />
      </DropZone>

      <CreateFolderDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        parentNodeId={parentNodeId}
        currentNodeId={nodeId ?? null}
      />
    </div>
  );
}
