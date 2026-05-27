import { useState } from "react";
import { KeyRound, LogOut, User } from "lucide-react";
import { useAuth } from "@/contexts/auth";
import { useMyQuota, formatBytes } from "@/hooks/useQuota";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { ChangePasswordDialog } from "@/components/auth/ChangePasswordDialog";

export function UserMenu() {
  const { user, logout } = useAuth();
  const { data: quota } = useMyQuota();
  const [changePassOpen, setChangePassOpen] = useState(false);

  const usedPct = quota
    ? Math.min(100, Math.round((quota.used_bytes / quota.max_bytes) * 100))
    : 0;

  return (
    <>
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="rounded-full" aria-label="Меню пользователя">
          <User className="h-5 w-5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col gap-1">
            <p className="text-sm font-medium leading-none">{user?.username}</p>
            <p className="text-xs text-muted-foreground">{user?.email}</p>
          </div>
        </DropdownMenuLabel>
        {quota && (
          <>
            <DropdownMenuSeparator />
            <div className="px-2 py-1.5">
              <div className="mb-1 flex justify-between text-xs text-muted-foreground">
                <span>{formatBytes(quota.used_bytes)}</span>
                <span>{formatBytes(quota.max_bytes)}</span>
              </div>
              <Progress value={usedPct} className="h-1.5" />
            </div>
          </>
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => setChangePassOpen(true)}>
          <KeyRound className="mr-2 h-4 w-4" />
          Сменить пароль
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={logout} className="text-destructive focus:text-destructive">
          <LogOut className="mr-2 h-4 w-4" />
          Выйти
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>

    <ChangePasswordDialog open={changePassOpen} onOpenChange={setChangePassOpen} />
    </>
  );
}
