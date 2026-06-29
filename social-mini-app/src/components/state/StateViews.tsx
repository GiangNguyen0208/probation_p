import { Button } from "../ui/Button";

function Loading({ count = 4 }: { count?: number }) {
  return (
    <div
      className="flex flex-col gap-2"
      aria-busy="true"
      aria-label="Loading content"
      role="status"
    >
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="rounded-xl overflow-hidden p-3 flex items-center gap-3"
          style={{ backgroundColor: "var(--tg-section-bg-color)" }}
        >
          <div
            className="rounded-full shrink-0 animate-pulse"
            style={{
              width: 40,
              height: 40,
              backgroundColor: "var(--tg-secondary-bg-color)",
            }}
          />
          <div className="flex-1 space-y-1.5">
            <div
              className="rounded animate-pulse"
              style={{
                width: `${60 + ((i * 13) % 30)}%`,
                height: 14,
                backgroundColor: "var(--tg-secondary-bg-color)",
              }}
            />
            <div
              className="rounded animate-pulse"
              style={{
                width: `${40 + ((i * 7) % 30)}%`,
                height: 12,
                backgroundColor: "var(--tg-secondary-bg-color)",
              }}
            />
          </div>
          <div
            className="rounded animate-pulse shrink-0"
            style={{
              width: 48,
              height: 12,
              backgroundColor: "var(--tg-secondary-bg-color)",
            }}
          />
        </div>
      ))}
    </div>
  );
}

function Empty({
  message,
  action,
  actionLabel,
}: {
  message?: string;
  action?: () => void;
  actionLabel?: string;
}) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 py-12"
      role="status"
    >
      <svg
        width="64"
        height="64"
        viewBox="0 0 64 64"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        aria-hidden="true"
        style={{ color: "var(--tg-hint-color)" }}
      >
        <rect x="8" y="14" width="48" height="36" rx="4" />
        <path d="M26 32h12M26 38h7" strokeLinecap="round" />
        <circle cx="32" cy="24" r="4" />
      </svg>
      <p
        className="text-sm text-center"
        style={{ color: "var(--tg-hint-color)" }}
      >
        {message ?? "No data available"}
      </p>
      {action && actionLabel && (
        <Button variant="secondary" onClick={action}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
}

function ErrorState({
  message,
  retry,
  retryLabel,
}: {
  message: string;
  retry?: () => void;
  retryLabel?: string;
}) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 py-12"
      role="alert"
    >
      <svg
        width="48"
        height="48"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        style={{ color: "var(--tg-destructive-text-color)" }}
      >
        <circle cx="12" cy="12" r="10" />
        <path d="M12 8v4M12 16h.01" />
      </svg>
      <p
        className="text-sm text-center"
        style={{ color: "var(--tg-text-color)" }}
      >
        {message}
      </p>
      {retry && (
        <Button variant="secondary" onClick={retry}>
          {retryLabel ?? "Try again"}
        </Button>
      )}
    </div>
  );
}

const StateViews = { Loading, Empty, Error: ErrorState };
export default StateViews;