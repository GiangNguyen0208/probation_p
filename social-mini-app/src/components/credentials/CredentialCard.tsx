import type { Credential } from "../../api/admin-types";
import { formatRelative } from "../../utils/format";

interface CredentialCardProps {
  credential: Credential;
  onClick: () => void;
}

const platformIcons: Record<string, string> = {
  facebook: "#1877f2",
  youtube: "#ff0000",
};

const platformInitials: Record<string, string> = {
  facebook: "F",
  youtube: "Y",
};

const statusStyles: Record<string, { dot: string; label: string }> = {
  active: { dot: "#34c759", label: "Active" },
  revoked: { dot: "#ff3b30", label: "Revoked" },
  expired: { dot: "#ff9500", label: "Expired" },
};

export function CredentialCard({ credential, onClick }: CredentialCardProps) {
  const iconColor = platformIcons[credential.platform_slug] ?? "#666";
  const initial = platformInitials[credential.platform_slug] ?? credential.platform_slug[0]?.toUpperCase() ?? "?";
  const status = statusStyles[credential.status] ?? { dot: "#8e8e93", label: credential.status };

  return (
    <div
      role="listitem"
      onClick={() => {
        onClick();
      }}
      className="rounded-2xl p-3 flex items-center gap-3 cursor-pointer active:opacity-80 transition-opacity"
      style={{
        backgroundColor: "var(--tg-section-bg-color)",
        boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
      }}
      aria-label={`${credential.label}, ${status.label}`}
    >
      <div
        className="rounded-full flex items-center justify-center text-white font-semibold text-sm shrink-0"
        style={{
          width: 40,
          height: 40,
          backgroundColor: iconColor,
        }}
      >
        {initial}
      </div>

      <div className="flex-1 min-w-0">
        <h3
          className="font-medium text-sm truncate"
          style={{ color: "var(--tg-text-color)" }}
        >
          {credential.label}
        </h3>
        <p
          className="text-xs"
          style={{ color: "var(--tg-hint-color)" }}
        >
          {credential.platform_slug}
          {credential.last_verified_at ? ` · Verified ${formatRelative(credential.last_verified_at)}` : ""}
        </p>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <div
          className="rounded-full"
          style={{
            width: 8,
            height: 8,
            backgroundColor: status.dot,
          }}
          aria-hidden="true"
        />
        <span
          className="text-xs"
          style={{ color: credential.is_active ? "var(--tg-text-color)" : "var(--tg-hint-color)" }}
        >
          {status.label}
        </span>
      </div>
    </div>
  );
}
