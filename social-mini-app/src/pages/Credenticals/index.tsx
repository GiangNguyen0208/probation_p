import { useNavigate, useSearchParams } from "react-router-dom";
import { useCredentials } from "../../api/credential-hooks";
import { GlassCard } from "../../components/ui/GlassCard";
import { StatusChip } from "../../components/ui/StatusChip";
import { Button } from "../../components/ui/Button";
import { useTranslation } from "../../i18n";
import { useTelegram } from "../../telegram/useTelegram";
import { formatRelative } from "../../utils/format";

const platformColors: Record<string, string> = {
  facebook: "#1877f2",
  youtube: "#ff0000",
  google: "#4285f4",
  linkedin: "#0a66c2",
};

const platformInitials: Record<string, string> = {
  facebook: "F",
  youtube: "Y",
  google: "G",
  linkedin: "L",
};

const statusConfig: Record<string, { variant: "success" | "warning" | "danger"; label: string }> = {
  active: { variant: "success", label: "Active" },
  expired: { variant: "warning", label: "Expired" },
  revoked: { variant: "danger", label: "Revoked" },
};

export default function CredentialListPage() {
  const navigate = useNavigate();
  const { haptics } = useTelegram();
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();

  const created = searchParams.get("created");

  const { data, isLoading, isError, error, refetch } = useCredentials();

  const credentials = data ?? [];

  return (
    <div className="flex flex-col gap-5">
      {created && (
        <div
          className="rounded-xl px-3 py-2.5 text-sm text-center font-medium"
          style={{ backgroundColor: "var(--si-success-tint)", color: "var(--si-success)" }}
          role="status"
        >
          {t("credentials.createdSuccess")}
        </div>
      )}

      <div className="relative w-full">
        <input
          className="w-full rounded-xl py-3 pl-11 pr-4 text-sm outline-none"
          style={{
            backgroundColor: "var(--si-surface-elevated)",
            color: "var(--si-text-primary)",
            border: "1px solid var(--si-border)",
          }}
          placeholder={t("common.search")}
          type="text"
        />
        <span
          className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-lg"
          style={{ color: "var(--si-text-tertiary)" }}
        >
          search
        </span>
      </div>

      {isLoading && <LoadingSkeleton />}
      {isError && (
        <div className="flex flex-col items-center gap-3 py-12 text-center" role="alert">
          <span className="material-symbols-outlined text-4xl" style={{ color: "var(--si-danger)" }}>error</span>
          <p className="text-sm" style={{ color: "var(--si-text-primary)" }}>{error?.message ?? t("common.error")}</p>
          <Button variant="secondary" onClick={() => refetch()}>
            {t("common.retry")}
          </Button>
        </div>
      )}

      {!isLoading && !isError && credentials.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div
            className="w-20 h-20 rounded-full flex items-center justify-center mb-5"
            style={{ backgroundColor: "var(--si-surface-elevated)" }}
          >
            <span className="material-symbols-outlined text-4xl" style={{ color: "var(--si-text-tertiary)" }}>description</span>
          </div>
          <h2 className="text-base font-bold mb-2" style={{ color: "var(--si-text-primary)" }}>
            {t("credentials.title")}
          </h2>
          <p className="text-sm max-w-[240px] mb-8" style={{ color: "var(--si-text-secondary)" }}>
            {t("credentials.empty")}
          </p>
          <Button
            fullWidth
            onClick={() => {
              haptics.impact("medium");
              navigate("/credentials/new");
            }}
          >
            {t("credentials.add")}
          </Button>
        </div>
      )}

      {!isLoading && !isError && credentials.length > 0 && (
        <section>
          <div className="mb-3 px-1">
            <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--si-text-tertiary)" }}>
              {t("credentials.activeCredentials")}
            </span>
          </div>

          <div className="flex flex-col gap-3">
            {credentials.map((cred) => {
              const color = platformColors[cred.platform_slug] ?? "#666";
              const initial = platformInitials[cred.platform_slug] ?? cred.platform_slug[0]?.toUpperCase() ?? "?";
              const status = statusConfig[cred.status] ?? { variant: "neutral" as const, label: cred.status };

              return (
                <GlassCard
                  key={cred.id}
                  onClick={() => {
                    haptics.impact("light");
                    navigate(`/credentials/${cred.id}`);
                  }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4 min-w-0 flex-1">
                      <div
                        className="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-lg shrink-0"
                        style={{ backgroundColor: color }}
                      >
                        {initial}
                      </div>
                      <div className="min-w-0">
                        <h3 className="text-base font-semibold truncate" style={{ color: "var(--si-text-primary)" }}>
                          {cred.label}
                        </h3>
                        <p className="text-xs truncate" style={{ color: "var(--si-text-tertiary)" }}>
                          {cred.platform_slug}
                          {cred.last_verified_at ? ` \u2022 verified ${formatRelative(cred.last_verified_at)}` : ""}
                        </p>
                      </div>
                    </div>
                    <StatusChip variant={status.variant} animate={cred.status === "active"}>
                      {status.label}
                    </StatusChip>
                  </div>
                </GlassCard>
              );
            })}
          </div>
        </section>
      )}

      {!isLoading && !isError && credentials.length > 0 && (
        <div className="fixed bottom-16 left-0 right-0 z-40 px-4 pointer-events-none">
          <div className="max-w-[480px] mx-auto pointer-events-auto pb-4">
            <Button
              fullWidth
              size="lg"
              onClick={() => {
                haptics.impact("medium");
                navigate("/credentials/new");
              }}
            >
              <span className="material-symbols-outlined text-lg">add</span>
              New Security Token
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="flex flex-col gap-3" aria-busy="true" role="status">
      {[1, 2, 3].map((i) => (
        <div key={i} className="rounded-2xl p-4" style={{ backgroundColor: "var(--si-surface)", border: "1px solid var(--si-border)" }}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-full" style={{ backgroundColor: "var(--si-surface-elevated)" }} />
              <div className="space-y-2">
                <div className="h-4 w-32 rounded" style={{ backgroundColor: "var(--si-surface-elevated)" }} />
                <div className="h-3 w-24 rounded" style={{ backgroundColor: "var(--si-surface-elevated)" }} />
              </div>
            </div>
            <div className="h-6 w-16 rounded-full" style={{ backgroundColor: "var(--si-surface-elevated)" }} />
          </div>
        </div>
      ))}
    </div>
  );
}
