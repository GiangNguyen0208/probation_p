import { useCallback, useEffect, useRef, useState } from "react";
import {
  backButton,
  closingBehavior,
  hapticFeedback,
  init,
  mainButton,
  miniApp,
  retrieveLaunchParams,
  swipeBehavior,
  themeParams,
  viewport,
} from "@telegram-apps/sdk";
import type { LaunchParams, ThemeParams } from "@telegram-apps/sdk";

type HapticStyle = "light" | "medium" | "heavy" | "rigid" | "soft";
type HapticNotification = "error" | "success" | "warning";

export interface MainButtonConfig {
  text: string;
  onClick: () => void;
  isLoading?: boolean;
  disabled?: boolean;
}

export function useTelegram() {
  const [ready, setReady] = useState(false);
  const [theme, setTheme] = useState<ThemeParams | null>(null);
  const [viewportHeight, setViewportHeight] = useState<string>(
    "var(--tg-viewport-stable-height, 100vh)",
  );
  const launchParamsRef = useRef<LaunchParams | null>(null);

  useEffect(() => {
    try {
      init();

      miniApp.ready();
      viewport.expand();
      viewport.mount();
      backButton.mount();
      themeParams.mount();
      closingBehavior.mount();
      swipeBehavior.mount();
      swipeBehavior.enableVertical();

      try {
        miniApp.setHeaderColor("bg_color");
        miniApp.setBackgroundColor("bg_color");
        miniApp.setBottomBarColor("bg_color");
      } catch {
        /* older API versions */
      }

      try {
        const currentTheme = themeParams.state();
        setTheme(currentTheme as unknown as ThemeParams);
      } catch {
        /* non-telegram environment */
      }

      try {
        const h = viewport.height();
        if (h) {
          setViewportHeight(`${h}px`);
        }
      } catch {
        /* ignore */
      }
    } catch {
      /* running outside Telegram */
    }

    setReady(true);

    /* Subscribe to viewport height changes AFTER setReady to avoid
       an early return that would prevent ready from becoming true.
       The subscription cleanup is merged with the effect's return. */
    let unsubscribeViewport: (() => void) | null = null;
    try {
      const unsub = viewport.height.sub((h) => {
        if (h) {
          setViewportHeight(`${h}px`);
        }
      });
      unsubscribeViewport = unsub;
    } catch {
      /* ignore */
    }

    return () => {
      try {
        backButton.unmount();
        themeParams.unmount();
        swipeBehavior.unmount();
        closingBehavior.unmount();
      } catch {
        /* ignore */
      }
      if (unsubscribeViewport) {
        try {
          unsubscribeViewport();
        } catch {
          /* ignore */
        }
      }
    };
  }, []);

  useEffect(() => {
    if (ready) return;
    const id = setTimeout(() => setReady(true), 200);
    return () => clearTimeout(id);
  }, [ready]);

  if (launchParamsRef.current === null) {
    try {
      launchParamsRef.current = retrieveLaunchParams();
    } catch {
      launchParamsRef.current = null;
    }
  }

  const showBack = useCallback(() => {
    try {
      backButton.show();
    } catch {
      /* ignore */
    }
  }, []);

  const hideBack = useCallback(() => {
    try {
      backButton.hide();
    } catch {
      /* ignore */
    }
  }, []);

  const onBackClick = useCallback((cb: () => void) => {
    try {
      backButton.onClick(cb);
    } catch {
      /* ignore */
    }
  }, []);

  const offBackClick = useCallback((cb: () => void) => {
    try {
      backButton.offClick(cb);
    } catch {
      /* ignore */
    }
  }, []);

  const impactHaptic = useCallback((style: HapticStyle = "light") => {
    try {
      hapticFeedback.impactOccurred(style);
    } catch {
      /* ignore */
    }
  }, []);

  const notificationHaptic = useCallback((type: HapticNotification) => {
    try {
      hapticFeedback.notificationOccurred(type);
    } catch {
      /* ignore */
    }
  }, []);

  const selectionHaptic = useCallback(() => {
    try {
      hapticFeedback.selectionChanged();
    } catch {
      /* ignore */
    }
  }, []);

  const enableClosingConfirmation = useCallback(() => {
    try {
      closingBehavior.enableConfirmation();
    } catch {
      /* ignore */
    }
  }, []);

  const disableClosingConfirmation = useCallback(() => {
    try {
      closingBehavior.disableConfirmation();
    } catch {
      /* ignore */
    }
  }, []);

  const setMainButton = useCallback((config: MainButtonConfig | null) => {
    try {
      if (config === null) {
        mainButton.setParams({
          isVisible: false,
        });
        return;
      }

      const buttonColor = themeParams.buttonColor();
      const textColor = themeParams.buttonTextColor();

      mainButton.setParams({
        text: config.text,
        backgroundColor: buttonColor,
        textColor: textColor,
        isVisible: true,
        isEnabled: !config.disabled,
        isLoaderVisible: config.isLoading,
      });

      mainButton.onClick(config.onClick);
    } catch {
      /* ignore */
    }
  }, []);

  return {
    ready,
    theme,
    viewportHeight,
    launchParams: launchParamsRef.current,
    back: {
      show: showBack,
      hide: hideBack,
      onClick: onBackClick,
      offClick: offBackClick,
    },
    haptics: {
      impact: impactHaptic,
      notification: notificationHaptic,
      selection: selectionHaptic,
    },
    closing: {
      enableConfirmation: enableClosingConfirmation,
      disableConfirmation: disableClosingConfirmation,
    },
    mainButton: { set: setMainButton },
  };
}