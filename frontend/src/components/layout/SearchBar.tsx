import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Search, Loader2, FileText, Folder } from "lucide-react";
import { nodesApi } from "@/api/nodes";
import { cn } from "@/lib/utils";
import type { NodeListItem } from "@/types/nodes";

function useDebounce(value: string, ms: number) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return debounced;
}

function resultHref(item: NodeListItem) {
  if (item.node_type === "folder") return `/files/folders/${item.id}`;
  return item.parent_id ? `/files/folders/${item.parent_id}` : "/files";
}

export function SearchBar() {
  const navigate = useNavigate();
  const [raw, setRaw] = useState("");
  const [open, setOpen] = useState(false);
  const [cursor, setCursor] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const query = useDebounce(raw.trim(), 300);

  const { data, isFetching } = useQuery({
    queryKey: ["search", query],
    queryFn: () => nodesApi.search(query, { limit: 10 }),
    enabled: query.length >= 1,
    staleTime: 15_000,
  });

  const results: NodeListItem[] = data?.items ?? [];

  // open when results arrive or query changes while focused
  useEffect(() => {
    if (query) setOpen(true);
    else setOpen(false);
    setCursor(-1);
  }, [query, results]);

  // Ctrl+K / Cmd+K global shortcut
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        inputRef.current?.focus();
        inputRef.current?.select();
      }
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open) return;
    if (e.key === "Escape") {
      setOpen(false);
      inputRef.current?.blur();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setCursor((c) => Math.min(c + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setCursor((c) => Math.max(c - 1, -1));
    } else if (e.key === "Enter" && cursor >= 0 && results[cursor]) {
      pick(results[cursor]);
    }
  }

  function pick(item: NodeListItem) {
    setOpen(false);
    setRaw("");
    navigate(resultHref(item));
  }

  // scroll active item into view
  useEffect(() => {
    if (cursor < 0 || !listRef.current) return;
    const el = listRef.current.children[cursor] as HTMLElement | undefined;
    el?.scrollIntoView({ block: "nearest" });
  }, [cursor]);

  const showDropdown = open && query.length >= 1;

  return (
    <div className="relative w-full max-w-sm">
      {/* Input */}
      <div className="relative flex items-center">
        <Search className="pointer-events-none absolute left-3 h-4 w-4 text-muted-foreground" />
        {isFetching && query ? (
          <Loader2 className="pointer-events-none absolute right-3 h-3.5 w-3.5 animate-spin text-muted-foreground" />
        ) : null}
        <input
          ref={inputRef}
          type="text"
          value={raw}
          placeholder="Поиск…"
          aria-label="Поиск файлов и папок"
          className="h-8 w-full rounded-full border border-input bg-background pl-9 pr-9 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          onChange={(e) => setRaw(e.target.value)}
          onFocus={() => { if (query) setOpen(true); }}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          onKeyDown={handleKeyDown}
        />
        <kbd className="pointer-events-none absolute right-3 hidden select-none rounded border border-border px-1 py-0.5 font-mono text-[10px] text-muted-foreground sm:block">
          ⌃K
        </kbd>
      </div>

      {/* Dropdown */}
      {showDropdown && (
        <div className="absolute left-0 right-0 top-full z-50 mt-1.5 max-h-72 overflow-auto rounded-xl border bg-popover shadow-xl">
          {results.length === 0 && !isFetching ? (
            <p className="px-4 py-3 text-sm text-muted-foreground">Ничего не найдено</p>
          ) : (
            <ul ref={listRef} role="listbox">
              {results.map((item, idx) => (
                <li
                  key={item.id}
                  role="option"
                  aria-selected={cursor === idx}
                  className={cn(
                    "flex cursor-pointer items-center gap-2.5 px-3 py-2 text-sm",
                    cursor === idx ? "bg-accent text-accent-foreground" : "hover:bg-accent/60",
                  )}
                  onMouseEnter={() => setCursor(idx)}
                  onMouseDown={(e) => { e.preventDefault(); pick(item); }}
                >
                  {item.node_type === "folder" ? (
                    <Folder className="h-4 w-4 shrink-0 text-muted-foreground" />
                  ) : (
                    <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                  )}
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{item.name}</span>
                    <span className="block truncate text-xs text-muted-foreground">{item.path}</span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
