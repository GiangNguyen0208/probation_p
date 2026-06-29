import type { ReactNode } from "react";

export function Section({
  title,
  children,
}: {
  title?: string;
  children?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2">
      {title && (
        <h2
          className="text-sm font-semibold px-1"
          style={{ color: "var(--tg-hint-color)" }}
        >
          {title}
        </h2>
      )}
      {children}
    </div>
  );
}
