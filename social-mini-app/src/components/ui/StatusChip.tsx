import type { ReactNode } from "react";

type Variant = "success" | "warning" | "danger" | "neutral";

interface StatusChipProps {
  variant?: Variant;
  animate?: boolean;
  children: ReactNode;
}

const variantColors: Record<Variant, { dot: string; bg: string; text: string; border: string }> = {
  success: {
    dot: "var(--si-success)",
    bg: "color-mix(in srgb, var(--si-success) 15%, transparent)",
    text: "var(--si-success)",
    border: "color-mix(in srgb, var(--si-success) 40%, transparent)",
  },
  warning: {
    dot: "var(--si-warning)",
    bg: "color-mix(in srgb, var(--si-warning) 15%, transparent)",
    text: "var(--si-warning)",
    border: "color-mix(in srgb, var(--si-warning) 40%, transparent)",
  },
  danger: {
    dot: "var(--si-danger)",
    bg: "color-mix(in srgb, var(--si-danger) 15%, transparent)",
    text: "var(--si-danger)",
    border: "color-mix(in srgb, var(--si-danger) 40%, transparent)",
  },
  neutral: {
    dot: "var(--si-outline)",
    bg: "color-mix(in srgb, var(--si-outline) 15%, transparent)",
    text: "var(--si-outline)",
    border: "color-mix(in srgb, var(--si-outline) 40%, transparent)",
  },
};

export function StatusChip({ variant = "neutral", animate, children }: StatusChipProps) {
  const c = variantColors[variant];
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border"
      style={{ backgroundColor: c.bg, color: c.text, borderColor: c.border }}
    >
      <span
        className="w-1.5 h-1.5 rounded-full"
        style={{
          backgroundColor: c.dot,
          animation: animate ? "tg-pulse 1.5s ease-in-out infinite" : undefined,
        }}
      />
      {children}
    </span>
  );
}
