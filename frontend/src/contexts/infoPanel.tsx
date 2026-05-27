import { createContext, useContext, useState } from "react";
import type { ReactNode } from "react";
import type { NodeListItem } from "@/types/nodes";

interface InfoPanelContextValue {
  selectedItem: NodeListItem | null;
  openInfo: (item: NodeListItem) => void;
  closeInfo: () => void;
}

const InfoPanelContext = createContext<InfoPanelContextValue | null>(null);

export function InfoPanelProvider({ children }: { children: ReactNode }) {
  const [selectedItem, setSelectedItem] = useState<NodeListItem | null>(null);

  return (
    <InfoPanelContext.Provider
      value={{
        selectedItem,
        openInfo: setSelectedItem,
        closeInfo: () => setSelectedItem(null),
      }}
    >
      {children}
    </InfoPanelContext.Provider>
  );
}

export function useInfoPanel() {
  const ctx = useContext(InfoPanelContext);
  if (!ctx) throw new Error("useInfoPanel must be used within InfoPanelProvider");
  return ctx;
}
