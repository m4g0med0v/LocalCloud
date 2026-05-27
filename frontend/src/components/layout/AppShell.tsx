import { useState, useEffect } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { BreadcrumbProvider } from "@/contexts/breadcrumb";
import { UploadProvider } from "@/contexts/upload";
import { InfoPanelProvider, useInfoPanel } from "@/contexts/infoPanel";
import { UploadPanel } from "@/components/files/UploadPanel";
import { NodeInfoPanel } from "@/components/files/NodeInfoPanel";
import { ErrorBoundary } from "@/components/ErrorBoundary";

const STORAGE_KEY = "sidebar-collapsed";

function AppShellLayout() {
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) === "true";
    } catch {
      return false;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, String(collapsed));
    } catch {
      // ignore
    }
  }, [collapsed]);

  const { selectedItem, closeInfo } = useInfoPanel();

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Desktop sidebar */}
      <div className="hidden md:flex">
        <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      </div>

      {/* Main area + info panel */}
      <div className="flex flex-1 overflow-hidden">
        <div className="flex flex-1 flex-col overflow-hidden bg-background">
          <TopBar />
          <main className="flex-1 overflow-y-auto p-4 md:p-6">
            <ErrorBoundary>
              <Outlet />
            </ErrorBoundary>
          </main>
        </div>

        {selectedItem && (
          <NodeInfoPanel item={selectedItem} onClose={closeInfo} />
        )}
      </div>
    </div>
  );
}

export function AppShell() {
  return (
    <BreadcrumbProvider>
      <UploadProvider>
        <InfoPanelProvider>
          <AppShellLayout />
          <UploadPanel />
        </InfoPanelProvider>
      </UploadProvider>
    </BreadcrumbProvider>
  );
}
