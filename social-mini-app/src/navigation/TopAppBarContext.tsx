import { createContext, useContext, useState, type ReactNode } from "react";

export interface TopAppBarConfig {
  icon: string;
  title: string;
  actions?: ReactNode;
}

interface TopAppBarContextValue {
  config: TopAppBarConfig | null;
  setConfig: (config: TopAppBarConfig | null) => void;
}

const TopAppBarContext = createContext<TopAppBarContextValue | null>(null);

export function TopAppBarProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<TopAppBarConfig | null>(null);
  return (
    <TopAppBarContext.Provider value={{ config, setConfig }}>
      {children}
    </TopAppBarContext.Provider>
  );
}

export function useTopAppBar(): TopAppBarContextValue {
  const ctx = useContext(TopAppBarContext);
  if (!ctx) {
    throw new Error("useTopAppBar must be used within TopAppBarProvider");
  }
  return ctx;
}
