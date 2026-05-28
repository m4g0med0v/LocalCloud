import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Users,
  Download,
  FolderOpen,
  MoreVertical,
  Pencil,
  FolderInput,
  Share2,
  Trash2,
  Loader2,
  Info,
} from "lucide-react";
import { toast } from "sonner";
import { permissionsApi } from "@/api/permissions";
import { nodesApi } from "@/api/nodes";
import { useBreadcrumb } from "@/contexts/breadcrumb";
import { FileIcon } from "@/components/files/FileIcon";
import { RenameDialog } from "@/components/files/RenameDialog";
import { DeleteConfirmDialog } from "@/components/files/DeleteConfirmDialog";
import { ShareDialog } from "@/components/files/ShareDialog";
import { MoveDialog } from "@/components/files/MoveDialog";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { formatBytes } from "@/hooks/useQuota";
import { useFolderDownload } from "@/hooks/useFolderDownload";
import { useInfoPanel } from "@/contexts/infoPanel";
import type { SharedWithMeItem } from "@/types/permissions";
import type { NodeListItem } from "@/types/nodes";

const QUERY_KEY = ["shared-with-me"];

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

interface RowProps {
  item: SharedWithMeItem;
}

function SharedRow({ item }: RowProps) {
  const navigate = useNavigate();
  const { downloadFolder, downloading } = useFolderDownload();
  const { openInfo } = useInfoPanel();
  const [menuOpen, setMenuOpen] = useState(false);
  const [renameOpen, setRenameOpen] = useState(false);
  const [moveOpen, setMoveOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);

  const isDownloadingThis = downloading === item.node_id;

  async function handleDownloadFile() {
    try {
      const resp = await nodesApi.download(item.node_id);
      const a = document.createElement("a");
      a.href = resp.presigned_url;
      a.download = resp.filename ?? item.node_name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch {
      toast.error("Не удалось скачать файл");
    }
  }

  function handleDownload() {
    if (item.node_type === "folder") {
      downloadFolder(item.node_id, item.node_name);
    } else {
      handleDownloadFile();
    }
  }

  function handleOpen() {
    navigate(`/files/folders/${item.node_id}`);
  }

  // Stub NodeListItem for useInfoPanel (it only needs basic fields)
  const nodeStub: NodeListItem = {
    id: item.node_id,
    name: item.node_name,
    node_type: item.node_type,
    owner_id: "",
    parent_id: null,
    visibility: "private",
    path: item.node_path,
    depth: 0,
    created_at: item.created_at,
    updated_at: item.updated_at,
    is_deleted: false,
    file_size_bytes: item.file_size_bytes ?? null,
    file_mime_type: item.file_mime_type ?? null,
  };

  const ownerLabel = item.owner_username ? `@${item.owner_username}` : null;
  const updaterLabel = item.updated_by_username ? `@${item.updated_by_username}` : null;

  return (
    <>
      <ContextMenu>
        <ContextMenuTrigger asChild>
          <div className="group flex items-center gap-3 rounded-lg border px-4 py-3 hover:bg-muted/40">
            <FileIcon
              nodeType={item.node_type}
              mimeType={item.file_mime_type}
              className="h-5 w-5 shrink-0"
            />

            <div className="flex min-w-0 flex-1 flex-col">
              <span
                className="truncate text-sm font-medium cursor-pointer hover:underline"
                onClick={() => item.node_type === "folder" && handleOpen()}
                onDoubleClick={() => item.node_type === "file" && item.can_download && handleDownload()}
              >
                {item.node_name}
              </span>
              <span className="truncate text-xs text-muted-foreground">
                {item.node_path}
                {ownerLabel && <span className="ml-1.5 text-muted-foreground/60">· {ownerLabel}</span>}
              </span>
            </div>

            {item.file_size_bytes != null && (
              <span className="shrink-0 text-xs text-muted-foreground">
                {formatBytes(item.file_size_bytes)}
              </span>
            )}

            {updaterLabel && (
              <span className="hidden shrink-0 text-xs text-muted-foreground md:block" title="Последний изменил">
                {updaterLabel}
              </span>
            )}

            <span className="shrink-0 text-xs text-muted-foreground">
              {formatDate(item.updated_at)}
            </span>

            {/* More options button */}
            <div onClick={(e) => e.stopPropagation()}>
              <DropdownMenu open={menuOpen} onOpenChange={(o) => { setMenuOpen(o); }}>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 shrink-0 opacity-0 group-hover:opacity-100 data-[state=open]:opacity-100"
                  >
                    <MoreVertical className="h-3.5 w-3.5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-44">
                  {item.node_type === "folder" && (
                    <DropdownMenuItem onClick={handleOpen}>
                      <FolderOpen className="mr-2 h-4 w-4" />
                      Открыть
                    </DropdownMenuItem>
                  )}
                  {item.can_download && (
                    <>
                      {item.node_type === "folder" && <DropdownMenuSeparator />}
                      <DropdownMenuItem disabled={isDownloadingThis} onClick={handleDownload}>
                        {isDownloadingThis
                          ? <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          : <Download className="mr-2 h-4 w-4" />}
                        Скачать
                      </DropdownMenuItem>
                    </>
                  )}
                  {item.can_write && (
                    <>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem onClick={() => setRenameOpen(true)}>
                        <Pencil className="mr-2 h-4 w-4" />
                        Переименовать
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => setMoveOpen(true)}>
                        <FolderInput className="mr-2 h-4 w-4" />
                        Переместить
                      </DropdownMenuItem>
                    </>
                  )}
                  {item.can_share && (
                    <DropdownMenuItem onClick={() => setShareOpen(true)}>
                      <Share2 className="mr-2 h-4 w-4" />
                      Поделиться
                    </DropdownMenuItem>
                  )}
                  <DropdownMenuItem onClick={() => openInfo(nodeStub)}>
                    <Info className="mr-2 h-4 w-4" />
                    Информация
                  </DropdownMenuItem>
                  {item.can_delete && (
                    <>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        onClick={() => setDeleteOpen(true)}
                        className="text-destructive focus:text-destructive"
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Удалить
                      </DropdownMenuItem>
                    </>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </ContextMenuTrigger>

        <ContextMenuContent className="w-48">
          {item.node_type === "folder" && (
            <>
              <ContextMenuItem onClick={handleOpen}>
                <FolderOpen />
                Открыть
              </ContextMenuItem>
              <ContextMenuSeparator />
            </>
          )}
          {item.can_download && (
            <ContextMenuItem disabled={isDownloadingThis} onClick={handleDownload}>
              {isDownloadingThis ? <Loader2 className="animate-spin" /> : <Download />}
              Скачать
            </ContextMenuItem>
          )}
          {item.can_write && (
            <>
              <ContextMenuSeparator />
              <ContextMenuItem onClick={() => setRenameOpen(true)}>
                <Pencil />
                Переименовать
              </ContextMenuItem>
              <ContextMenuItem onClick={() => setMoveOpen(true)}>
                <FolderInput />
                Переместить
              </ContextMenuItem>
            </>
          )}
          {item.can_share && (
            <ContextMenuItem onClick={() => setShareOpen(true)}>
              <Share2 />
              Поделиться
            </ContextMenuItem>
          )}
          <ContextMenuItem onClick={() => openInfo(nodeStub)}>
            <Info />
            Информация
          </ContextMenuItem>
          {item.can_delete && (
            <>
              <ContextMenuSeparator />
              <ContextMenuItem
                onClick={() => setDeleteOpen(true)}
                className="text-destructive focus:text-destructive"
              >
                <Trash2 />
                Удалить
              </ContextMenuItem>
            </>
          )}
        </ContextMenuContent>
      </ContextMenu>

      {item.can_write && (
        <>
          <RenameDialog
            open={renameOpen}
            onOpenChange={setRenameOpen}
            nodeId={item.node_id}
            currentName={item.node_name}
            folderQueryKey={QUERY_KEY}
          />
          <MoveDialog
            open={moveOpen}
            onOpenChange={setMoveOpen}
            nodeId={item.node_id}
            nodeName={item.node_name}
            folderQueryKey={QUERY_KEY}
          />
        </>
      )}
      {item.can_share && (
        <ShareDialog
          open={shareOpen}
          onOpenChange={setShareOpen}
          nodeId={item.node_id}
          nodeName={item.node_name}
          nodeType={item.node_type}
        />
      )}
      {item.can_delete && (
        <DeleteConfirmDialog
          open={deleteOpen}
          onOpenChange={setDeleteOpen}
          nodeId={item.node_id}
          name={item.node_name}
          folderQueryKey={QUERY_KEY}
        />
      )}
    </>
  );
}

export function SharedWithMePage() {
  const { setCrumbs } = useBreadcrumb();

  useEffect(() => {
    setCrumbs([{ label: "Доступно мне" }]);
  }, [setCrumbs]);

  const { data, isLoading } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: () => permissionsApi.listSharedWithMe({ limit: 200 }),
    staleTime: 30_000,
  });

  const items = data?.items ?? [];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Доступно мне</h1>
        {!isLoading && (
          <span className="text-sm text-muted-foreground">{items.length} элем.</span>
        )}
      </div>

      {isLoading ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-14 rounded-lg" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 py-20 text-muted-foreground">
          <Users className="h-12 w-12 opacity-30" />
          <p className="text-sm">Пока никто не поделился с вами файлами</p>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {items.map((item) => (
            <SharedRow key={item.permission_id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
