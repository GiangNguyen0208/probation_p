import { useMemo } from "react";
import { useTranslation } from "../../i18n";
import type { TranslationKey } from "../../i18n";
import { Section } from "../ui/Section";
import { MetricCard } from "../ui/MetricCard";
import { formatCompact, resolveColor } from "../../utils/format";
import { castYouTubeExtended, getMetricLatestValue, getMetricSparklineData } from "../../types/extended-data";
import type { components } from "../../api/types";

type Subject = components["schemas"]["Subject"];

const ANALYTIC_DISPLAY = [
  { key: "views", labelKey: "insights.viewsPerDay" },
  { key: "subscribersGained", labelKey: "insights.subscribersGained" },
  { key: "likes", labelKey: "insights.likes" },
  { key: "comments", labelKey: "insights.comments" },
] as const;

function AnalyticCard({ metric, label }: { metric?: { name: string; title: string; values: { value: number; end_time: string }[] }; label: string }) {
  const latestValue = getMetricLatestValue(metric);
  const sparklineData = getMetricSparklineData(metric);
  const accentColor = resolveColor("--tg-accent-text-color", "#2481cc");

  return (
    <div className="flex flex-col gap-1 rounded-xl p-3" style={{ backgroundColor: "var(--tg-secondary-bg-color)" }}>
      <span className="text-xs" style={{ color: "var(--tg-hint-color)" }}>{label}</span>
      <span className="text-lg font-semibold" style={{ color: "var(--tg-text-color)" }}>
        {latestValue !== null ? formatCompact(latestValue) : "\u2014"}
      </span>
      {sparklineData.length > 1 && (
        <svg width={80} height={28} viewBox="0 0 80 28" className="w-full" preserveAspectRatio="none">
          {(() => {
            const max = Math.max(...sparklineData);
            const min = Math.min(...sparklineData);
            const range = max - min || 1;
            const bw = 80 / sparklineData.length;
            return sparklineData.map((v, i) => (
              <rect
                key={i}
                x={i * bw}
                y={28 - ((v - min) / range) * 28}
                width={Math.max(bw - 0.5, 1)}
                height={((v - min) / range) * 28}
                fill={accentColor}
                opacity={0.5}
                rx={1}
              />
            ));
          })()}
        </svg>
      )}
    </div>
  );
}

export function YouTubeEngagementPanel({ subject }: { subject: Subject }) {
  const { t } = useTranslation();
  const ext = castYouTubeExtended(subject.extended_data);
  const analytics = ext?.analytics;

  const visibleAnalytics = useMemo(
    () => ANALYTIC_DISPLAY.filter((m) => analytics?.some((a) => a.name === m.key)),
    [analytics],
  );
  const analyticsMap = useMemo(
    () => Object.fromEntries((analytics || []).map((a) => [a.name, a])),
    [analytics],
  );

  if (!ext || ext.view_count === undefined) {
    return null;
  }

  const engagementRate =
    ext.sample_engagement_rate !== undefined
      ? `${(ext.sample_engagement_rate * 100).toFixed(1)}%`
      : "\u2014";

  const showExtra = ext.sample_like_count !== undefined || ext.sample_comment_count !== undefined;

  return (
    <>
      <Section title={t("engagement.section")}>
        <div className="grid grid-cols-2 gap-2" role="region" aria-label={t("engagement.section")}>
          <MetricCard label={t("engagement.totalViews")} value={formatCompact(ext.view_count)} />
          <MetricCard label={t("engagement.avgEngRate")} value={engagementRate} />
          {showExtra && (
            <>
              {ext.sample_like_count !== undefined && (
                <MetricCard label="Likes" value={formatCompact(ext.sample_like_count)} />
              )}
              {ext.sample_comment_count !== undefined && (
                <MetricCard label="Comments" value={formatCompact(ext.sample_comment_count)} />
              )}
            </>
          )}
        </div>
      </Section>
      {visibleAnalytics.length > 0 && (
        <Section title={t("insights.title")}>
          <div className="grid grid-cols-2 gap-2">
            {visibleAnalytics.map((m) => (
              <AnalyticCard
                key={m.key}
                metric={analyticsMap[m.key]}
                label={t(m.labelKey as TranslationKey)}
              />
            ))}
          </div>
        </Section>
      )}
    </>
  );
}
