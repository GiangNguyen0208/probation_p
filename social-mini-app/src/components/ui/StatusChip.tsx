import type { ReactNode } from "react";

type Variant = "success" | "warning" | "danger" | "neutral";

interface StatusChipProps {
  variant?: Variant;
  animate?: boolean;
  children: ReactNode;
}

const variantColors: Record<Variant, { dot: string; bg: string; text: string }> = {
  success: { dot: "#34c759", bg: "rgba(52,199,89,0.12)", text: "#34c759" },
  warning: { dot: "#ff9500", bg: "rgba(255,149,0,0.12)", text: "#ff9500" },
  danger: { dot: "#ff3b30", bg: "rgba(255,59,48,0.12)", text: "#ff3b30" },
  neutral: { dot: "#8e8e93", bg: "rgba(142,142,147,0.12)", text: "#8e8e93" },
};

export function StatusChip({ variant = "neutral", animate, children }: StatusChipProps) {
  const c = variantColors[variant];
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium"
      style={{ backgroundColor: c.bg, color: c.text }}
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
