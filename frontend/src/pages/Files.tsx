import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useLocation } from "react-router-dom";
import { FolderPlus, FolderUp, LayoutGrid, LayoutList, Upload } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useFileBrowser } from "@/hooks/useFileBrowser";
import { useBreadcrumb } from "@/contexts/breadcrumb";
import { useUpload } from "@/contexts/upload";
import { useFolderUpload } from "@/hooks/useFolderUpload";
import { nodesApi } from "@/api/nodes";
import { FileGrid, sortItems, type ViewMode, type SelectOpts } from "@/components/files/FileGrid";
import { FileFilterBar, applyFilter, type FileFilter } from "@/components/files/FileFilterBar";
import { FileActionBar } from "@/components/files/FileActionBar";
import { FileMultiActionBar } from "@/components/files/FileMultiActionBar";
import { DropZone } from "@/components/files/DropZone";
import { CreateFolderDialog } from "@/components/files/CreateFolderDialog";
import { Button } from "@/components/ui/button";
import { useInfoPanel } from "@/contexts/infoPanel";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import type { NodeListItem } from "@/types/nodes";

const VIEW_KEY = "file-view-mode";

export function FilesPage() {
  const { nodeId } = useParams<{ nodeId?: string }>();
  const location = useLocation();
  const { data, isLoading, error } = useFileBrowser(nodeId);
  const { setCrumbs } = useBreadcrumb();
  const { enqueue } = useUpload();
  const { uploadFolder } = useFolderUpload();
  const { selectedItem: infoPanelItem, openInfo } = useInfoPanel();
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

  // webkitdirectory is not in React's type definitions — set it imperatively
  useEffect(() => {
    folderInputRef.current?.setAttribute("webkitdirectory", "");
  }, []);

  const [view, setView] = useState<ViewMode>(() => {
    const saved = localStorage.getItem(VIEW_KEY);
    return saved === "list" ? "list" : "grid";
  });
  const [filter, setFilter] = useState<FileFilter>("all");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const lastSelectedIdRef = useRef<string | null>(null);

  // Derive selected items from fresh query data so renames/updates reflect immediately
  const selectedItems = useMemo<NodeListItem[]>(
    () => (data?.items ?? []).filter((i) => selectedIds.has(i.id)),
    [selectedIds, data?.items],
  );

  // On every navigation: pre-select a file from search state, or clear selection
  useEffect(() => {
    const state = location.state as { selectId?: string } | null;
    const selectId = state?.selectId ?? null;
    setSelectedIds(selectId ? new Set([selectId]) : new Set());
    lastSelectedIdRef.current = selectId;
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

  const handleFolderInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (!parentNodeId) return;
      const captured = Array.from(e.target.files ?? []);
      e.target.value = "";
      if (captured.length) uploadFolder(captured, parentNodeId, folderQueryKey);
    },
    [uploadFolder, parentNodeId, folderQueryKey],
  );

  function handleSelectItem(item: NodeListItem, opts: SelectOpts) {
    const filteredSorted = sortItems(applyFilter(data?.items ?? [], filter));

    if (opts.shift && lastSelectedIdRef.current) {
      const anchorIdx = filteredSorted.findIndex((i) => i.id === lastSelectedIdRef.current);
      const clickIdx = filteredSorted.findIndex((i) => i.id === item.id);
      if (anchorIdx !== -1 && clickIdx !== -1) {
        const [lo, hi] = anchorIdx < clickIdx ? [anchorIdx, clickIdx] : [clickIdx, anchorIdx];
        const rangeIds = filteredSorted.slice(lo, hi + 1).map((i) => i.id);
        setSelectedIds((prev) => {
          const next = new Set(prev);
          for (const id of rangeIds) next.add(id);
          return next;
        });
      }
      return;
    }

    if (opts.ctrl) {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        if (next.has(item.id)) {
          next.delete(item.id);
        } else {
          next.add(item.id);
          lastSelectedIdRef.current = item.id;
        }
        return next;
      });
      return;
    }

    // Plain click — single select
    lastSelectedIdRef.current = item.id;
    setSelectedIds(new Set([item.id]));
    if (infoPanelItem !== null) {
      openInfo(item);
    }
  }

  const handleDrop = useCallback(
    async (draggedId: string, targetFolderId: string) => {
      // If the dragged item is part of the selection, move all selected; otherwise just the dragged one
      const idsToMove = selectedIds.has(draggedId)
        ? [...selectedIds].filter((id) => id !== targetFolderId)
        : [draggedId];

      if (!idsToMove.length) return;

      const results = await Promise.allSettled(
        idsToMove.map((id) => nodesApi.move(id, { target_parent_id: targetFolderId })),
      );

      const failed = results.filter((r) => r.status === "rejected").length;
      setSelectedIds(new Set());
      queryClient.invalidateQueries({ queryKey: folderQueryKey });

      if (failed > 0) {
        toast.error(`Не удалось переместить ${failed} из ${idsToMove.length} элементов`);
      } else {
        toast.success(idsToMove.length === 1 ? "Перемещено" : `Перемещено ${idsToMove.length} элементов`);
      }
    },
    [selectedIds, folderQueryKey, queryClient],
  );

  const filteredItems = applyFilter(data?.items ?? [], filter);
  const singleSelected = selectedItems.length === 1 ? selectedItems[0] : null;

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
      <div className="flex items-center justify-between gap-3">
        <h1 className="min-w-0 flex-1 truncate text-lg font-semibold">
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
            variant="outline"
            onClick={() => folderInputRef.current?.click()}
            disabled={!parentNodeId}
            title={!parentNodeId ? "Перейдите в папку для загрузки" : undefined}
          >
            <FolderUp className="mr-2 h-4 w-4" />
            Папку
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

          {/* Hidden file inputs */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={handleInputChange}
          />
          <input
            ref={folderInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={handleFolderInputChange}
          />
        </div>
      </div>

      {/* Filter bar or action bar */}
      {selectedItems.length > 1 ? (
        <FileMultiActionBar
          items={selectedItems}
          folderQueryKey={folderQueryKey}
          onDeselect={() => setSelectedIds(new Set())}
        />
      ) : singleSelected ? (
        <FileActionBar
          item={singleSelected}
          folderQueryKey={folderQueryKey}
          onDeselect={() => setSelectedIds(new Set())}
        />
      ) : (
        <FileFilterBar active={filter} onChange={setFilter} />
      )}

      {/* Workspace context menu wraps the drop zone */}
      <ContextMenu>
        <ContextMenuTrigger asChild>
          <div className="flex-1 overflow-y-auto rounded-lg">
            <DropZone onDrop={handleFiles} disabled={!parentNodeId}>
              <FileGrid
                items={filteredItems}
                isLoading={isLoading}
                folderQueryKey={folderQueryKey}
                view={view}
                selectedIds={selectedIds}
                onSelectItem={handleSelectItem}
                onDeselect={() => setSelectedIds(new Set())}
                onDrop={handleDrop}
              />
            </DropZone>
          </div>
        </ContextMenuTrigger>
        <ContextMenuContent className="w-52">
          <ContextMenuItem onClick={() => setCreateOpen(true)}>
            <FolderPlus />
            Создать папку
          </ContextMenuItem>
          <ContextMenuSeparator />
          <ContextMenuItem
            disabled={!parentNodeId}
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload />
            Загрузить файлы
          </ContextMenuItem>
          <ContextMenuItem
            disabled={!parentNodeId}
            onClick={() => folderInputRef.current?.click()}
          >
            <FolderUp />
            Загрузить папку
          </ContextMenuItem>
        </ContextMenuContent>
      </ContextMenu>

      <CreateFolderDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        parentNodeId={parentNodeId}
        currentNodeId={nodeId ?? null}
      />
    </div>
  );
}
