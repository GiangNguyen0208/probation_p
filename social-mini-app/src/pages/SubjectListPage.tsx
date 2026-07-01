import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useInfiniteSubjects } from "../api/hooks";
import type { SubjectFilters } from "../api/hooks";
import { GlassCard } from "../components/ui/GlassCard";
import { StatusChip } from "../components/ui/StatusChip";
import { Spinner } from "../components/ui/Spinner";
import { useTranslation } from "../i18n";
import { useTelegram } from "../telegram/useTelegram";
import { formatCompact, formatRelative } from "../utils/format";

const platformInitials: Record<string, string> = {
  facebook: "F",
  youtube: "Y",
};

const platformColors: Record<string, string> = {
  facebook: "#1877f2",
  youtube: "#ff0000",
};

const statusConfig: Record<string, { variant: "success" | "warning" | "danger" | "neutral"; label: string }> = {
  active: { variant: "success", label: "High Impact" },
  inactive: { variant: "neutral", label: "Stable" },
  suspended: { variant: "danger", label: "Suspended" },
};

export default function SubjectListPage() {
  const navigate = useNavigate();
  const { haptics } = useTelegram();
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const sentinelRef = useRef<HTMLDivElement>(null);
  const [searchQuery, setSearchQuery] = useState(searchParams.get("q") ?? "");

  const filters: SubjectFilters = {
    platform: searchParams.get("platform"),
    status: searchParams.get("status"),
    q: searchParams.get("q"),
  };

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteSubjects(filters);

  const subjects = data?.pages.flatMap((p) => p.data) ?? [];

  const setFilter = (key: string, value: string | null) => {
    const next = new URLSearchParams(searchParams);
    if (value) {
      next.set(key, value);
    } else {
      next.delete(key);
    }
    setSearchParams(next);
  };

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el || !hasNextPage || isFetchingNextPage) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          fetchNextPage();
        }
      },
      { rootMargin: "200px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  const handleSearch = (val: string) => {
    setSearchQuery(val);
    setFilter("q", val || null);
  };

  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className="text-sm leading-relaxed" style={{ color: "var(--si-text-secondary)" }}>
          Your Unified Intelligence Feed. SocialMonitor consolidates fragmented data into actionable growth levers.
        </p>
      </div>

      <div className="relative w-full">
        <input
          className="w-full rounded-xl py-3 pl-11 pr-4 text-sm outline-none"
          style={{
            backgroundColor: "var(--si-surface-elevated)",
            color: "var(--si-text-primary)",
            border: "1px solid var(--si-border)",
          }}
          placeholder={t("subjects.search")}
          type="text"
          value={searchQuery}
          onChange={(e) => handleSearch(e.target.value)}
        />
        <span
          className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-lg"
          style={{ color: "var(--si-text-tertiary)" }}
        >
          search
        </span>
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1">
        <button
          className="rounded-full px-3 py-1.5 text-xs font-medium whitespace-nowrap shrink-0"
          style={{
            backgroundColor: !filters.platform && !filters.status ? "var(--si-accent)" : "var(--si-surface-elevated)",
            color: !filters.platform && !filters.status ? "#ffffff" : "var(--si-text-secondary)",
          }}
          onClick={() => {
            setFilter("platform", null);
            setFilter("status", null);
            setSearchQuery("");
          }}
        >
          All Channels
        </button>
        <button
          className="rounded-full px-3 py-1.5 text-xs font-medium whitespace-nowrap shrink-0"
          style={{
            backgroundColor: filters.platform === "facebook" ? "var(--si-accent)" : "var(--si-surface-elevated)",
            color: filters.platform === "facebook" ? "#ffffff" : "var(--si-text-secondary)",
          }}
          onClick={() => {
            haptics.selection();
            setFilter("platform", filters.platform === "facebook" ? null : "facebook");
          }}
        >
          Facebook
        </button>
        <button
          className="rounded-full px-3 py-1.5 text-xs font-medium whitespace-nowrap shrink-0"
          style={{
            backgroundColor: filters.platform === "youtube" ? "var(--si-accent)" : "var(--si-surface-elevated)",
            color: filters.platform === "youtube" ? "#ffffff" : "var(--si-text-secondary)",
          }}
          onClick={() => {
            haptics.selection();
            setFilter("platform", filters.platform === "youtube" ? null : "youtube");
          }}
        >
          YouTube
        </button>
      </div>

      {isLoading && <LoadingSkeleton />}
      {isError && (
        <div className="flex flex-col items-center gap-3 py-12 text-center" role="alert">
          <span className="material-symbols-outlined text-4xl" style={{ color: "var(--si-danger)" }}>error</span>
          <p className="text-sm" style={{ color: "var(--si-text-primary)" }}>{error?.message ?? t("common.error")}</p>
          <button className="text-xs font-semibold" style={{ color: "var(--si-accent)" }} onClick={() => refetch()}>
            {t("common.retry")}
          </button>
        </div>
      )}

      {!isLoading && !isError && data && subjects.length === 0 && (
        <div className="flex flex-col items-center gap-3 py-12 text-center">
          <span className="material-symbols-outlined text-4xl" style={{ color: "var(--si-text-tertiary)" }}>search_off</span>
          <p className="text-sm" style={{ color: "var(--si-text-secondary)" }}>{t("subjects.noResults")}</p>
          <button
            className="text-xs font-semibold"
            style={{ color: "var(--si-accent)" }}
            onClick={() => {
              setFilter("platform", null);
              setFilter("status", null);
              setFilter("q", null);
              setSearchQuery("");
            }}
          >
            {t("subjects.resetFilters")}
          </button>
        </div>
      )}

      {subjects.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-3">
            <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--si-text-secondary)" }}>
              Intelligence Channels
            </h2>
            <span
              className="text-xs font-medium px-2 py-0.5 rounded-full"
              style={{ backgroundColor: "var(--si-accent-tint)", color: "var(--si-accent)" }}
            >
              {subjects.length} Active Connections
            </span>
          </div>

          <div className="flex flex-col gap-3">
            {subjects.map((subject) => {
              const color = platformColors[subject.platform] ?? "#666";
              const initial = platformInitials[subject.platform] ?? subject.platform[0]?.toUpperCase() ?? "?";
              const status = statusConfig[subject.status] ?? { variant: "neutral" as const, label: subject.status };
              const grayscale = subject.status === "suspended";

              return (
                <GlassCard
                  key={subject.id}
                  onClick={() => {
                    haptics.impact("light");
                    navigate(`/subjects/${subject.id}`);
                  }}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      {subject.extended_data?.avatar_url ? (
                        <img
                          src={subject.extended_data.avatar_url as string}
                          alt={subject.display_name}
                          className={`w-10 h-10 rounded-full object-cover shrink-0 ${grayscale ? "grayscale" : ""}`}
                        />
                      ) : (
                        <div
                          className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-lg shrink-0 ${grayscale ? "grayscale" : ""}`}
                          style={{ backgroundColor: color }}
                        >
                          {initial}
                        </div>
                      )}
                      <div className="min-w-0">
                        <h3 className="text-sm font-bold truncate" style={{ color: "var(--si-text-primary)" }}>
                          {subject.name}
                        </h3>
                        <p className="text-xs truncate" style={{ color: "var(--si-text-tertiary)" }}>
                          {formatCompact(subject.followers ?? 0)} followers
                          {" \u2022 "}
                          {formatRelative(subject.last_synced_at ?? new Date().toISOString())}
                        </p>
                      </div>
                    </div>
                    <StatusChip variant={status.variant} animate={subject.status === "active"}>
                      {status.label}
                    </StatusChip>
                  </div>

                  <div className="flex items-center justify-between mt-3 pt-3" style={{ borderTop: "1px solid var(--si-border)" }}>
                    <div className="flex items-center gap-4">
                      <div>
                        <p className="text-xs" style={{ color: "var(--si-text-tertiary)" }}>Velocity</p>
                        <p className="text-sm font-semibold" style={{ color: "var(--si-text-primary)" }}>
                          {subject.activity_frequency != null ? `${subject.activity_frequency}/d` : "-"}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs" style={{ color: "var(--si-text-tertiary)" }}>Growth</p>
                        <div className="flex items-center gap-1">
                          <div className="flex items-end gap-[2px] h-5">
                            {[4, 7, 3, 9, 5, 8, 6].map((h, i) => (
                              <div
                                key={i}
                                className="w-1 rounded-t-sm transition-all"
                                style={{
                                  height: `${h * 2}px`,
                                  backgroundColor: subject.status === "active" ? "var(--si-success)" : "var(--si-text-tertiary)",
                                }}
                              />
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {subject.status === "suspended" && (
                    <div className="mt-3 pt-3 flex items-center gap-2" style={{ borderTop: "1px solid var(--si-border)" }}>
                      <span className="material-symbols-outlined text-sm" style={{ color: "var(--si-danger)" }}>report</span>
                      <span className="text-xs font-medium" style={{ color: "var(--si-danger)" }}>
                        Compliance issues detected. Action required.
                      </span>
                    </div>
                  )}
                </GlassCard>
              );
            })}
          </div>

          <div ref={sentinelRef} className="flex justify-center py-3">
            {isFetchingNextPage && <Spinner size="md" />}
            {!hasNextPage && subjects.length > 0 && (
              <span className="text-xs" style={{ color: "var(--si-text-tertiary)" }}>
                {subjects.length} {t("subjects.loaded", { count: subjects.length })}
              </span>
            )}
          </div>
        </section>
      )}
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="flex flex-col gap-3" aria-busy="true" role="status">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="rounded-2xl p-4" style={{ backgroundColor: "var(--si-surface)", border: "1px solid var(--si-border)" }}>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full shrink-0" style={{ backgroundColor: "var(--si-surface-elevated)" }} />
            <div className="flex-1 space-y-2">
              <div className="h-4 w-40 rounded" style={{ backgroundColor: "var(--si-surface-elevated)" }} />
              <div className="h-3 w-28 rounded" style={{ backgroundColor: "var(--si-surface-elevated)" }} />
            </div>
            <div className="h-6 w-20 rounded-full" style={{ backgroundColor: "var(--si-surface-elevated)" }} />
          </div>
        </div>
      ))}
    </div>
  );
}
