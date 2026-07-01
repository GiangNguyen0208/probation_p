import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useInfiniteSubjects } from "../../api/hooks";
import type { SubjectFilters } from "../../api/hooks";
import { StatusChip } from "../../components/ui/StatusChip";
import { Spinner } from "../../components/ui/Spinner";
import { useTranslation } from "../../i18n";
import { useTelegram } from "../../telegram/useTelegram";
import { formatCompact, formatRelative } from "../../utils/format";
import { FilterChip } from "@/pages/SubjectList/FilterChip";

const platformInitials: Record<string, string> = {
  facebook: "F",
  youtube: "Y",
  tiktok: "T",
};

const platformColors: Record<string, string> = {
  facebook: "#1877f2",
  youtube: "#ff0000",
  tiktok: "#000000",
};

const statusConfig: Record<string, { variant: "success" | "warning" | "danger" | "neutral"; label: string }> = {
  active: { variant: "success", label: "High Impact" },
  inactive: { variant: "neutral", label: "Inactive" },
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

  const filterChips = [
    {
      label: "All Channels",
      isActive: !filters.platform && !filters.status,
      onClick: () => {
        setFilter("platform", null);
        setFilter("status", null);
        setSearchQuery("");
      },
    },
    {
      label: "High Growth",
      isActive: filters.status === "active",
      onClick: () => {
        haptics.selection();
        setFilter("status", filters.status === "active" ? null : "active");
      },
    },
    {
      label: "Facebook",
      isActive: filters.platform === "facebook",
      onClick: () => {
        haptics.selection();
        setFilter("platform", filters.platform === "facebook" ? null : "facebook");
      },
    },
    {
      label: "YouTube",
      isActive: filters.platform === "youtube",
      onClick: () => {
        haptics.selection();
        setFilter("platform", filters.platform === "youtube" ? null : "youtube");
      },
    },
    {
      label: "Tiktok",
      isActive: filters.platform === "tiktok",
      onClick: () => {
        haptics.selection();
        setFilter("platform", filters.platform === "tiktok" ? null : "tiktok");
      },
    },
  ];

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
      {/* Header Section */}
      <section className="flex flex-col gap-2">
        <h2 className="text-2xl font-bold leading-tight" style={{ color: "var(--si-text-primary)" }}>
          Intelligence Feed.
        </h2>
        <p className="text-sm" style={{ color: "var(--si-text-secondary)" }}>
          SocialMonitor consolidates fragmented data into{" "}
          <span className="font-semibold" style={{ color: "var(--si-accent)" }}>actionable growth levers</span>.
        </p>
      </section>

      {/* Filter & Search Section */}
      <section className="flex flex-col gap-3">
        <div className="relative w-full">
          <input
            className="w-full rounded-xl py-3 pl-11 pr-4 text-sm outline-none"
            style={{
              backgroundColor: "var(--si-surface-low)",
              color: "var(--si-text-primary)",
              boxShadow: "0 1px 2px 0 rgb(0 0 0 / 0.05)",
            }}
            placeholder="Filter intelligence channels..."
            type="text"
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
          />
          <span
            className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-lg"
            style={{ color: "var(--si-outline)" }}
          >
            filter_list
          </span>
        </div>

        <div className="flex gap-2 overflow-x-auto pb-1 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
          {filterChips.map((chip) => (
            <FilterChip key={chip.label} {...chip} />
          ))}
        </div>
      </section>

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
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--si-text-secondary)" }}>
              Intelligence Channels
            </h2>
            <span
              className="text-xs font-medium"
              style={{ color: "var(--si-accent)" }}
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
              const isActive = subject.status === "active";
              const isInactive = subject.status === "inactive";
              const isSuspended = subject.status === "suspended";

              // Card container styles based on status
              const cardContainerStyle: React.CSSProperties = isActive
                ? {
                    borderLeft: "4px solid var(--si-success)",
                    backgroundColor: "var(--si-surface)",
                    border: "1px solid var(--si-border)",
                  }
                : isInactive
                  ? {
                      backgroundColor: "var(--si-surface-low)",
                      border: "1px solid color-mix(in srgb, var(--si-border) 30%, transparent)",
                      opacity: 0.6,
                    }
                  : isSuspended
                    ? {
                        backgroundColor: "color-mix(in srgb, var(--si-error-container) 10%, transparent)",
                        border: "1px solid color-mix(in srgb, var(--si-danger) 30%, transparent)",
                      }
                    : {
                        backgroundColor: "var(--si-surface)",
                        border: "1px solid var(--si-border)",
                      };

              return (
                <div
                  key={subject.id}
                  className="rounded-2xl p-4 flex flex-col gap-3 cursor-pointer transition-all active:scale-[0.98]"
                  style={cardContainerStyle}
                  onClick={() => {
                    haptics.impact("light");
                    navigate(`/subjects/${subject.id}`);
                  }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      {subject.extended_data?.avatar_url ? (
                        <img
                          src={subject.extended_data.avatar_url as string}
                          alt={subject.display_name}
                          className={`w-10 h-10 rounded-xl object-cover shrink-0 ${grayscale ? "grayscale" : ""}`}
                        />
                      ) : (
                        <div
                          className={`w-10 h-10 rounded-xl flex items-center justify-center text-white font-bold text-lg shrink-0 ${grayscale ? "grayscale" : ""}`}
                          style={{ backgroundColor: color }}
                        >
                          {initial}
                        </div>
                      )}
                      <div className="flex flex-col min-w-0">
                        <span className="text-sm font-bold truncate" style={{ color: isSuspended ? "var(--si-danger)" : "var(--si-text-primary)" }}>
                          {subject.name}
                        </span>
                        <span className="text-xs truncate" style={{ color: "var(--si-text-tertiary)" }}>
                          {formatCompact(subject.followers ?? 0)} followers{" "}{"\u2022"}{" "}{formatRelative(subject.last_synced_at ?? new Date().toISOString())}
                        </span>
                      </div>
                    </div>
                    <StatusChip variant={status.variant} animate={isActive}>
                      {status.label}
                    </StatusChip>
                  </div>

                  {/* Velocity + Growth section */}
                  <div className="flex items-center justify-between pt-2" style={{ borderTop: "1px solid color-mix(in srgb, var(--si-border) 20%, transparent)" }}>
                    <div className="flex flex-col">
                      <span className="text-xs" style={{ color: "var(--si-text-tertiary)" }}>Velocity</span>
                      {isInactive ? (
                        <span className="text-lg font-bold" style={{ color: "var(--si-text-tertiary)" }}>
                          {subject.activity_frequency != null ? `${subject.activity_frequency.toFixed(1)}` : "0.0"}
                          <span className="text-xs font-normal">/d</span>
                        </span>
                      ) : (
                        <span className="text-lg font-bold" style={{ color: isSuspended ? "var(--si-text-tertiary)" : "var(--si-text-primary)" }}>
                          {subject.activity_frequency != null ? `${subject.activity_frequency.toFixed(1)}` : "0.0"}
                          <span className="text-xs font-normal" style={{ color: "var(--si-text-tertiary)" }}>/d</span>
                        </span>
                      )}
                    </div>
                    <div className="flex flex-col items-end">
                      {isInactive ? (
                        <>
                          <span className="text-xs" style={{ color: "var(--si-text-tertiary)" }}>Status</span>
                          <span className="text-xs font-medium italic" style={{ color: "var(--si-text-tertiary)" }}>Dormant</span>
                        </>
                      ) : isSuspended ? null : (
                        <>
                          <span className="text-xs mb-1" style={{ color: "var(--si-text-tertiary)" }}>Growth Curve</span>
                          <div className="flex items-end gap-[2px] h-5">
                            {[4, 7, 3, 9, 5, 8, 6].map((h, i) => (
                              <div
                                key={i}
                                className="w-1 rounded-t-sm transition-all"
                                style={{
                                  height: `${h * 2}px`,
                                  backgroundColor: isActive ? "var(--si-success)" : "var(--si-text-tertiary)",
                                }}
                              />
                            ))}
                          </div>
                        </>
                      )}
                    </div>
                  </div>

                  {isSuspended && (
                    <div className="flex items-center gap-2">
                      <span className="material-symbols-outlined text-sm" style={{ color: "var(--si-danger)" }}>report</span>
                      <span className="text-xs font-medium" style={{ color: "var(--si-danger)" }}>
                        Compliance issues detected. Action required.
                      </span>
                    </div>
                  )}
                </div>
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
        <div key={i} className="rounded-2xl p-4" style={{ backgroundColor: "var(--si-surface)", border: "1px solid var(--si-border)", borderLeft: "4px solid var(--si-border)" }}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl shrink-0" style={{ backgroundColor: "var(--si-surface-elevated)" }} />
              <div className="flex flex-col gap-1">
                <div className="h-4 w-40 rounded" style={{ backgroundColor: "var(--si-surface-elevated)" }} />
                <div className="h-3 w-28 rounded" style={{ backgroundColor: "var(--si-surface-elevated)" }} />
              </div>
            </div>
            <div className="h-6 w-20 rounded-full" style={{ backgroundColor: "var(--si-surface-elevated)" }} />
          </div>
        </div>
      ))}
    </div>
  );
}
