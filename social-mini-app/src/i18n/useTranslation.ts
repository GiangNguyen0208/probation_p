import { useContext } from "react";
import { I18nContext } from "./I18nProvider";
import type { TranslationKey } from "./translations";

export function useTranslation() {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error("useTranslation must be used within an I18nProvider");
  }
  return ctx;
}

export type { TranslationKey };
