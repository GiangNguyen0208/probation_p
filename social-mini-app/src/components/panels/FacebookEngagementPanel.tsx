import { useMemo } from "react";
import { resolveColor } from "../../utils/format";
import { useTranslation } from "../../i18n";
import type { TranslationKey } from "../../i18n";
import { Section } from "../ui/Section";
import { Sparkline } from "../ui/Sparkline";
import { formatCompact } from "../../utils/format";
import { castFacebookExtended, getMetricLatestValue, getMetricSparklineData } from "../../types/extended-data";
import type { InsightMetric } from "../../types/extended-data";
import type { components } from "../../api/types";

type Subject = components["schemas"]["Subject"];

const DISPLAY_METRICS = [
  { key: "page_media_view", labelKey: "insights.impressions" },
  { key: "page_total_media_view_unique", labelKey: "insights.reach" },
  { key: "page_views_total", labelKey: "insights.pageViews" },
  { key: "page_post_engagements", labelKey: "insights.engagements" },
  { key: "page_actions_post_reactions_total", labelKey: "insights.reactions" },
  { key: "page_video_views", labelKey: "insights.videoViews" },
  { key: "page_total_actions", labelKey: "insights.totalActions" },
  { key: "page_daily_follows", labelKey: "insights.dailyFollows" },
  { key: "page_daily_follows_unique", labelKey: "insights.follows" },
  { key: "page_daily_unfollows_unique", labelKey: "insights.unfollows" },
  { key: "page_follows", labelKey: "insights.pageFans" },
] as const;

function InsightCard({ metric, label }: { metric?: InsightMetric; label: string }) {
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
        <Sparkline data={sparklineData} color={accentColor} />
      )}
    </div>
  );
}

export function FacebookEngagementPanel({ subject }: { subject: Subject }) {
  const { t } = useTranslation();
  const ext = castFacebookExtended(subject.extended_data);
  const insights = ext?.insights;

  const visibleMetrics = useMemo(
    () => DISPLAY_METRICS.filter((m) => insights?.[m.key]?.values?.length),
    [insights],
  );

  if (!insights || visibleMetrics.length === 0) {
    return null;
  }

  return (
    <Section title={t("insights.title")}>
      <div className="grid grid-cols-2 gap-2" role="region" aria-label={t("insights.title")}>
        {visibleMetrics.map((m) => (
          <InsightCard
            key={m.key}
            metric={insights[m.key]}
            label={t(m.labelKey as TranslationKey)}
          />
        ))}
      </div>
    </Section>
  );
}
