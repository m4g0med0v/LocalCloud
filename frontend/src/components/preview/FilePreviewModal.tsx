import { useEffect, useRef, useState } from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  AlertCircle,
  Check,
  Download,
  ExternalLink,
  Loader2,
  Maximize2,
  Minimize2,
  Minus,
  Music,
  Pause,
  Pencil,
  Play,
  Plus,
  Volume2,
  VolumeX,
  X,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { nodesApi } from "@/api/nodes";
import { uploadsApi } from "@/api/uploads";
import type { NodeListItem } from "@/types/nodes";

export type PreviewKind = "image" | "video" | "audio" | "pdf" | "text" | "markdown";

// Extensions whose content is always human-readable text.
// For extension-less files (Dockerfile, Makefile, …) name.split(".").pop()
// returns the full lowercased filename, which is also matched here.
const TEXT_EXTENSIONS = new Set([
  // Plain text / docs
  "txt", "log", "rst", "adoc", "tex", "csv", "tsv", "diff", "patch", "ics", "vcf",
  // Web
  "html", "htm", "css", "scss", "sass", "less",
  // Data & config
  "json", "jsonc", "json5", "yaml", "yml", "toml", "ini", "cfg", "conf",
  "properties", "env", "lock", "plist",
  // XML family
  "xml", "xsl", "xslt", "rss", "atom",
  // Shells
  "sh", "bash", "zsh", "fish", "ps1", "bat", "cmd",
  // JavaScript / TypeScript
  "js", "mjs", "cjs", "ts", "jsx", "tsx",
  // Web frameworks
  "vue", "svelte", "astro",
  // Python
  "py", "pyw", "pyi",
  // Ruby
  "rb", "rake", "gemspec", "gemfile", "rakefile",
  // Go
  "go",
  // Rust
  "rs",
  // JVM
  "java", "kt", "kts", "groovy", "scala",
  // C family
  "c", "h", "cpp", "cc", "cxx", "hpp", "hxx", "cs",
  // Other languages
  "php", "swift", "dart", "lua", "r", "jl",
  "ex", "exs", "hs", "elm", "clj", "cljs",
  "ml", "mli", "fs", "fsx", "fsi", "pl", "pm",
  // Query / schema
  "sql", "psql", "graphql", "gql",
  // DevOps / build
  "dockerfile", "makefile", "vagrantfile", "procfile", "brewfile", "jenkinsfile",
  "cmake", "tf", "tfvars", "hcl", "gradle", "bazel", "bzl",
  // Dotfiles (ext = name after the last dot, or full name when no dot)
  "gitignore", "gitattributes", "gitmodules",
  "npmignore", "dockerignore", "editorconfig",
  "eslintrc", "prettierrc", "babelrc", "stylelintrc",
  "huskyrc", "lintstagedrc",
]);

// application/* MIME types whose payload is plaintext.
const TEXT_APP_MIME = new Set([
  "application/json", "application/ld+json", "application/manifest+json",
  "application/geo+json", "application/xml", "application/xhtml+xml",
  "application/atom+xml", "application/rss+xml",
  "application/javascript", "application/ecmascript",
  "application/typescript", "application/x-yaml",
  "application/x-sh", "application/x-httpd-php",
  "application/sql", "application/graphql",
]);

export function detectPreviewKind(name: string, mimeType?: string | null): PreviewKind | null {
  const ext = name.split(".").pop()?.toLowerCase() ?? "";

  // If the extension is a known text format, skip MIME-type-based binary detection.
  // This resolves ambiguous extensions like .ts (TypeScript vs MPEG-TS / video/mp2t).
  const knownTextExt = TEXT_EXTENSIONS.has(ext);

  if (!knownTextExt) {
    if (mimeType?.startsWith("image/")) return "image";
    if (mimeType?.startsWith("video/")) return "video";
    if (mimeType?.startsWith("audio/")) return "audio";
    if (mimeType === "application/pdf") return "pdf";
  }

  // Extension-based checks are always authoritative for these specific formats.
  if (["jpg","jpeg","png","gif","webp","svg","bmp","ico"].includes(ext)) return "image";
  if (["mp4","webm","ogv","mov","mkv"].includes(ext)) return "video";
  if (["mp3","wav","ogg","flac","aac","m4a","opus"].includes(ext)) return "audio";
  if (ext === "pdf") return "pdf";
  if (["md","mdx","markdown"].includes(ext) || mimeType === "text/markdown" || mimeType === "text/x-markdown") return "markdown";

  const isTextMime = !!mimeType && (mimeType.startsWith("text/") || TEXT_APP_MIME.has(mimeType));
  if (knownTextExt || isTextMime) return "text";

  return null;
}

function formatTime(s: number) {
  if (!isFinite(s) || s < 0) return "--:--";
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

// ── Shared primitives ─────────────────────────────────────────────────────────

function TrackBar({ value, max, step = 0.1, fillClass = "bg-primary", onChange }: {
  value: number; max: number; step?: number; fillClass?: string; onChange: (v: number) => void;
}) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-border">
      <div className={cn("absolute inset-y-0 left-0 rounded-full", fillClass)} style={{ width: `${pct}%` }} />
      <input
        type="range" min={0} max={max || 1} step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
      />
    </div>
  );
}

function SeekRow({ currentTime, duration, onSeek }: {
  currentTime: number; duration: number; onSeek: (t: number) => void;
}) {
  return (
    <div className="space-y-1.5">
      <TrackBar value={currentTime} max={duration} step={0.1} onChange={onSeek} />
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{formatTime(currentTime)}</span>
        <span>{formatTime(duration)}</span>
      </div>
    </div>
  );
}

function PlaybackButtons({ playing, onToggle, onSeek }: {
  playing: boolean; onToggle: () => void; onSeek: (delta: number) => void;
}) {
  return (
    <div className="flex items-center justify-center gap-4">
      <button onClick={() => onSeek(-10)} className="flex h-8 w-8 flex-col items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-accent hover:text-foreground">
        <span className="text-[10px] font-bold leading-none">−10</span>
        <span className="text-[8px] leading-none opacity-60">с</span>
      </button>
      <button onClick={onToggle} className="flex h-11 w-11 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-md transition-opacity hover:opacity-90">
        {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4 translate-x-px" />}
      </button>
      <button onClick={() => onSeek(10)} className="flex h-8 w-8 flex-col items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-accent hover:text-foreground">
        <span className="text-[10px] font-bold leading-none">+10</span>
        <span className="text-[8px] leading-none opacity-60">с</span>
      </button>
    </div>
  );
}

function VolumeRow({ volume, muted, onVolumeChange, onToggleMute, extra }: {
  volume: number; muted: boolean; onVolumeChange: (v: number) => void;
  onToggleMute: () => void; extra?: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-2">
      <button onClick={onToggleMute} className="shrink-0 text-muted-foreground transition-colors hover:text-foreground">
        {muted || volume === 0 ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
      </button>
      <TrackBar value={muted ? 0 : volume} max={1} step={0.01} fillClass="bg-muted-foreground/50" onChange={onVolumeChange} />
      {extra}
    </div>
  );
}

// ── Image viewer with zoom / pan ──────────────────────────────────────────────

function ImageViewer({ src, alt }: { src: string; alt: string }) {
  const [zoom, setZoom] = useState(1);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragOrigin = useRef({ x: 0, y: 0, px: 0, py: 0 });

  function applyZoom(next: number) {
    const clamped = Math.round(Math.min(5, Math.max(0.25, next)) * 100) / 100;
    setZoom(clamped);
    if (clamped <= 1) setPos({ x: 0, y: 0 });
  }

  function handleWheel(e: React.WheelEvent) {
    e.preventDefault();
    setZoom((prev) => {
      const next = Math.round(Math.min(5, Math.max(0.25, prev * (e.deltaY < 0 ? 1.1 : 0.9))) * 100) / 100;
      if (next <= 1) setPos({ x: 0, y: 0 });
      return next;
    });
  }

  function handleMouseDown(e: React.MouseEvent) {
    if (zoom <= 1) return;
    e.preventDefault();
    setIsDragging(true);
    dragOrigin.current = { x: e.clientX, y: e.clientY, px: pos.x, py: pos.y };
  }

  function handleMouseMove(e: React.MouseEvent) {
    if (!isDragging) return;
    setPos({ x: dragOrigin.current.px + (e.clientX - dragOrigin.current.x), y: dragOrigin.current.py + (e.clientY - dragOrigin.current.y) });
  }

  return (
    <div
      className="relative flex h-full w-full select-none items-center justify-center overflow-hidden"
      style={{ cursor: isDragging ? "grabbing" : zoom > 1 ? "grab" : "default" }}
      onWheel={handleWheel} onMouseDown={handleMouseDown} onMouseMove={handleMouseMove}
      onMouseUp={() => setIsDragging(false)} onMouseLeave={() => setIsDragging(false)}
    >
      <img src={src} alt={alt} draggable={false} className="max-h-full max-w-full rounded-lg object-contain shadow-2xl"
        style={{ transform: `translate(${pos.x}px, ${pos.y}px) scale(${zoom})`, transition: isDragging ? "none" : "transform 0.12s ease-out" }}
      />
      <div className="absolute bottom-4 left-1/2 flex -translate-x-1/2 items-center gap-0.5 rounded-lg border border-border bg-panel/95 p-1 shadow-lg backdrop-blur-sm">
        <button onClick={() => applyZoom(zoom - 0.25)} className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground">
          <Minus className="h-3.5 w-3.5" />
        </button>
        <button onClick={() => { setZoom(1); setPos({ x: 0, y: 0 }); }} className="min-w-[3.25rem] rounded-md px-1 py-1 text-center text-xs font-medium text-foreground transition-colors hover:bg-accent">
          {Math.round(zoom * 100)}%
        </button>
        <button onClick={() => applyZoom(zoom + 0.25)} className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground">
          <Plus className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

// ── Audio player ──────────────────────────────────────────────────────────────

function AudioPlayer({ src, name }: { src: string; name: string }) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [muted, setMuted] = useState(false);
  const [volume, setVolume] = useState(1);

  function toggle() {
    const a = audioRef.current;
    if (!a) return;
    if (playing) { a.pause(); setPlaying(false); }
    else { a.play().then(() => setPlaying(true)).catch(() => {}); }
  }

  function seek(delta: number) {
    const a = audioRef.current;
    if (!a) return;
    a.currentTime = Math.max(0, Math.min(a.duration || 0, a.currentTime + delta));
  }

  function handleVolume(v: number) {
    setVolume(v);
    if (audioRef.current) audioRef.current.volume = v;
    setMuted(v === 0);
  }

  function toggleMute() {
    const a = audioRef.current;
    if (!a) return;
    const next = !muted;
    a.muted = next;
    setMuted(next);
  }

  return (
    <div className="w-full max-w-xs overflow-hidden rounded-2xl border border-border bg-card shadow-2xl">
      <div className="flex h-36 items-center justify-center bg-muted/30">
        <Music className="h-12 w-12 text-muted-foreground/30" />
      </div>
      <div className="p-5">
        <p className="mb-4 truncate text-sm font-semibold text-foreground" title={name}>{name}</p>
        <div className="mb-4">
          <SeekRow currentTime={currentTime} duration={duration} onSeek={(t) => { if (audioRef.current) audioRef.current.currentTime = t; setCurrentTime(t); }} />
        </div>
        <div className="mb-4">
          <PlaybackButtons playing={playing} onToggle={toggle} onSeek={seek} />
        </div>
        <VolumeRow volume={volume} muted={muted} onVolumeChange={handleVolume} onToggleMute={toggleMute} />
      </div>
      <audio ref={audioRef} src={src}
        onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
        onLoadedMetadata={(e) => setDuration(e.currentTarget.duration)}
        onEnded={() => setPlaying(false)}
      />
    </div>
  );
}

// ── Video player — single JSX tree so <video> is never remounted ──────────────

function VideoPlayer({ src, name, posterUrl }: { src: string; name: string; posterUrl?: string | null }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const hideTimerRef = useRef<ReturnType<typeof setTimeout>>();

  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [muted, setMuted] = useState(false);
  const [volume, setVolume] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showOverlay, setShowOverlay] = useState(true);
  const [videoError, setVideoError] = useState<string | null>(null);

  useEffect(() => { return () => clearTimeout(hideTimerRef.current); }, []);

  useEffect(() => {
    function onFsChange() { setIsFullscreen(!!document.fullscreenElement); }
    document.addEventListener("fullscreenchange", onFsChange);
    return () => document.removeEventListener("fullscreenchange", onFsChange);
  }, []);

  function scheduleHide() {
    clearTimeout(hideTimerRef.current);
    hideTimerRef.current = setTimeout(() => setShowOverlay(false), 2500);
  }

  function toggle() {
    const v = videoRef.current;
    if (!v) return;
    if (playing) { v.pause(); }
    else { v.play().catch(() => {}); scheduleHide(); }
  }

  function seek(delta: number) {
    const v = videoRef.current;
    if (!v) return;
    v.currentTime = Math.max(0, Math.min(v.duration || 0, v.currentTime + delta));
  }

  function handleVolume(val: number) {
    setVolume(val);
    if (videoRef.current) videoRef.current.volume = val;
    setMuted(val === 0);
  }

  function toggleMute() {
    const v = videoRef.current;
    if (!v) return;
    const next = !muted;
    v.muted = next;
    setMuted(next);
  }

  function toggleFullscreen() {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) containerRef.current.requestFullscreen();
    else document.exitFullscreen();
  }

  const fsProgress = duration > 0 ? (currentTime / duration) * 100 : 0;

  // Single return — <video> stays at the same JSX position regardless of isFullscreen,
  // so React never unmounts/remounts it (playback state is preserved).
  return (
    <div
      ref={containerRef}
      className={cn(
        "overflow-hidden",
        isFullscreen
          ? "h-full w-full bg-black"
          : "w-full max-w-md rounded-2xl border border-border bg-card shadow-2xl",
      )}
      onMouseMove={() => { if (isFullscreen) { setShowOverlay(true); if (playing) scheduleHide(); } }}
      onMouseLeave={() => { if (isFullscreen && playing) setShowOverlay(false); }}
    >
      {/* Video area — always rendered at this position in the tree */}
      <div
        className={cn(
          "relative cursor-pointer bg-black",
          isFullscreen ? "h-full w-full" : "aspect-video w-full",
        )}
        onClick={toggle}
      >
        <video
          ref={videoRef}
          src={src}
          poster={posterUrl ?? undefined}
          className="h-full w-full object-contain"
          onPlay={() => setPlaying(true)}
          onPause={() => { setPlaying(false); setShowOverlay(true); clearTimeout(hideTimerRef.current); }}
          onEnded={() => { setPlaying(false); setShowOverlay(true); clearTimeout(hideTimerRef.current); }}
          onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
          onLoadedMetadata={(e) => setDuration(e.currentTarget.duration)}
          onError={(e) => {
            const err = e.currentTarget.error;
            const msg = err?.message ?? "";
            const isCodec = err?.code === 4 || msg.includes("no supported streams") || msg.includes("DEMUXER_ERROR");
            setVideoError(isCodec
              ? "Видеокодек не поддерживается браузером. Скачайте файл и откройте в плеере."
              : "Не удалось воспроизвести видео.");
          }}
        />

        {videoError && (
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-3 bg-black/90">
            <AlertCircle className="h-8 w-8 text-muted-foreground" />
            <span className="px-6 text-center text-xs text-muted-foreground">{videoError}</span>
          </div>
        )}

        {/* Center play button when paused */}
        {!playing && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <div className={cn(
              "flex items-center justify-center rounded-full bg-black/50 text-white backdrop-blur-sm",
              isFullscreen ? "h-16 w-16" : "h-14 w-14",
            )}>
              <Play className={cn("translate-x-0.5", isFullscreen ? "h-7 w-7" : "h-6 w-6")} />
            </div>
          </div>
        )}

        {/* Fullscreen overlay controls */}
        {isFullscreen && (
          <div className={cn(
            "absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent px-5 pb-5 pt-12 transition-opacity duration-300",
            showOverlay ? "opacity-100" : "opacity-0 pointer-events-none",
          )}>
            <div className="mb-3 relative h-1 w-full rounded-full bg-white/25">
              <div className="absolute inset-y-0 left-0 rounded-full bg-primary" style={{ width: `${fsProgress}%` }} />
              <input type="range" min={0} max={duration || 1} step={0.1} value={currentTime}
                onChange={(e) => { const t = Number(e.target.value); if (videoRef.current) videoRef.current.currentTime = t; setCurrentTime(t); }}
                className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
              />
            </div>
            <div className="flex items-center gap-3">
              <button onClick={() => seek(-10)} className="flex h-7 w-7 flex-col items-center justify-center text-white/70 hover:text-white">
                <span className="text-[10px] font-bold leading-none">−10</span>
                <span className="text-[8px] leading-none opacity-60">с</span>
              </button>
              <button onClick={toggle} className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground hover:opacity-90">
                {playing ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5 translate-x-px" />}
              </button>
              <button onClick={() => seek(10)} className="flex h-7 w-7 flex-col items-center justify-center text-white/70 hover:text-white">
                <span className="text-[10px] font-bold leading-none">+10</span>
                <span className="text-[8px] leading-none opacity-60">с</span>
              </button>
              <span className="text-xs tabular-nums text-white/60">{formatTime(currentTime)} / {formatTime(duration)}</span>
              <div className="ml-auto flex items-center gap-2.5">
                <button onClick={toggleMute} className="text-white/70 hover:text-white">
                  {muted || volume === 0 ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
                </button>
                <div className="relative h-1 w-20 rounded-full bg-white/25">
                  <div className="absolute inset-y-0 left-0 rounded-full bg-white/70" style={{ width: `${(muted ? 0 : volume) * 100}%` }} />
                  <input type="range" min={0} max={1} step={0.01} value={muted ? 0 : volume}
                    onChange={(e) => handleVolume(Number(e.target.value))}
                    className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
                  />
                </div>
                <button onClick={toggleFullscreen} className="text-white/70 hover:text-white">
                  <Minimize2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Card controls — only when not fullscreen */}
      {!isFullscreen && (
        <div className="p-5">
          <p className="mb-4 truncate text-sm font-semibold text-foreground" title={name}>{name}</p>
          <div className="mb-4">
            <SeekRow currentTime={currentTime} duration={duration}
              onSeek={(t) => { if (videoRef.current) videoRef.current.currentTime = t; setCurrentTime(t); }}
            />
          </div>
          <div className="mb-4">
            <PlaybackButtons playing={playing} onToggle={toggle} onSeek={seek} />
          </div>
          <VolumeRow
            volume={volume} muted={muted} onVolumeChange={handleVolume} onToggleMute={toggleMute}
            extra={
              <button onClick={toggleFullscreen} className="ml-auto shrink-0 text-muted-foreground transition-colors hover:text-foreground">
                <Maximize2 className="h-4 w-4" />
              </button>
            }
          />
        </div>
      )}
    </div>
  );
}

// ── Main modal ────────────────────────────────────────────────────────────────

interface Props {
  item: NodeListItem;
  mimeType?: string | null;
  open: boolean;
  onClose: () => void;
}

export function FilePreviewModal({ item, mimeType, open, onClose }: Props) {
  const kind = detectPreviewKind(item.name, mimeType ?? item.file_mime_type);
  const queryClient = useQueryClient();

  const [presignedUrl, setPresignedUrl] = useState<string | null>(null);
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [posterUrl, setPosterUrl] = useState<string | null | undefined>(undefined);
  const [pdfLoaded, setPdfLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const blobRef = useRef<string | null>(null);
  const editorRef = useRef<HTMLDivElement>(null);
  const videoStreamUrl = kind === "video" ? nodesApi.streamUrl(item.id) : null;

  // Thumbnail for video / audio
  useEffect(() => {
    if (!open || !kind || kind === "image" || kind === "text" || kind === "markdown" || kind === "pdf") return;
    setPosterUrl(undefined);
    nodesApi.thumbnail(item.id).then((r) => setPosterUrl(r.presigned_url)).catch(() => setPosterUrl(null));
  }, [open, item.id, kind]);

  // Main download URL + PDF blob (video uses same-origin stream URL instead)
  useEffect(() => {
    if (!open || !kind) return;
    if (kind === "video") { setLoading(false); return; }

    setPresignedUrl(null);
    setPdfBlobUrl(null);
    setPdfError(null);
    setTextContent(null);
    setPdfLoaded(false);
    setError(null);
    setLoading(true);

    if (blobRef.current) { URL.revokeObjectURL(blobRef.current); blobRef.current = null; }

    nodesApi
      .download(item.id, false)
      .then(async (resp) => {
        const url = resp.presigned_url;
        setPresignedUrl(url);

        if (kind === "pdf") {
          // Fetch as blob so the browser always treats it as application/pdf,
          // regardless of what Content-Type MinIO returns.
          try {
            const res = await fetch(url);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const blob = await res.blob();
            const blobUrl = URL.createObjectURL(new Blob([blob], { type: "application/pdf" }));
            blobRef.current = blobUrl;
            setPdfBlobUrl(blobUrl);
          } catch {
            // CORS or network error — fall back to direct iframe
            setPdfBlobUrl(url);
          }
        } else if (kind === "text" || kind === "markdown") {
          const text = await fetch(url).then((r) => r.text());
          setTextContent(text);
        }
      })
      .catch((e: Error) => setError(e.message ?? "Не удалось загрузить файл"))
      .finally(() => setLoading(false));

    return () => {
      if (blobRef.current) { URL.revokeObjectURL(blobRef.current); blobRef.current = null; }
    };
  }, [open, item.id, kind]);

  // Reset edit state whenever the modal closes or the item changes
  useEffect(() => {
    if (!open) { setEditing(false); setEditContent(""); setSaveError(null); }
  }, [open, item.id]);

  // Populate the contenteditable editor when edit mode opens
  useEffect(() => {
    if (!editing || !editorRef.current) return;
    editorRef.current.innerText = textContent ?? "";
    editorRef.current.focus();
  }, [editing]);

  if (!kind) return null;

  async function handleSave() {
    if (!item.parent_id) { setSaveError("Невозможно сохранить файл в корне."); return; }
    const content = editorRef.current?.innerText ?? editContent;
    if (!content.length) { setSaveError("Файл не может быть пустым."); return; }
    setSaving(true);
    setSaveError(null);
    try {
      const mType = kind === "markdown" ? "text/markdown" : "text/plain";
      const blob = new Blob([content], { type: mType });

      // Delete the old file first so the name is free for the replacement
      await nodesApi.softDelete(item.id);

      const session = await uploadsApi.create({
        parent_node_id: item.parent_id,
        filename: item.name,
        file_size_bytes: blob.size,
        parts_count: 1,
        mime_type: mType,
        part_size_bytes: blob.size,
      });

      const { parts } = await uploadsApi.getPresignedParts(session.id);
      const part = parts[0];

      const restricted = new Set(["content-length", "host", "connection", "transfer-encoding"]);
      const safeHeaders: Record<string, string> = {};
      for (const [k, v] of Object.entries(part.headers ?? {})) {
        if (!restricted.has(k.toLowerCase())) safeHeaders[k] = v;
      }

      const resp = await fetch(part.url, { method: "PUT", body: blob, headers: safeHeaders });
      if (!resp.ok) throw new Error(`Ошибка загрузки: ${resp.status}`);

      const etag = (resp.headers.get("ETag") ?? resp.headers.get("etag") ?? "").replace(/"/g, "");
      await uploadsApi.completePart(session.id, 1, { part_number: 1, etag, size_bytes: blob.size });
      await uploadsApi.complete(session.id, {
        upload_session_id: session.id,
        parts: [{ part_number: 1, etag, size_bytes: blob.size }],
      });

      queryClient.invalidateQueries({ queryKey: ["nodes"] });
      onClose();
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Не удалось сохранить файл.");
    } finally {
      setSaving(false);
    }
  }

  async function triggerDownload() {
    let url = presignedUrl;
    if (!url) {
      try {
        const resp = await nodesApi.download(item.id, true);
        url = resp.presigned_url;
      } catch { return; }
    }
    const a = document.createElement("a");
    a.href = url;
    a.download = item.name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  return (
    <DialogPrimitive.Root open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/75 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <DialogPrimitive.Content className="fixed inset-0 z-50 flex flex-col focus:outline-none" aria-describedby={undefined}>
          <DialogPrimitive.Title className="sr-only">{item.name}</DialogPrimitive.Title>

          {/* Header */}
          <div className="flex shrink-0 items-center gap-2 border-b border-border bg-panel px-4 py-2.5">
            <span className="min-w-0 flex-1 truncate text-sm font-medium text-foreground" title={item.name}>{item.name}</span>

            {/* Edit toggle — only for loaded text/markdown, not while editing */}
            {(kind === "text" || kind === "markdown") && textContent !== null && !loading && !error && !editing && (
              <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0" title="Редактировать"
                onClick={() => { setEditContent(textContent); setEditing(true); setSaveError(null); }}>
                <Pencil className="h-4 w-4" />
              </Button>
            )}

            {/* Save / Cancel — only in edit mode */}
            {editing && (
              <>
                {saveError && <span className="shrink-0 text-xs text-destructive">{saveError}</span>}
                <Button size="sm" className="h-8 shrink-0 gap-1.5" onClick={handleSave} disabled={saving}>
                  {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                  {saving ? "Сохранение…" : "Сохранить"}
                </Button>
                <Button variant="ghost" size="sm" className="h-8 shrink-0" onClick={() => { setEditing(false); setSaveError(null); }} disabled={saving}>
                  Отмена
                </Button>
              </>
            )}

            {!editing && (
              <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0" onClick={triggerDownload} title="Скачать">
                <Download className="h-4 w-4" />
              </Button>
            )}
            <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0" onClick={onClose} title="Закрыть" disabled={saving}>
              <X className="h-4 w-4" />
            </Button>
          </div>

          {/* Content */}
          <div className="relative flex flex-1 items-center justify-center overflow-hidden bg-background">
            {loading && <Loader2 className="h-7 w-7 animate-spin text-muted-foreground" />}

            {!loading && error && (
              <div className="flex flex-col items-center gap-2 text-muted-foreground">
                <AlertCircle className="h-7 w-7" />
                <span className="text-sm">{error}</span>
              </div>
            )}

            {kind === "video" && videoStreamUrl && (
              <VideoPlayer src={videoStreamUrl} name={item.name} posterUrl={posterUrl} />
            )}

            {!loading && !error && presignedUrl && (
              <>
                {kind === "image" && <ImageViewer src={presignedUrl} alt={item.name} />}

                {kind === "audio" && <AudioPlayer src={presignedUrl} name={item.name} />}

                {kind === "pdf" && (
                  <div className="relative h-full w-full">
                    {/* Spinner until iframe reports loaded */}
                    {!pdfLoaded && !pdfError && (
                      <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
                        <Loader2 className="h-7 w-7 animate-spin text-muted-foreground" />
                        <span className="text-xs text-muted-foreground">Загрузка PDF…</span>
                      </div>
                    )}
                    {pdfError && (
                      <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-muted-foreground">
                        <AlertCircle className="h-7 w-7" />
                        <span className="text-sm">{pdfError}</span>
                        <a href={presignedUrl} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-sm text-primary underline underline-offset-2 hover:opacity-80">
                          <ExternalLink className="h-3.5 w-3.5" /> Открыть в новой вкладке
                        </a>
                      </div>
                    )}
                    {pdfBlobUrl && (
                      <iframe
                        src={pdfBlobUrl}
                        title={item.name}
                        className={cn("h-full w-full border-0", !pdfLoaded && "invisible")}
                        onLoad={() => setPdfLoaded(true)}
                        onError={() => setPdfError("Не удалось отобразить PDF")}
                      />
                    )}
                  </div>
                )}

                {(kind === "text" || kind === "markdown") && textContent !== null && editing && (
                  <div className="flex h-full w-full overflow-auto font-mono text-sm leading-relaxed">
                    {/* Line numbers are in the same scroll container — no sync needed */}
                    <div
                      className="select-none shrink-0 border-r border-border bg-background px-3 py-6 text-right text-muted-foreground"
                      style={{ minWidth: `${String(editContent.split("\n").length).length + 2}ch` }}
                      aria-hidden
                    >
                      {editContent.split("\n").map((_, i) => (
                        <div key={i}>{i + 1}</div>
                      ))}
                    </div>
                    <div
                      ref={editorRef}
                      contentEditable
                      suppressContentEditableWarning
                      spellCheck={false}
                      onInput={() => setEditContent(editorRef.current?.innerText ?? "")}
                      onPaste={(e) => {
                        e.preventDefault();
                        document.execCommand("insertText", false, e.clipboardData?.getData("text/plain") ?? "");
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Tab") { e.preventDefault(); document.execCommand("insertText", false, "  "); }
                      }}
                      className="min-w-0 flex-1 whitespace-pre-wrap break-words py-6 pl-4 pr-8 text-foreground focus:outline-none"
                    />
                  </div>
                )}

                {(kind === "text" || kind === "markdown") && textContent !== null && !editing && (
                  <div className="flex h-full w-full items-start justify-center overflow-auto p-6">
                    <div className="w-full max-w-4xl rounded-xl border border-border bg-card p-8 shadow-2xl">
                      {kind === "markdown" ? (
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            h1: ({ children }) => <h1 className="mb-4 mt-0 text-2xl font-bold text-foreground">{children}</h1>,
                            h2: ({ children }) => <h2 className="mb-3 mt-6 text-xl font-semibold text-foreground">{children}</h2>,
                            h3: ({ children }) => <h3 className="mb-2 mt-4 text-lg font-semibold text-foreground">{children}</h3>,
                            h4: ({ children }) => <h4 className="mb-1 mt-3 text-base font-semibold text-foreground">{children}</h4>,
                            p: ({ children }) => <p className="mb-3 leading-relaxed text-foreground">{children}</p>,
                            ul: ({ children }) => <ul className="mb-3 list-disc pl-5 text-foreground">{children}</ul>,
                            ol: ({ children }) => <ol className="mb-3 list-decimal pl-5 text-foreground">{children}</ol>,
                            li: ({ children }) => <li className="mb-1">{children}</li>,
                            pre: ({ children }) => <pre className="mb-3 overflow-x-auto rounded-lg bg-muted p-4">{children}</pre>,
                            code: ({ className, children, ...props }) => {
                              const isBlock = !!className?.startsWith("language-");
                              return isBlock
                                ? <code className="block font-mono text-xs leading-relaxed text-foreground" {...props}>{children}</code>
                                : <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-foreground" {...props}>{children}</code>;
                            },
                            blockquote: ({ children }) => <blockquote className="mb-3 border-l-4 border-primary/40 pl-4 italic text-muted-foreground">{children}</blockquote>,
                            a: ({ href, children }) => <a href={href} className="text-primary underline underline-offset-2 hover:opacity-80" target="_blank" rel="noopener noreferrer">{children}</a>,
                            hr: () => <hr className="my-6 border-border" />,
                            table: ({ children }) => <div className="mb-3 overflow-x-auto rounded-lg border border-border"><table className="w-full border-collapse text-sm">{children}</table></div>,
                            th: ({ children }) => <th className="border-b border-border bg-muted px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">{children}</th>,
                            td: ({ children }) => <td className="border-b border-border px-4 py-2 text-foreground last:border-b-0">{children}</td>,
                          }}
                        >
                          {textContent}
                        </ReactMarkdown>
                      ) : (
                        <div className="flex font-mono text-xs leading-relaxed text-foreground">
                          <div
                            className="select-none shrink-0 border-r border-border pr-3 text-right text-muted-foreground"
                            style={{ minWidth: `${String(textContent.split("\n").length).length + 2}ch` }}
                            aria-hidden
                          >
                            {textContent.split("\n").map((_, i) => (
                              <div key={i}>{i + 1}</div>
                            ))}
                          </div>
                          <div className="min-w-0 flex-1 pl-4">
                            {textContent.split("\n").map((line, i) => (
                              <div key={i} className="whitespace-pre-wrap break-words">{line || " "}</div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
