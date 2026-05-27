import { Cloud, Files, Trash2, Shield, ChevronLeft, ChevronRight, HardDrive } from "lucide-react";
import { NavItem } from "./NavItem";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { TooltipProvider, Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { Progress } from "@/components/ui/progress";
import { useAuth } from "@/contexts/auth";
import { useMyQuota, formatBytes } from "@/hooks/useQuota";
import { cn } from "@/lib/utils";

interface Props {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: Props) {
  const { user } = useAuth();
  const isAdmin = user?.roles.some((r) => r.code === "admin") ?? false;
  const { data: quota } = useMyQuota();
  const usedPct = quota
    ? Math.min(100, Math.round((quota.storage_used_bytes / quota.storage_limit_bytes) * 100))
    : 0;

  return (
    <TooltipProvider>
      <aside
        className={cn(
          "relative flex h-screen flex-col bg-panel border-r border-border transition-all duration-200",
          collapsed ? "w-[60px]" : "w-[220px]",
        )}
      >
        {/* Logo */}
        <div
          className={cn(
            "flex h-14 items-center px-3",
            collapsed ? "justify-center" : "gap-2.5",
          )}
        >
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/20">
            <Cloud className="h-4 w-4 text-primary" />
          </div>
          {!collapsed && (
            <span className="text-sm font-semibold tracking-tight text-foreground">LocalCloud</span>
          )}
        </div>

        {/* Nav */}
        <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-2 py-1">
          <NavItem to="/files" icon={Files} label="Файлы" collapsed={collapsed} />
          <NavItem to="/trash" icon={Trash2} label="Корзина" collapsed={collapsed} />
          {isAdmin && (
            <>
              <Separator className="my-2 bg-border/50" />
              <NavItem to="/admin/users" icon={Shield} label="Администратор" collapsed={collapsed} />
            </>
          )}
        </nav>

        {/* Quota */}
        {quota && (
          <div className="px-2 pb-1">
            {collapsed ? (
              <Tooltip delayDuration={0}>
                <TooltipTrigger asChild>
                  <div className="flex justify-center py-1">
                    <HardDrive className="h-4 w-4 text-muted-foreground" />
                  </div>
                </TooltipTrigger>
                <TooltipContent side="right" sideOffset={8}>
                  {formatBytes(quota.storage_used_bytes)} / {formatBytes(quota.storage_limit_bytes)}
                </TooltipContent>
              </Tooltip>
            ) : (
              <div className="rounded-lg bg-muted/40 px-3 py-2">
                <div className="mb-1.5 flex items-center gap-1.5 text-xs text-muted-foreground">
                  <HardDrive className="h-3 w-3 shrink-0" />
                  <span className="truncate">{formatBytes(quota.storage_used_bytes)} / {formatBytes(quota.storage_limit_bytes)}</span>
                </div>
                <Progress value={usedPct} className="h-1 bg-border" />
              </div>
            )}
          </div>
        )}

        {/* Collapse toggle */}
        <div className="p-2">
          <Button
            variant="ghost"
            size="icon"
            className="w-full text-muted-foreground hover:text-foreground"
            onClick={onToggle}
            aria-label={collapsed ? "Развернуть боковую панель" : "Свернуть боковую панель"}
          >
            {collapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </Button>
        </div>
      </aside>
    </TooltipProvider>
  );
}
