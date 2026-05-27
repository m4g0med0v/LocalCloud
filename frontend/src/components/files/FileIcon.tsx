import {
  Folder,
  File,
  FileImage,
  FileVideo,
  FileAudio,
  FileText,
  FileArchive,
  FileCode,
  FileSpreadsheet,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  nodeType: "file" | "folder";
  mimeType?: string | null;
  className?: string;
  color?: string | null;
}

function iconForMime(mime: string): LucideIcon {
  if (mime.startsWith("image/")) return FileImage;
  if (mime.startsWith("video/")) return FileVideo;
  if (mime.startsWith("audio/")) return FileAudio;
  if (mime.startsWith("text/")) return FileText;
  if (mime === "application/pdf") return FileText;
  if (
    mime === "application/zip" ||
    mime === "application/x-rar-compressed" ||
    mime === "application/x-7z-compressed" ||
    mime === "application/gzip"
  )
    return FileArchive;
  if (
    mime === "application/vnd.ms-excel" ||
    mime === "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
  )
    return FileSpreadsheet;
  if (
    mime === "application/json" ||
    mime === "application/xml" ||
    mime.includes("javascript") ||
    mime.includes("typescript")
  )
    return FileCode;
  return File;
}

export function FileIcon({ nodeType, mimeType, className, color }: Props) {
  const cls = cn("shrink-0", className);
  if (nodeType === "folder") {
    return (
      <Folder
        className={cn(cls, !color && "text-yellow-500")}
        style={color ? { color } : undefined}
      />
    );
  }
  const Icon = mimeType ? iconForMime(mimeType) : File;
  return <Icon className={cn(cls, "text-muted-foreground")} />;
}
