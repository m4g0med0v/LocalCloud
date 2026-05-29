import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  Download,
  FolderInput,
  FolderOpen,
  Info,
  Loader2,
  MoreHorizontal,
  Palette,
  Pencil,
  Share2,
  Trash2,
  X,
} from "lucide-react";
import { FileIcon } from "./FileIcon";
import { RenameDialog } from "./RenameDialog";
import { DeleteConfirmDialog } from "./DeleteConfirmDialog";
import { ShareDialog } from "./ShareDialog";
import { FolderColorDialog, getFolderColor } from "./FolderColorDialog";
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
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

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
  onDeselect: () => void;
}

export function FileActionBar({ item, folderQueryKey, onDeselect }: Props) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { openInfo } = useInfoPanel();
  const { downloadFolder, downloading } = useFolderDownload();
  const isFolderDownloading = downloading === item.id;
  const [colorVersion, setColorVersion] = useState(0);
  const folderColor = item.node_type === "folder" ? getFolderColor(item.id) : null;

  const [renameOpen, setRenameOpen] = useState(false);
  const [moveOpen, setMoveOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  const [colorOpen, setColorOpen] = useState(false);
  const [isFileDownloading, setIsFileDownloading] = useState(false);

  async function handleDownload() {
    if (item.node_type === "folder") {
      downloadFolder(item.id, item.name);
    } else {
      setIsFileDownloading(true);
      try {
        await triggerDownload(item.id, item.name);
      } finally {
        setIsFileDownloading(false);
      }
    }
  }

  const overflowItems = [
    <DropdownMenuItem key="move" onClick={() => setMoveOpen(true)}>
      <FolderInput className="mr-2 h-4 w-4" />
      Переместить
    </DropdownMenuItem>,
    <DropdownMenuItem key="share" onClick={() => setShareOpen(true)}>
      <Share2 className="mr-2 h-4 w-4" />
      Поделиться
    </DropdownMenuItem>,
    ...(item.node_type === "folder"
      ? [
          <DropdownMenuItem key="color" onClick={() => setColorOpen(true)}>
            <Palette className="mr-2 h-4 w-4" />
            Цвет папки
          </DropdownMenuItem>,
        ]
      : []),
  ];

  return (
    <>
      <div className="flex items-center gap-1 rounded-lg border bg-card px-2 py-1.5">
        {/* Deselect */}
        <Button variant="ghost" size="icon" className="h-6 w-6 shrink-0" onClick={onDeselect}>
          <X className="h-3.5 w-3.5" />
        </Button>

        {/* Item identity */}
        <FileIcon
          nodeType={item.node_type}
          mimeType={item.file_mime_type}
          className="mx-1 h-4 w-4 shrink-0"
          color={folderColor}
        />
        <span className="min-w-0 flex-1 truncate text-sm font-medium">{item.name}</span>

        {/* Overflow → left of primary actions */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-7 w-7 shrink-0">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-40">
            {overflowItems}
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Primary action icons */}
        <div className="flex shrink-0 items-center">
          {item.node_type === "folder" && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={() => navigate(`/files/folders/${item.id}`)}
                >
                  <FolderOpen className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Открыть</TooltipContent>
            </Tooltip>
          )}

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                disabled={isFolderDownloading || isFileDownloading}
                onClick={handleDownload}
              >
                {isFolderDownloading || isFileDownloading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Download className="h-4 w-4" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent>Скачать</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => setRenameOpen(true)}
              >
                <Pencil className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Переименовать</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => openInfo(item)}
              >
                <Info className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Информация</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-destructive hover:bg-destructive/10 hover:text-destructive"
                onClick={() => setDeleteOpen(true)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Удалить</TooltipContent>
          </Tooltip>
        </div>
      </div>

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
          onColorChange={() => {
            setColorVersion((v) => v + 1);
            queryClient.invalidateQueries({ queryKey: folderQueryKey });
          }}
        />
      )}
    </>
  );
}
