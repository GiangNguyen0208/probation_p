import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { themeParams } from "@telegram-apps/sdk";

export type ThemeMode = "system" | "light" | "dark";
export type ChartStyle = "line" | "bar" | "area";

export interface VisualizationSettings {
  chartStyle: ChartStyle;
  showGrid: boolean;
  compactView: boolean;
}

interface ThemeContextValue {
  mode: ThemeMode;
  isDark: boolean;
  appearance: "light" | "dark";
  visualization: VisualizationSettings;
  setMode: (mode: ThemeMode) => void;
  setVisualization: (settings: Partial<VisualizationSettings>) => void;
}

const STORAGE_KEY_THEME = "si_theme_mode";
const STORAGE_KEY_VIZ = "si_visualization";

const defaultVisualization: VisualizationSettings = {
  chartStyle: "line",
  showGrid: true,
  compactView: false,
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

function getTelegramColorScheme(): "light" | "dark" {
  try {
    const css = getComputedStyle(document.documentElement)
      .getPropertyValue("--tg-color-scheme")
      .trim();
    return css === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(() => {
    const stored = localStorage.getItem(STORAGE_KEY_THEME);
    return (stored as ThemeMode) || "system";
  });

  const [tgScheme, setTgScheme] = useState<"light" | "dark">(() =>
    getTelegramColorScheme(),
  );

  const [visualization, setVisualizationState] =
    useState<VisualizationSettings>(() => {
      const stored = localStorage.getItem(STORAGE_KEY_VIZ);
      if (stored) {
        try {
          return { ...defaultVisualization, ...JSON.parse(stored) };
        } catch {
          /* ignore */
        }
      }
      return defaultVisualization;
    });

  useEffect(() => {
    try {
      return themeParams.mount();
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const observer = new MutationObserver(() => {
      setTgScheme(getTelegramColorScheme());
    });
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["style"],
    });
    return () => observer.disconnect();
  }, []);

  const isDark = useMemo(() => {
    if (mode === "system") {
      try {
        return themeParams.isDark();
      } catch {
        return tgScheme === "dark";
      }
    }
    return mode === "dark";
  }, [mode, tgScheme]);

  const appearance: "light" | "dark" = isDark ? "dark" : "light";

  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute("data-theme", appearance);
  }, [appearance]);

  const setMode = useCallback((newMode: ThemeMode) => {
    setModeState(newMode);
    localStorage.setItem(STORAGE_KEY_THEME, newMode);
  }, []);

  const setVisualization = useCallback(
    (settings: Partial<VisualizationSettings>) => {
      setVisualizationState((prev) => {
        const next = { ...prev, ...settings };
        localStorage.setItem(STORAGE_KEY_VIZ, JSON.stringify(next));
        return next;
      });
    },
    [],
  );

  const value = useMemo(
    () => ({
      mode,
      isDark,
      appearance,
      visualization,
      setMode,
      setVisualization,
    }),
    [mode, isDark, appearance, visualization, setMode, setVisualization],
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return ctx;
}