import { useEffect } from "react";
import { useParams } from "react-router-dom";
import { useActivity, useSubject, useTriggerSync, useVideos } from "../api/hooks";
import { ActivityFrequencyChart } from "../components/charts/ActivityFrequencyChart";
import { AlertConfigPanel } from "../components/panels/AlertConfigPanel";
import { AlertHistoryPanel } from "../components/panels/AlertHistoryPanel";
import { FacebookEngagementPanel } from "../components/panels/FacebookEngagementPanel";
import { FollowerChart } from "../components/charts/FollowerChart";
import { TikTokEngagementPanel } from "../components/panels/TikTokEngagementPanel";
import { YouTubeEngagementPanel } from "../components/panels/YouTubeEngagementPanel";
import StateViews from "../components/state/StateViews";
import { useTelegram } from "../telegram/useTelegram";
import { useTheme } from "../theme/ThemeProvider";
import { useTranslation } from "../i18n";
import { formatCompact, formatRelative } from "../utils/format";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { MetricCard } from "../components/ui/MetricCard";
import { Section } from "../components/ui/Section";

const platformColors: Record<string, string> = {
  facebook: "#1877f2",
  youtube: "#ff0000",
  tiktok: "#000000",
};

const statusVariant: Record<string, "success" | "warning" | "danger"> = {
  active: "success",
  inactive: "warning",
  suspended: "danger",
};

export default function SubjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { back, theme, haptics, closing } = useTelegram();
  const { isDark } = useTheme();
  const { data: subject, isLoading, isError, error, refetch } = useSubject(id!);
  const { data: activity } = useActivity(id!);
  const { data: videos, isLoading: videosLoading } = useVideos(id!);
  const syncMutation = useTriggerSync();
  const { t } = useTranslation();

  useEffect(() => {
    if (subject) {
      back.show();
      return () => back.hide();
    }
  }, [subject, back]);

  useEffect(() => {
    const cb = () => window.history.back();
    back.onClick(cb);
    return () => back.offClick(cb);
  }, [back]);

  useEffect(() => {
    if (syncMutation.isPending) {
      closing.enableConfirmation();
      return () => closing.disableConfirmation();
    }
  }, [syncMutation.isPending, closing]);

  if (isLoading) return <StateViews.Loading />;
  if (isError) {
    return (
      <StateViews.Error
        message={error?.message ?? t("subject.error")}
        retry={() => refetch()}
        retryLabel={t("common.retry")}
      />
    );
  }
  if (!subject) return <StateViews.Empty />;

  const variant = statusVariant[subject.status] ?? "warning";
  const statusTKey = subject.status === "active" ? "subject.active"
    : subject.status === "inactive" ? "subject.inactive"
    : "subject.suspended";
  const platformColor = platformColors[subject.platform] ?? "#666";
  const accentColor = theme?.accentTextColor ?? (isDark ? "#6ab2f2" : "#2481cc");

  return (
    <div className="flex flex-col gap-3">
      <Section>
        <Card className="flex items-center gap-3">
          <div
            className="w-3 h-3 rounded-full shrink-0"
            style={{ backgroundColor: platformColor }}
            aria-hidden="true"
          />
          <div className="flex-1 min-w-0">
            <h2
              className="font-semibold text-base truncate"
              style={{ color: "var(--tg-text-color)" }}
            >
              {subject.display_name}
            </h2>
            <p className="text-xs" style={{ color: "var(--tg-hint-color)" }}>
              {subject.platform === "facebook" ? t("dashboard.facebook") : subject.platform === "youtube" ? t("dashboard.youtube") : t("dashboard.tiktok")} · {subject.platform_id}
            </p>
          </div>
          <Badge variant={variant}>{t(statusTKey)}</Badge>
        </Card>
      </Section>

      <Section title={t("subject.metrics")}>
        <div className="grid grid-cols-2 gap-2" role="region" aria-label={t("subject.metrics")}>
          <MetricCard label={t("subject.followers")} value={formatCompact(subject.followers)} />
          <MetricCard label={t("subject.posts")} value={formatCompact(subject.post_count)} />
          <MetricCard
            label={t("subject.activity")}
            value={`${subject.activity_frequency.toFixed(1)}/d`}
          />
          <MetricCard
            label={t("subject.lastSync")}
            value={formatRelative(subject.last_synced_at)}
          />
        </div>
      </Section>

      {subject.platform === "youtube" ? (
        <YouTubeEngagementPanel subject={subject} />
      ) : subject.platform === "tiktok" ? (
        <TikTokEngagementPanel subject={subject} />
      ) : (
        <FacebookEngagementPanel subject={subject} />
      )}

      {activity && activity.length > 0 && (
        <Section>
          <div className="flex flex-col gap-2">
            <FollowerChart data={activity} accentColor={accentColor} />
            <ActivityFrequencyChart data={activity} accentColor={accentColor} />
          </div>
        </Section>
      )}

      {subject.platform === "youtube" && (
        <Section title={t("video.title")}>
          {videosLoading ? (
            <p className="text-sm" style={{ color: "var(--tg-hint-color)" }}>
              {t("video.loading")}
            </p>
          ) : !videos || videos.length === 0 ? (
            <p className="text-sm" style={{ color: "var(--tg-hint-color)" }}>
              {t("video.noVideos")}
            </p>
          ) : (
            <div className="flex flex-col gap-2" role="region" aria-label={t("video.title")}>
              {videos.map((video) => (
                <a
                  key={video.id ?? video.platform_video_id}
                  href={`https://www.youtube.com/watch?v=${video.platform_video_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block no-underline"
                  onClick={() => haptics.impact("light")}
                >
                  <Card className="flex gap-3 !p-3">
                    {video.thumbnail_url && (
                      <img
                        src={video.thumbnail_url}
                        alt={video.title}
                        className="w-24 h-16 rounded object-cover shrink-0"
                        loading="lazy"
                      />
                    )}
                    <div className="flex-1 min-w-0">
                      <p
                        className="text-sm font-medium leading-tight line-clamp-2"
                        style={{ color: "var(--tg-text-color)" }}
                      >
                        {video.title}
                      </p>
                      <p
                        className="text-xs mt-1"
                        style={{ color: "var(--tg-hint-color)" }}
                      >
                        {t("video.views", { count: formatCompact(video.view_count) })} ·{" "}
                        {formatRelative(video.published_at)}
                      </p>
                      <div className="flex gap-3 mt-1">
                        <span
                          className="text-xs"
                          style={{ color: "var(--tg-hint-color)" }}
                        >
                          {t("video.likes", { count: formatCompact(video.like_count) })}
                        </span>
                        <span
                          className="text-xs"
                          style={{ color: "var(--tg-hint-color)" }}
                        >
                          {t("video.comments", { count: formatCompact(video.comment_count) })}
                        </span>
                      </div>
                    </div>
                  </Card>
                </a>
              ))}
            </div>
          )}
        </Section>
      )}

      <Section title={t("subject.alerts")}>
        <AlertConfigPanel subjectId={id!} haptics={haptics} />
        <AlertHistoryPanel subjectId={id!} />
      </Section>

      <Button
        fullWidth
        size="lg"
        loading={syncMutation.isPending}
        onClick={() => {
          haptics.impact("medium");
          syncMutation.mutate(id!);
        }}
      >
        {syncMutation.isPending ? t("subject.syncing") : t("subject.syncNow")}
      </Button>
      {syncMutation.isSuccess && (
        <p
          className="text-xs text-center"
          style={{ color: "var(--tg-hint-color)" }}
          role="status"
        >
          {t("subject.syncScheduled", { taskId: syncMutation.data?.task_id?.slice(0, 8) ?? "" })}
        </p>
      )}
      {syncMutation.isError && (
        <p
          className="text-xs text-center"
          style={{ color: "var(--tg-destructive-text-color)" }}
          role="alert"
        >
          {t("subject.syncFailed")}
        </p>
      )}
    </div>
  );
}



