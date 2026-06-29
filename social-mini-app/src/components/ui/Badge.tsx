import type { ReactNode } from "react";

type Variant = "success" | "warning" | "danger";

const variantColors: Record<Variant, { bg: string; text: string }> = {
  success: { bg: "rgba(52,199,89,0.15)", text: "#34c759" },
  warning: { bg: "rgba(255,149,0,0.15)", text: "#ff9500" },
  danger: { bg: "rgba(255,59,48,0.15)", text: "#ff3b30" },
};

export function Badge({
  variant = "success",
  children,
}: {
  variant?: Variant;
  children: ReactNode;
}) {
  const colors = variantColors[variant];
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold"
      style={{ backgroundColor: colors.bg, color: colors.text }}
    >
      {children}
    </span>
  );
}