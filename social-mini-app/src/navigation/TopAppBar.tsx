import { useTopAppBar } from "./TopAppBarContext";

export function TopAppBar() {
  const { config } = useTopAppBar();

  if (!config) return null;

  return (
    <header
      className="fixed top-0 left-0 right-0 z-50 h-14"
      style={{
        backgroundColor: "color-mix(in srgb, var(--si-surface) 80%, transparent)",
        borderBottom: "1px solid var(--si-border)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
      }}
    >
      <div
        className="flex items-center justify-between h-full max-w-[600px] mx-auto"
        style={{ paddingLeft: 16, paddingRight: 16 }}
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className="material-symbols-outlined shrink-0" style={{ color: "var(--si-accent)" }}>{config.icon}</span>
          <h1 className="text-lg font-bold truncate" style={{ color: "var(--si-text-primary)" }}>{config.title}</h1>
        </div>
        {config.actions && (
          <div className="flex items-center gap-1 shrink-0">{config.actions}</div>
        )}
      </div>
    </header>
  );
}

export function TopAppBarAction({
  icon,
  onClick,
}: {
  icon: string;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="material-symbols-outlined text-on-surface-variant active:scale-95 transition-transform flex items-center justify-center w-10 h-10"
    >
      {icon}
    </button>
  );
}
