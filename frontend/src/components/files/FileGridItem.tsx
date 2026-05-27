import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Download, MoreVertical, Pencil, Share2, Trash2 } from "lucide-react";
import { FileIcon } from "./FileIcon";
import { RenameDialog } from "./RenameDialog";
import { DeleteConfirmDialog } from "./DeleteConfirmDialog";
import { ShareDialog } from "./ShareDialog";
import { formatBytes } from "@/hooks/useQuota";
import { nodesApi } from "@/api/nodes";
import type { NodeListItem } from "@/types/nodes";
import { cn } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";

interface Props {
  item: NodeListItem;
  mimeType?: string | null;
  sizeBytes?: number | null;
  folderQueryKey: unknown[];
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

async function triggerDownload(nodeId: string, filename: string) {
  const resp = await nodesApi.download(nodeId);
  const url = resp.url ?? resp.download_url;
  if (!url) return;
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.target = "_blank";
  a.rel = "noopener noreferrer";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

export function FileGridItem({ item, mimeType, sizeBytes, folderQueryKey }: Props) {
  const navigate = useNavigate();
  const [renameOpen, setRenameOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  function handleCardClick() {
    if (item.node_type === "folder") {
      navigate(`/files/folders/${item.id}`);
    }
  }

  return (
    <>
      <div
        className={cn(
          "group relative flex flex-col items-center gap-2 rounded-xl bg-card p-4 text-center",
          "transition-all duration-150 hover:bg-accent hover:shadow-md",
          item.node_type === "folder" && "cursor-pointer",
        )}
        onClick={handleCardClick}
        role={item.node_type === "folder" ? "button" : undefined}
        tabIndex={item.node_type === "folder" ? 0 : undefined}
        onKeyDown={(e) => {
          if (item.node_type === "folder" && (e.key === "Enter" || e.key === " ")) {
            handleCardClick();
          }
        }}
      >
        <FileIcon nodeType={item.node_type} mimeType={mimeType} className="h-10 w-10" />

        <span className="w-full truncate text-xs font-medium leading-tight" title={item.name}>
          {item.name}
        </span>

        <span className="text-[10px] text-muted-foreground">
          {item.node_type === "file" && sizeBytes != null
            ? formatBytes(sizeBytes)
            : formatDate(item.updated_at)}
        </span>

        {/* Actions button — visible on hover or when menu open */}
        <div
          className={cn(
            "absolute right-1 top-1 transition-opacity",
            menuOpen ? "opacity-100" : "opacity-0 group-hover:opacity-100",
          )}
          onClick={(e) => e.stopPropagation()}
        >
          <DropdownMenu open={menuOpen} onOpenChange={setMenuOpen}>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-6 w-6">
                <MoreVertical className="h-3.5 w-3.5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-40">
              {item.node_type === "file" && (
                <>
                  <DropdownMenuItem
                    onClick={() => triggerDownload(item.id, item.name)}
                  >
                    <Download className="mr-2 h-4 w-4" />
                    Скачать
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                </>
              )}
              <DropdownMenuItem onClick={() => setRenameOpen(true)}>
                <Pencil className="mr-2 h-4 w-4" />
                Переименовать
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setShareOpen(true)}>
                <Share2 className="mr-2 h-4 w-4" />
                Поделиться
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
        </div>
      </div>

      <RenameDialog
        open={renameOpen}
        onOpenChange={setRenameOpen}
        nodeId={item.id}
        currentName={item.name}
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
    </>
  );
}
