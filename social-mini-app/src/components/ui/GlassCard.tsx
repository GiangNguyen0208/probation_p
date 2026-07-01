import type { ReactNode, MouseEvent } from "react";

export function GlassCard({
  children,
  onClick,
  className = "",
}: {
  children: ReactNode;
  onClick?: (e: MouseEvent<HTMLDivElement>) => void;
  className?: string;
}) {
  return (
    <div
      onClick={onClick}
      className={`rounded-2xl p-4 cursor-pointer transition-all duration-200 active:scale-[0.98] ${className}`}
      style={{
        backgroundColor: "var(--si-surface)",
        border: "1px solid var(--si-border)",
      }}
    >
      {children}
    </div>
  );
}
