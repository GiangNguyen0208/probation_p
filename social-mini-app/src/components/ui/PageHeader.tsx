import type { ReactNode } from "react";

export function PageHeader({
  icon,
  title,
  actions,
  className = "",
}: {
  icon?: string;
  title: string;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <div className={`flex items-center justify-between mb-4 ${className}`}>
      <div className="flex items-center gap-2">
        {icon && (
          <span className="material-symbols-outlined text-xl" style={{ color: "var(--si-accent)" }}>
            {icon}
          </span>
        )}
        <h1 className="text-lg font-bold" style={{ color: "var(--si-text-primary)" }}>
          {title}
        </h1>
      </div>
      {actions && <div className="flex items-center gap-1">{actions}</div>}
    </div>
  );
}