import { Cloud, Files, Trash2, Shield, ChevronLeft, ChevronRight } from "lucide-react";
import { NavItem } from "./NavItem";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useAuth } from "@/contexts/auth";
import { cn } from "@/lib/utils";

interface Props {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: Props) {
  const { user } = useAuth();
  const isAdmin = user?.roles.some((r) => r.code === "admin") ?? false;

  return (
    <TooltipProvider>
      <aside
        className={cn(
          "relative flex h-screen flex-col bg-panel transition-all duration-200",
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
