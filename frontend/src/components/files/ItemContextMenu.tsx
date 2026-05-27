import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Download,
  FolderInput,
  FolderOpen,
  Info,
  Loader2,
  Palette,
  Pencil,
  Share2,
  Trash2,
} from "lucide-react";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { RenameDialog } from "./RenameDialog";
import { DeleteConfirmDialog } from "./DeleteConfirmDialog";
import { ShareDialog } from "./ShareDialog";
import { FolderColorDialog } from "./FolderColorDialog";
import { MoveDialog } from "./MoveDialog";
import { useFolderDownload } from "@/hooks/useFolderDownload";
import { useInfoPanel } from "@/contexts/infoPanel";
import { nodesApi } from "@/api/nodes";
import type { NodeListItem } from "@/types/nodes";
import type { SelectOpts } from "./FileGrid";
import type { ReactNode } from "react";

async function triggerDownload(nodeId: string, filename: string) {
  const resp = await nodesApi.download(nodeId);
  const a = document.createElement("a");
  a.href = resp.presigned_url;
  a.download = resp.filename ?? filename;
  a.target = "_blank";
  a.rel = "noopener noreferrer";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

interface Props {
  item: NodeListItem;
  folderQueryKey: unknown[];
  folderColor: string | null;
  onColorChange: (color: string | null) => void;
  isSelected?: boolean;
  onSelect?: (item: NodeListItem, opts: SelectOpts) => void;
  children: ReactNode;
}

export function ItemContextMenu({
  item,
  folderQueryKey,
  folderColor,
  onColorChange,
  isSelected,
  onSelect,
  children,
}: Props) {
  const navigate = useNavigate();
  const { openInfo } = useInfoPanel();
  const { downloadFolder, downloading } = useFolderDownload();
  const isFolderDownloading = downloading === item.id;

  const [renameOpen, setRenameOpen] = useState(false);
  const [moveOpen, setMoveOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  const [colorOpen, setColorOpen] = useState(false);

  function handleDownload() {
    if (item.node_type === "folder") {
      downloadFolder(item.id, item.name);
    } else {
      triggerDownload(item.id, item.name);
    }
  }

  return (
    <>
      <ContextMenu onOpenChange={(open) => { if (open && !isSelected) onSelect?.(item, { ctrl: false, shift: false }); }}>
        <ContextMenuTrigger asChild>{children}</ContextMenuTrigger>
        <ContextMenuContent className="w-48">
          {item.node_type === "folder" && (
            <>
              <ContextMenuItem onClick={() => navigate(`/files/folders/${item.id}`)}>
                <FolderOpen />
                Открыть
              </ContextMenuItem>
              <ContextMenuSeparator />
            </>
          )}

          <ContextMenuItem disabled={isFolderDownloading} onClick={handleDownload}>
            {isFolderDownloading ? (
              <Loader2 className="animate-spin" />
            ) : (
              <Download />
            )}
            Скачать
          </ContextMenuItem>

          <ContextMenuSeparator />

          <ContextMenuItem onClick={() => setRenameOpen(true)}>
            <Pencil />
            Переименовать
          </ContextMenuItem>

          <ContextMenuItem onClick={() => setMoveOpen(true)}>
            <FolderInput />
            Переместить
          </ContextMenuItem>

          {item.node_type === "folder" && (
            <ContextMenuItem onClick={() => setColorOpen(true)}>
              <Palette />
              Цвет папки
            </ContextMenuItem>
          )}

          <ContextMenuItem onClick={() => setShareOpen(true)}>
            <Share2 />
            Поделиться
          </ContextMenuItem>

          <ContextMenuItem onClick={() => openInfo(item)}>
            <Info />
            Информация
          </ContextMenuItem>

          <ContextMenuSeparator />

          <ContextMenuItem
            onClick={() => setDeleteOpen(true)}
            className="text-destructive focus:text-destructive"
          >
            <Trash2 />
            Удалить
          </ContextMenuItem>
        </ContextMenuContent>
      </ContextMenu>

      <RenameDialog
        open={renameOpen}
        onOpenChange={setRenameOpen}
        nodeId={item.id}
        currentName={item.name}
        folderQueryKey={folderQueryKey}
      />
      <MoveDialog
        open={moveOpen}
        onOpenChange={setMoveOpen}
        nodeId={item.id}
        nodeName={item.name}
        folderQueryKey={folderQueryKey}
      />
      <DeleteConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        nodeId={item.id}
        name={item.name}
        folderQueryKey={folderQueryKey}
      />
      <ShareDialog
        open={shareOpen}
        onOpenChange={setShareOpen}
        nodeId={item.id}
        nodeName={item.name}
        nodeType={item.node_type}
      />
      {item.node_type === "folder" && (
        <FolderColorDialog
          open={colorOpen}
          onOpenChange={setColorOpen}
          nodeId={item.id}
          currentColor={folderColor}
          onColorChange={onColorChange}
        />
      )}
    </>
  );
}
