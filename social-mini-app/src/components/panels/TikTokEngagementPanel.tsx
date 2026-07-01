import { useTranslation } from "../../i18n";
import { Section } from "../ui/Section";
import { MetricCard } from "../ui/MetricCard";
import { formatCompact } from "../../utils/format";
import { castTikTokExtended } from "../../types/extended-data";
import type { components } from "../../api/types";

type Subject = components["schemas"]["Subject"];

export function TikTokEngagementPanel({ subject }: { subject: Subject }) {
  const { t } = useTranslation();
  const ext = castTikTokExtended(subject.extended_data);

  return (
    <Section title={t("engagement.section")}>
      <div className="grid grid-cols-2 gap-2" role="region" aria-label={t("engagement.section")}>
        <MetricCard label={t("insights.tiktokFollowers")} value={formatCompact(subject.followers)} />
        <MetricCard label={t("insights.tiktokFollowing")} value={formatCompact(ext?.following_count ?? 0)} />
        <MetricCard label={t("insights.tiktokLikes")} value={formatCompact(ext?.likes_count ?? 0)} />
        <MetricCard label={t("insights.tiktokVideos")} value={formatCompact(ext?.video_count ?? 0)} />
      </div>
    </Section>
  );
}
