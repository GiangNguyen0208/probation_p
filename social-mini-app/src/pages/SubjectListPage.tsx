import { useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { FilterBar } from "../components/subject/FilterBar";
import StateViews from "../components/state/StateViews";
import { SubjectCard } from "../components/subject/SubjectCard";
import { useInfiniteSubjects } from "../api/hooks";
import type { SubjectFilters } from "../api/hooks";
import { useTranslation } from "../i18n";
import { useTelegram } from "../telegram/useTelegram";
import { PageHeader } from "../components/ui/PageHeader";
import { Spinner } from "../components/ui/Spinner";

export default function SubjectListPage() {
  const navigate = useNavigate();
  const { haptics } = useTelegram();
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const sentinelRef = useRef<HTMLDivElement>(null);

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

  return (
    <div className="flex flex-col gap-3">
      <PageHeader title={t("subjects.title")} />

      <FilterBar
        platform={filters.platform ?? null}
        status={filters.status ?? null}
        q={filters.q ?? null}
        onFilterChange={setFilter}
        haptics={haptics}
      />

      {isLoading && <StateViews.Loading />}
      {isError && (
        <StateViews.Error
          message={error?.message ?? t("common.error")}
          retry={() => refetch()}
          retryLabel={t("common.retry")}
        />
      )}
      {!isLoading && !isError && data && subjects.length === 0 && (
          <StateViews.Empty
            message={t("subjects.noResults")}
            action={() => {
              setFilter("platform", null);
              setFilter("status", null);
              setFilter("q", null);
            }}
            actionLabel={t("subjects.resetFilters")}
          />
      )}

      {subjects.length > 0 && (
        <>
          <div className="flex flex-col gap-2" role="list" aria-label="Subjects">
            {subjects.map((subject) => (
              <div role="listitem" key={subject.id}>
                <SubjectCard
                  subject={subject}
                  onClick={() => {
                    haptics.impact("light");
                    navigate(`/subjects/${subject.id}`);
                  }}
                  haptics={haptics}
                />
              </div>
            ))}
          </div>

          <div ref={sentinelRef} className="flex justify-center py-3">
            {isFetchingNextPage && <Spinner size="md" />}
            {!hasNextPage && (
              <span
                className="text-xs"
                style={{ color: "var(--tg-hint-color)" }}
              >
                {subjects.length} subject{subjects.length !== 1 ? "s" : ""} loaded
              </span>
            )}
          </div>
        </>
      )}
    </div>
  );
}
