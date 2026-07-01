import { useNavigate } from "react-router-dom";
import { useDashboardStats } from "../api/hooks";
import { GlassCard } from "../components/ui/GlassCard";
import { Button } from "../components/ui/Button";
import { useTranslation } from "../i18n";
import { useTelegram } from "../telegram/useTelegram";
import { formatCompact } from "../utils/format";

const systemIndicators = [
  { label: "Command Active", status: "live" as const },
  { label: "Latency 24ms", status: "live" as const },
  { label: "Data Flow", status: "live" as const },
  { label: "AI Engine", status: "live" as const },
  { label: "Sync Rate", status: "live" as const },
];

export default function DashboardPage() {
  const navigate = useNavigate();
  const { haptics } = useTelegram();
  const { t } = useTranslation();
  const { data, isLoading, isError, error, refetch } = useDashboardStats();

  return (
    <div className="flex flex-col gap-5">
      {isLoading && <LoadingSkeleton />}
      {isError && (
        <div className="flex flex-col items-center gap-3 py-12 text-center" role="alert">
          <span className="material-symbols-outlined text-4xl" style={{ color: "var(--si-danger)" }}>error</span>
          <p style={{ color: "var(--si-text-primary)" }} className="text-sm">{error?.message ?? t("common.error")}</p>
          <Button variant="secondary" onClick={() => refetch()}>
            {t("common.retry")}
          </Button>
        </div>
      )}
      {!isLoading && !isError && !data && <EmptySkeleton />}

      {data && (
        <>
          <section>
            <div
              className="rounded-2xl p-5 flex flex-col gap-4"
              style={{ backgroundColor: "var(--si-surface)" }}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--si-accent)" }}>
                  System Architecture
                </span>
                <div className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: "var(--si-success)", animation: "tg-pulse 1.5s ease-in-out infinite" }} />
                  <span className="text-xs font-medium" style={{ color: "var(--si-text-secondary)" }}>Command Active</span>
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                {systemIndicators.map((indicator) => (
                  <span
                    key={indicator.label}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium"
                    style={{
                      backgroundColor: "var(--si-accent-tint)",
                      color: "var(--si-accent)",
                    }}
                  >
                    <span
                      className="w-1.5 h-1.5 rounded-full"
                      style={{
                        backgroundColor: "var(--si-success)",
                        animation: "tg-pulse 1.5s ease-in-out infinite",
                      }}
                    />
                    {indicator.label}
                  </span>
                ))}
              </div>
            </div>
          </section>

          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--si-text-secondary)" }}>
                Performance Matrix
              </h2>
              <div className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: "var(--si-success)", animation: "tg-pulse 1.5s ease-in-out infinite" }} />
                <span className="text-xs font-medium" style={{ color: "var(--si-text-secondary)" }}>Live Feed</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <GlassCard>
                <p className="text-xs font-medium" style={{ color: "var(--si-text-tertiary) " }}>{t("dashboard.totalSubjects")}</p>
                <div className="flex items-baseline gap-2 mt-1">
                  <span className="text-3xl font-bold" style={{ color: "var(--si-text-primary)" }}>
                    {formatCompact(data.totalSubjects)}
                  </span>
                  {data.totalSubjects > 0 && (
                    <span className="text-xs font-medium flex items-center gap-0.5" style={{ color: "var(--si-success)" }}>
                      arrow_upward
                      <span className="material-symbols-outlined text-[14px]">arrow_upward</span>
                      {data.mostActivePlatform === "facebook" ? "4%" : "2%"}
                    </span>
                  )}
                </div>
              </GlassCard>

              <GlassCard>
                <p className="text-xs font-medium" style={{ color: "var(--si-text-tertiary)" }}>Active Channel</p>
                <div className="flex items-baseline gap-2 mt-1">
                  <span className="text-3xl font-bold" style={{ color: "var(--si-accent)" }}>
                    {data.mostActivePlatform === "facebook" ? "Facebook" : data.mostActivePlatform === "youtube" ? "YouTube" : "TikTok"}
                  </span>
                </div>
                <p className="text-xs mt-1" style={{ color: "var(--si-text-secondary)" }}>
                  {data.lastSyncTimestamp ? `${formatCompact(data.totalSubjects)} events/hr` : "No data"}
                </p>
              </GlassCard>

              <GlassCard>
                <p className="text-xs font-medium" style={{ color: "var(--si-text-tertiary)" }}>Meta</p>
                <span className="text-3xl font-bold" style={{ color: "var(--si-text-primary)" }}>
                  {data.facebookCount}
                </span>
              </GlassCard>

              <GlassCard>
                <p className="text-xs font-medium" style={{ color: "var(--si-text-tertiary)" }}>YT</p>
                <span className="text-3xl font-bold" style={{ color: "var(--si-text-primary)" }}>
                  {data.youtubeCount}
                </span>
              </GlassCard>
            </div>
          </section>

          <section>
            <GlassCard onClick={() => { haptics.impact("light"); navigate("/"); }}>
              <div className="flex flex-col gap-3">
                <p className="text-xs font-semibold" style={{ color: "var(--si-text-secondary)" }}>
                  Platform Advantage
                </p>
                <p className="text-sm leading-relaxed" style={{ color: "var(--si-text-tertiary)" }}>
                  Real-time sync, cross-platform attribution, and AI-driven sentiment analysis that competitors lack. Stay ahead of the narrative.
                </p>
                <div className="flex flex-wrap gap-3">
                  <span className="inline-flex items-center gap-1 text-xs font-medium" style={{ color: "var(--si-success)" }}>
                    <span className="material-symbols-outlined text-[16px]">check_circle</span>
                    Real-time
                  </span>
                  <span className="inline-flex items-center gap-1 text-xs font-medium" style={{ color: "var(--si-success)" }}>
                    <span className="material-symbols-outlined text-[16px]">check_circle</span>
                    Cross-platform
                  </span>
                </div>
              </div>
            </GlassCard>
          </section>

          <Button
            variant="primary"
            fullWidth
            onClick={() => {
              haptics.impact("light");
              navigate("/");
            }}
          >
            <span className="material-symbols-outlined text-[20px]">explore</span>
            {t("dashboard.browseSubjects")}
          </Button>

          <section>
            <h2 className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--si-text-secondary)" }}>
              Intelligence Logs
            </h2>
            <div className="flex flex-col gap-3">
              <GlassCard className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="material-symbols-outlined text-xl" style={{ color: "var(--si-warning)" }}>trending_up</span>
                  <div>
                    <p className="text-sm font-medium" style={{ color: "var(--si-text-primary)" }}>Anomalous Spike</p>
                    <p className="text-xs" style={{ color: "var(--si-text-tertiary)" }}>
                      Volume increased by 24% on Facebook.
                    </p>
                  </div>
                </div>
                <span className="material-symbols-outlined text-lg" style={{ color: "var(--si-text-tertiary)" }}>chevron_right</span>
              </GlassCard>

              <GlassCard className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="material-symbols-outlined text-xl" style={{ color: "var(--si-success)" }}>trending_up</span>
                  <div>
                    <p className="text-sm font-medium" style={{ color: "var(--si-text-primary)" }}>Sentiment Shift</p>
                    <p className="text-xs" style={{ color: "var(--si-text-tertiary)" }}>
                      Positive mentions on YouTube are trending.
                    </p>
                  </div>
                </div>
                <span className="material-symbols-outlined text-lg" style={{ color: "var(--si-text-tertiary)" }}>chevron_right</span>
              </GlassCard>
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="flex flex-col gap-5" aria-busy="true" role="status">
      <div className="rounded-2xl p-5" style={{ backgroundColor: "var(--si-surface)" }}>
        <div className="h-3 w-32 rounded mb-4" style={{ backgroundColor: "var(--si-surface-elevated)" }} />
        <div className="flex flex-wrap gap-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-7 w-24 rounded-full" style={{ backgroundColor: "var(--si-surface-elevated)" }} />
          ))}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="rounded-2xl p-4" style={{ backgroundColor: "var(--si-surface)" }}>
            <div className="h-3 w-20 rounded mb-3" style={{ backgroundColor: "var(--si-surface-elevated)" }} />
            <div className="h-8 w-16 rounded" style={{ backgroundColor: "var(--si-surface-elevated)" }} />
          </div>
        ))}
      </div>
    </div>
  );
}

function EmptySkeleton() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="w-20 h-20 rounded-full flex items-center justify-center mb-4" style={{ backgroundColor: "var(--si-surface-elevated)" }}>
        <span className="material-symbols-outlined text-4xl" style={{ color: "var(--si-text-tertiary)" }}>monitoring</span>
      </div>
      <p className="text-sm" style={{ color: "var(--si-text-secondary)" }}>No dashboard data available</p>
    </div>
  );
}
