import type { ReactNode } from "react";

export interface CardProps {
  className?: string;
  ariaLabel?: string;
  children: ReactNode;
  style?: React.CSSProperties;
}

export function Card({
  className = "",
  ariaLabel,
  children,
  style,
}: CardProps) {
  return (
    <div
      className={`rounded-2xl ${className}`}
      style={{
        backgroundColor: "var(--tg-section-bg-color)",
        boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
        ...style,
      }}
      aria-label={ariaLabel}
    >
      {children}
    </div>
  );
}

export interface CardHeaderProps {
  title: string;
}

export function CardHeader({ title }: CardHeaderProps) {
  return (
    <div
      className="px-4 pt-3 pb-1 text-xs font-semibold uppercase tracking-wide"
      style={{ color: "var(--tg-hint-color)" }}
    >
      {title}
    </div>
  );
}