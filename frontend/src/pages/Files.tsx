import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useLocation } from "react-router-dom";
import { FolderPlus, LayoutGrid, LayoutList, Upload } from "lucide-react";
import { useFileBrowser } from "@/hooks/useFileBrowser";
import { useBreadcrumb } from "@/contexts/breadcrumb";
import { useUpload } from "@/contexts/upload";
import { FileGrid, type ViewMode } from "@/components/files/FileGrid";
import { FileFilterBar, applyFilter, type FileFilter } from "@/components/files/FileFilterBar";
import { FileActionBar } from "@/components/files/FileActionBar";
import { DropZone } from "@/components/files/DropZone";
import { CreateFolderDialog } from "@/components/files/CreateFolderDialog";
import { Button } from "@/components/ui/button";
import type { NodeListItem } from "@/types/nodes";

const VIEW_KEY = "file-view-mode";

export function FilesPage() {
  const { nodeId } = useParams<{ nodeId?: string }>();
  const location = useLocation();
  const { data, isLoading, error } = useFileBrowser(nodeId);
  const { setCrumbs } = useBreadcrumb();
  const { enqueue } = useUpload();
  const [createOpen, setCreateOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [view, setView] = useState<ViewMode>(() => {
    const saved = localStorage.getItem(VIEW_KEY);
    return saved === "list" ? "list" : "grid";
  });
  const [filter, setFilter] = useState<FileFilter>("all");
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);

  // Derive the selected item from fresh query data so renames/updates reflect immediately
  const selectedItem = useMemo<NodeListItem | null>(
    () =>
      selectedItemId
        ? (data?.items.find((i) => i.id === selectedItemId) ?? null)
        : null,
    [selectedItemId, data?.items],
  );

  // On every navigation: pre-select a file from search state, or clear selection
  useEffect(() => {
    const state = location.state as { selectId?: string } | null;
    setSelectedItemId(state?.selectId ?? null);
  }, [location.key]);

  function toggleView(v: ViewMode) {
    setView(v);
    localStorage.setItem(VIEW_KEY, v);
  }

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

  function handleSelectItem(item: NodeListItem) {
    setSelectedItemId(item.id);
  }

  const filteredItems = applyFilter(data?.items ?? [], filter);

  if (error) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-destructive">Не удалось загрузить файлы.</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-3">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">
          {data?.folder?.node?.name ?? "Файлы"}
        </h1>
        <div className="flex items-center gap-2">
          {/* View toggle */}
          <div className="flex rounded-lg border p-0.5">
            <Button
              size="icon"
              variant={view === "grid" ? "secondary" : "ghost"}
              className="h-7 w-7"
              onClick={() => toggleView("grid")}
              aria-label="Сетка"
            >
              <LayoutGrid className="h-3.5 w-3.5" />
            </Button>
            <Button
              size="icon"
              variant={view === "list" ? "secondary" : "ghost"}
              className="h-7 w-7"
              onClick={() => toggleView("list")}
              aria-label="Список"
            >
              <LayoutList className="h-3.5 w-3.5" />
            </Button>
          </div>

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

      {/* Filter bar or action bar */}
      {selectedItem ? (
        <FileActionBar
          item={selectedItem}
          folderQueryKey={folderQueryKey}
          onDeselect={() => setSelectedItemId(null)}
        />
      ) : (
        <FileFilterBar active={filter} onChange={setFilter} />
      )}

      {/* Drop zone wraps grid */}
      <DropZone onDrop={handleFiles} disabled={!parentNodeId}>
        <FileGrid
          items={filteredItems}
          isLoading={isLoading}
          folderQueryKey={folderQueryKey}
          view={view}
          selectedItemId={selectedItemId}
          onSelectItem={handleSelectItem}
          onDeselect={() => setSelectedItemId(null)}
        />
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
