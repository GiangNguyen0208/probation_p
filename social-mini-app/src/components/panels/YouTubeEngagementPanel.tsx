import { useTranslation } from "../../i18n";
import { Section } from "../ui/Section";
import { MetricCard } from "../ui/MetricCard";
import { formatCompact } from "../../utils/format";
import { castYouTubeExtended } from "../../types/extended-data";
import type { components } from "../../api/types";

type Subject = components["schemas"]["Subject"];

export function YouTubeEngagementPanel({ subject }: { subject: Subject }) {
  const { t } = useTranslation();
  const ext = castYouTubeExtended(subject.extended_data);
  if (!ext || ext.view_count === undefined) {
    return null;
  }

  const engagementRate =
    ext.sample_engagement_rate !== undefined
      ? `${(ext.sample_engagement_rate * 100).toFixed(1)}%`
      : "\u2014";

  const showExtra = ext.sample_like_count !== undefined || ext.sample_comment_count !== undefined;

  return (
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
  );
}
