import { useState } from "react";
import { Download, Eye, FolderInput, Info, Loader2, MoreVertical, Palette, Pencil, Share2, Trash2 } from "lucide-react";
import { detectPreviewKind } from "@/components/preview/FilePreviewModal";
import { RenameDialog } from "./RenameDialog";
import { DeleteConfirmDialog } from "./DeleteConfirmDialog";
import { ShareDialog } from "./ShareDialog";
import { FolderColorDialog } from "./FolderColorDialog";
import { MoveDialog } from "./MoveDialog";
import { useFolderDownload } from "@/hooks/useFolderDownload";
import { useInfoPanel } from "@/contexts/infoPanel";
import { nodesApi } from "@/api/nodes";
import type { NodeListItem } from "@/types/nodes";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

async function triggerDownload(nodeId: string, filename: string) {
  const resp = await nodesApi.download(nodeId);
  const a = document.createElement("a");
  a.href = resp.presigned_url;
  a.download = resp.filename ?? filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

interface Props {
  item: NodeListItem;
  folderQueryKey: unknown[];
  folderColor: string | null;
  onColorChange: (color: string | null) => void;
  onOpenChange?: (open: boolean) => void;
  onPreview?: () => void;
}

export function ItemActions({ item, folderQueryKey, folderColor, onColorChange, onOpenChange, onPreview }: Props) {
  const { downloadFolder, downloading } = useFolderDownload();
  const { openInfo } = useInfoPanel();
  const isFolderDownloading = downloading === item.id;
  const previewKind = item.node_type === "file" ? detectPreviewKind(item.name, item.file_mime_type) : null;
  const [menuOpen, setMenuOpen] = useState(false);
  const [renameOpen, setRenameOpen] = useState(false);
  const [moveOpen, setMoveOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  const [colorOpen, setColorOpen] = useState(false);

  function handleMenuOpenChange(open: boolean) {
    setMenuOpen(open);
    onOpenChange?.(open);
  }

  return (
    <>
      <DropdownMenu open={menuOpen} onOpenChange={handleMenuOpenChange}>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" className="h-6 w-6 shrink-0">
            <MoreVertical className="h-3.5 w-3.5" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-40">
          {item.node_type === "file" && (
            <>
              {previewKind && onPreview && (
                <DropdownMenuItem onClick={onPreview}>
                  <Eye className="mr-2 h-4 w-4" />
                  Просмотр
                </DropdownMenuItem>
              )}
              <DropdownMenuItem onClick={() => triggerDownload(item.id, item.name)}>
                <Download className="mr-2 h-4 w-4" />
                Скачать
              </DropdownMenuItem>
              <DropdownMenuSeparator />
            </>
          )}
          {item.node_type === "folder" && (
            <>
              <DropdownMenuItem
                disabled={isFolderDownloading}
                onClick={() => downloadFolder(item.id, item.name)}
              >
                {isFolderDownloading
                  ? <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  : <Download className="mr-2 h-4 w-4" />}
                Скачать
              </DropdownMenuItem>
              <DropdownMenuSeparator />
            </>
          )}
          <DropdownMenuItem onClick={() => setRenameOpen(true)}>
            <Pencil className="mr-2 h-4 w-4" />
            Переименовать
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => setMoveOpen(true)}>
            <FolderInput className="mr-2 h-4 w-4" />
            Переместить
          </DropdownMenuItem>
          {item.node_type === "folder" && (
            <DropdownMenuItem onClick={() => setColorOpen(true)}>
              <Palette className="mr-2 h-4 w-4" />
              Цвет папки
            </DropdownMenuItem>
          )}
          <DropdownMenuItem onClick={() => setShareOpen(true)}>
            <Share2 className="mr-2 h-4 w-4" />
            Поделиться
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => openInfo(item)}>
            <Info className="mr-2 h-4 w-4" />
            Информация
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onClick={() => setDeleteOpen(true)}
            className="text-destructive focus:text-destructive"
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Удалить
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

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
        items={[item]}
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
