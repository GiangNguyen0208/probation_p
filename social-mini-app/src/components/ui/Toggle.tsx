export function Toggle({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div className="flex flex-col gap-0.5">
        <span
          className="text-sm font-medium"
          style={{ color: "var(--tg-text-color)" }}
        >
          {label}
        </span>
        {description && (
          <span
            className="text-xs"
            style={{ color: "var(--tg-hint-color)" }}
          >
            {description}
          </span>
        )}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        onClick={() => onChange(!checked)}
        className="shrink-0 rounded-full transition-colors"
        style={{
          width: 44,
          height: 26,
          backgroundColor: checked
            ? "var(--tg-link-color)"
            : "var(--tg-secondary-bg-color)",
          border: "none",
          cursor: "pointer",
          position: "relative",
        }}
      >
        <span
          className="rounded-full bg-white transition-transform"
          style={{
            position: "absolute",
            top: 2,
            left: 2,
            width: 22,
            height: 22,
            transform: checked ? "translateX(18px)" : "translateX(0)",
          }}
        />
      </button>
    </div>
  );
}