import { useNavigate } from "react-router-dom";
import { useDashboardStats } from "../api/hooks";
import { GlassCard } from "../components/ui/GlassCard";
import { Button } from "../components/ui/Button";
import { useTranslation } from "../i18n";
import { useTelegram } from "../telegram/useTelegram";
import { formatCompact } from "../utils/format";

const systemIndicators = [
  { label: "Data Flow", value: 85 },
  { label: "AI Engine", value: 92 },
  { label: "Sync Rate", value: 98 },
];

export default function DashboardPage() {
  const navigate = useNavigate();
  const { haptics } = useTelegram();
  const { t } = useTranslation();
  const { data, isLoading, isError, error, refetch } = useDashboardStats();

  const activePlatformEventsPerHr = data
    ? data.mostActivePlatform === "facebook"
      ? data.facebookCount
      : data.mostActivePlatform === "youtube"
        ? data.youtubeCount
        : data.tiktokCount
    : 0;

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
          {/* System Status Command Center */}
          <section>
            <div
              className="rounded-2xl p-5 flex flex-col gap-4"
              style={{
                backgroundColor: "var(--si-surface)",
                borderLeft: "4px solid var(--si-accent)",
                backgroundImage: "linear-gradient(to bottom right, var(--si-surface), color-mix(in srgb, var(--si-accent) 5%, var(--si-surface)))",
              }}
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-widest mb-1" style={{ color: "var(--si-accent)" }}>
                    System Architecture
                  </p>
                  <div className="flex items-center gap-2">
                    <span className="relative flex h-3 w-3">
                      <span
                        className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
                        style={{ backgroundColor: "var(--si-success)" }}
                      />
                      <span
                        className="relative inline-flex rounded-full h-3 w-3"
                        style={{ backgroundColor: "var(--si-success)", boxShadow: "0 0 8px rgba(52,199,89,0.6)" }}
                      />
                    </span>
                    <h2 className="text-xl font-semibold" style={{ color: "var(--si-text-primary)" }}>
                      Command Active
                    </h2>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xs font-medium" style={{ color: "var(--si-text-tertiary)" }}>Latency</p>
                  <p className="text-sm font-bold" style={{ color: "var(--si-accent)" }}>24ms</p>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2" style={{ borderTop: "1px solid color-mix(in srgb, var(--si-border) 30%, transparent)", paddingTop: "16px", marginTop: "8px" }}>
                {systemIndicators.map((indicator) => (
                  <div key={indicator.label}>
                    <p className="text-[10px] uppercase font-bold mb-1" style={{ color: "var(--si-text-tertiary)" }}>{indicator.label}</p>
                    <div className="h-1.5 w-full rounded-full overflow-hidden" style={{ backgroundColor: "var(--si-surface-highest)" }}>
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${indicator.value}%`, backgroundColor: "var(--si-accent)" }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* Performance Matrix */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--si-text-secondary)" }}>
                Performance Matrix
              </h2>
              <span
                className="text-xs font-medium flex items-center gap-1.5 px-2 py-1 rounded-full"
                style={{ backgroundColor: "color-mix(in srgb, var(--si-accent) 12%, transparent)", color: "var(--si-accent)" }}
              >
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: "var(--si-accent)", animation: "tg-pulse 1.5s ease-in-out infinite" }} />
                Live Feed
              </span>
            </div>

            <div className="grid grid-cols-6 gap-3">
              {/* Total Subjects */}
              <GlassCard className="col-span-3 p-4">
                <p className="text-xs font-medium" style={{ color: "var(--si-text-tertiary)" }}>{t("dashboard.totalSubjects")}</p>
                <div className="flex items-baseline gap-2 mt-1">
                  <span className="text-2xl font-bold" style={{ color: "var(--si-accent)" }}>
                    {formatCompact(data.totalSubjects)}
                  </span>
                  {data.totalSubjects > 0 && (
                    <span className="text-xs font-bold flex items-center" style={{ color: "var(--si-success)" }}>
                      <span className="material-symbols-outlined text-[14px]">arrow_upward</span>
                      {data.mostActivePlatform === "facebook" ? "4%" : "2%"}
                    </span>
                  )}
                </div>
              </GlassCard>

              {/* Active Channel */}
              <GlassCard className="col-span-3 p-4">
                <p className="text-xs font-medium" style={{ color: "var(--si-text-tertiary)" }}>Active Channel</p>
                <div className="font-semibold text-xl mt-1" style={{ color: "var(--si-text-primary)" }}>
                  {data.mostActivePlatform === "facebook" ? "Facebook" : data.mostActivePlatform === "youtube" ? "YouTube" : "TikTok"}
                </div>
                <p className="text-xs mt-1" style={{ color: "var(--si-accent)" }}>
                  {formatCompact(activePlatformEventsPerHr)} events/hr
                </p>
              </GlassCard>

              {/* Meta */}
              <div
                className="col-span-2 rounded-2xl p-4"
                style={{
                  backgroundColor: "color-mix(in srgb, var(--si-surface-low) 40%, var(--si-surface))",
                  border: "1px solid var(--si-border)",
                }}
              >
                <p className="text-xs font-medium" style={{ color: "var(--si-text-tertiary)" }}>Meta</p>
                <span className="text-xl font-bold mt-1 block" style={{ color: "var(--si-text-primary)" }}>
                  {data.facebookCount}
                </span>
              </div>

              {/* YT */}
              <div
                className="col-span-2 rounded-2xl p-4"
                style={{
                  backgroundColor: "color-mix(in srgb, var(--si-surface-low) 40%, var(--si-surface))",
                  border: "1px solid var(--si-border)",
                }}
              >
                <p className="text-xs font-medium" style={{ color: "var(--si-text-tertiary)" }}>Youtube</p>
                <span className="text-xl font-bold mt-1 block" style={{ color: "var(--si-text-primary)" }}>
                  {data.youtubeCount}
                </span>
              </div>

              {/* TikTok */}
              <div
                className="col-span-2 rounded-2xl p-4"
                style={{
                  backgroundColor: "color-mix(in srgb, var(--si-surface-low) 40%, var(--si-surface))",
                  border: "1px solid var(--si-border)",
                }}
              >
                <p className="text-xs font-medium" style={{ color: "var(--si-text-tertiary)" }}>TikTok</p>
                <span className="text-xl font-bold mt-1 block" style={{ color: "var(--si-text-primary)" }}>
                  {data.tiktokCount}
                </span>
              </div>
            </div>
          </section>

          {/* Platform Advantage */}
          <section>
            <div
              className="rounded-2xl p-5 relative overflow-hidden"
              style={{ backgroundColor: "var(--si-surface-highest)" }}
            >
              <div className="absolute top-0 right-0 p-4" style={{ opacity: 0.1 }}>
                <span className="material-symbols-outlined text-[80px]" style={{ color: "var(--si-text-primary)" }}>auto_awesome</span>
              </div>
              <div className="relative">
                <h4 className="text-xs font-semibold uppercase tracking-widest mb-2" style={{ color: "var(--si-text-secondary)" }}>
                  Platform Advantage
                </h4>
                <p className="text-sm leading-relaxed" style={{ color: "var(--si-text-tertiary)" }}>
                  Real-time sync, cross-platform attribution, and AI-driven sentiment analysis that competitors lack. Stay ahead of the narrative.
                </p>
                <div className="mt-4 flex gap-4">
                  <span className="inline-flex items-center gap-1 text-xs font-bold" style={{ color: "var(--si-accent)" }}>
                    <span className="material-symbols-outlined text-[16px]">check_circle</span>
                    Real-time
                  </span>
                  <span className="inline-flex items-center gap-1 text-xs font-bold" style={{ color: "var(--si-accent)" }}>
                    <span className="material-symbols-outlined text-[16px]">check_circle</span>
                    Cross-platform
                  </span>
                </div>
              </div>
            </div>
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

          {/* Intelligence Logs */}
          <section>
            <h2 className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--si-text-secondary)" }}>
              Intelligence Logs
            </h2>
            <div className="flex flex-col gap-3">
              <GlassCard className="flex items-center gap-4 p-4">
                <div className="w-12 h-12 rounded-full overflow-hidden flex-shrink-0" style={{ border: "2px solid color-mix(in srgb, var(--si-accent) 20%, transparent)" }}>
                  <img
                    alt="Profile"
                    className="w-full h-full object-cover"
                    src="https://lh3.googleusercontent.com/aida-public/AB6AXuCt0NCOBK8fARbsXcHf_Oed5c0SfT_-GlhV-cQOYQGwa0b0ancIFq7Pztp7IpspqlvEM8QYbu-Ba8XKj47cjuFQKB43GAS0wZ8FUiULxtCk29RFSUvqqU-uVq7yp1KmgyOtRzNYW0X02OkPmSx-1GGt6nXujSYxLJtazblvmJEkaMh3rxqbCFNUZHUKTJXKuYEoJNqdNUMXzhrcbpoosdnRQbveHQy68_EEF--vyQRlNtsnTbaDHkZCHesagaJmPOEY4XOYNcYawRM"
                  />
                </div>
                <div className="flex-grow min-w-0">
                  <h4 className="text-sm font-bold" style={{ color: "var(--si-text-primary)" }}>Anomalous Spike</h4>
                  <p className="text-sm" style={{ color: "var(--si-text-secondary)" }}>Volume increased by 24% on Facebook.</p>
                </div>
                <span className="material-symbols-outlined text-lg flex-shrink-0" style={{ color: "var(--si-text-tertiary)" }}>chevron_right</span>
              </GlassCard>

              <GlassCard className="flex items-center gap-4 p-4">
                <div
                  className="w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0"
                  style={{ backgroundColor: "color-mix(in srgb, var(--si-accent) 12%, transparent)" }}
                >
                  <span className="material-symbols-outlined" style={{ color: "var(--si-accent)" }}>trending_up</span>
                </div>
                <div className="flex-grow min-w-0">
                  <h4 className="text-sm font-bold" style={{ color: "var(--si-text-primary)" }}>Sentiment Shift</h4>
                  <p className="text-sm" style={{ color: "var(--si-text-secondary)" }}>Positive mentions on YouTube are trending.</p>
                </div>
                <span className="material-symbols-outlined text-lg flex-shrink-0" style={{ color: "var(--si-text-tertiary)" }}>chevron_right</span>
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
      <div
        className="rounded-2xl p-5"
        style={{ backgroundColor: "var(--si-surface)", borderLeft: "4px solid var(--si-accent)" }}
      >
        <div className="flex items-start justify-between">
          <div>
            <div className="h-3 w-32 rounded mb-2" style={{ backgroundColor: "var(--si-surface-elevated)" }} />
            <div className="h-5 w-40 rounded" style={{ backgroundColor: "var(--si-surface-elevated)" }} />
          </div>
          <div className="text-right">
            <div className="h-3 w-12 rounded mb-1" style={{ backgroundColor: "var(--si-surface-elevated)" }} />
            <div className="h-4 w-8 rounded" style={{ backgroundColor: "var(--si-surface-elevated)" }} />
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2 mt-4 pt-4" style={{ borderTop: "1px solid color-mix(in srgb, var(--si-border) 30%, transparent)" }}>
          {[1, 2, 3].map((i) => (
            <div key={i}>
              <div className="h-2.5 w-16 rounded mb-1" style={{ backgroundColor: "var(--si-surface-elevated)" }} />
              <div className="h-1.5 w-full rounded-full" style={{ backgroundColor: "var(--si-surface-elevated)" }} />
            </div>
          ))}
        </div>
      </div>
      <div className="grid grid-cols-6 gap-3">
        {[1, 2].map((i) => (
          <div key={i} className="col-span-3 rounded-2xl p-4" style={{ backgroundColor: "var(--si-surface)", border: "1px solid var(--si-border)" }}>
            <div className="h-3 w-20 rounded mb-3" style={{ backgroundColor: "var(--si-surface-elevated)" }} />
            <div className="h-8 w-16 rounded" style={{ backgroundColor: "var(--si-surface-elevated)" }} />
          </div>
        ))}
        {[1, 2, 3].map((i) => (
          <div key={i} className="col-span-2 rounded-2xl p-4" style={{ backgroundColor: "var(--si-surface)", border: "1px solid var(--si-border)" }}>
            <div className="h-3 w-12 rounded mb-3" style={{ backgroundColor: "var(--si-surface-elevated)" }} />
            <div className="h-6 w-8 rounded" style={{ backgroundColor: "var(--si-surface-elevated)" }} />
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
