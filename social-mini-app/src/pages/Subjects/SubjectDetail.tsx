import { useEffect } from "react";
import { useParams } from "react-router-dom";
import { useActivity, useSubject, useTriggerSync, useVideos } from "../../api/hooks";
import { ActivityFrequencyChart } from "../../components/charts/ActivityFrequencyChart";
import { AlertConfigPanel } from "../../components/panels/AlertConfigPanel";
import { AlertHistoryPanel } from "../../components/panels/AlertHistoryPanel";
import { FacebookEngagementPanel } from "../../components/panels/FacebookEngagementPanel";
import { FollowerChart } from "../../components/charts/FollowerChart";
import { TikTokEngagementPanel } from "../../components/panels/TikTokEngagementPanel";
import { YouTubeEngagementPanel } from "../../components/panels/YouTubeEngagementPanel";
import { GlassCard } from "../../components/ui/GlassCard";
import { StatusChip } from "../../components/ui/StatusChip";
import { Button } from "../../components/ui/Button";
import { Section } from "../../components/ui/Section";
import { PageHeader } from "../../components/ui/PageHeader";
import { useTelegram } from "../../telegram/useTelegram";
import { useTheme } from "../../theme/ThemeProvider";
import { useTranslation } from "../../i18n";
import { formatCompact, formatRelative } from "../../utils/format";

const platformColors: Record<string, string> = {
  facebook: "#1877f2",
  youtube: "#ff0000",
  tiktok: "#000000",
};

const platformInitials: Record<string, string> = {
  facebook: "F",
  youtube: "Y",
  tiktok: "T",
};

const statusConfig: Record<string, { variant: "success" | "warning" | "danger"; label: string }> = {
  active: { variant: "success", label: "Active" },
  inactive: { variant: "warning", label: "Inactive" },
  suspended: { variant: "danger", label: "Suspended" },
};

export default function SubjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { back, haptics, closing } = useTelegram();
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

  if (isLoading) {
    return (
      <>
        <PageHeader icon="school" title="Loading..." />
        <div className="space-y-3" aria-busy="true" role="status">
          <div
            className="rounded-xl p-4"
            style={{ backgroundColor: "var(--si-surface)", border: "1px solid var(--si-border)" }}
          >
            <div className="flex items-center gap-4">
              <div
                className="w-16 h-16 rounded-full shrink-0"
                style={{ backgroundColor: "var(--si-surface-highest)" }}
              />
              <div className="flex-1 space-y-2">
                <div className="h-5 w-40 rounded" style={{ backgroundColor: "var(--si-surface-highest)" }} />
                <div className="h-4 w-24 rounded" style={{ backgroundColor: "var(--si-surface-highest)" }} />
              </div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="h-24 rounded-xl"
                style={{ backgroundColor: "var(--si-surface)", border: "1px solid var(--si-border)" }}
              />
            ))}
          </div>
        </div>
      </>
    );
  }

  if (isError) {
    return (
      <>
        <PageHeader icon="school" title="Error" />
        <div className="flex flex-col items-center gap-3 py-12 text-center" role="alert">
          <span className="material-symbols-outlined text-4xl" style={{ color: "var(--si-danger)" }}>error</span>
          <p className="text-sm" style={{ color: "var(--si-text-primary)" }}>{error?.message ?? t("subject.error")}</p>
          <Button variant="secondary" onClick={() => refetch()}>{t("common.retry")}</Button>
        </div>
      </>
    );
  }

  if (!subject) {
    return (
      <>
        <PageHeader icon="school" title="Not found" />
        <div className="flex flex-col items-center py-12 text-center">
          <span className="material-symbols-outlined text-4xl" style={{ color: "var(--si-outline)" }}>person_off</span>
          <p className="text-sm mt-4" style={{ color: "var(--si-text-secondary)" }}>Subject not found</p>
        </div>
      </>
    );
  }

  const status = statusConfig[subject.status] ?? { variant: "neutral" as const, label: subject.status };
  const platformColor = platformColors[subject.platform] ?? "#666";
  const initial = platformInitials[subject.platform] ?? subject.platform[0]?.toUpperCase() ?? "?";
  const accentColor = isDark ? "#9dcaff" : "#005f9e";
  const avatarUrl = subject.extended_data?.avatar_url as string | undefined;

  return (
    <>
      <PageHeader
        icon="school"
        title={subject.display_name}
        actions={
          <button className="active:scale-95 transition-transform p-1">
            <span className="material-symbols-outlined" style={{ color: "var(--si-accent)" }}>search</span>
          </button>
        }
      />

      {/* Identity Card */}
      <div className="mb-6">
        <GlassCard>
          <div className="flex items-center gap-4">
            <div
              className="relative w-16 h-16 flex items-center justify-center rounded-full text-white font-bold text-2xl shadow-sm overflow-hidden shrink-0"
              style={{ backgroundColor: "var(--si-surface-elevated)" }}
            >
              {avatarUrl ? (
                <img src={avatarUrl} alt={subject.display_name} className="w-full h-full object-cover" />
              ) : (
                initial
              )}
              <div
                className="absolute bottom-1 right-1 w-3.5 h-3.5 border-2 rounded-full"
                style={{ backgroundColor: platformColor, borderColor: "var(--si-surface)" }}
              />
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold" style={{ color: "var(--si-text-primary)" }}>{subject.display_name}</h2>
                <StatusChip variant={status.variant} animate={subject.status === "active"}>
                  {t(`subject.${subject.status}`)}
                </StatusChip>
              </div>
              <p className="text-sm flex items-center gap-1 mt-0.5" style={{ color: "var(--si-text-secondary)" }}>
                <span className="material-symbols-outlined text-[16px]">public</span>
                {subject.platform === "facebook" ? "Facebook" : subject.platform === "youtube" ? "YouTube" : "TikTok"} 
              </p>
            </div>
          </div>
        </GlassCard>
      </div>

      {/* Key Metrics */}
      <Section title={t("subject.metrics")} className="mb-6">
        <div className="grid grid-cols-2 gap-3">
          <GlassCard>
            <span className="material-symbols-outlined text-[20px]" style={{ color: "var(--si-accent)" }}>group</span>
            <p className="text-xs font-medium mt-1" style={{ color: "var(--si-text-tertiary)" }}>{t("subject.followers")}</p>
            <p className="text-xl font-semibold" style={{ color: "var(--si-text-primary)" }}>{formatCompact(subject.followers)}</p>
          </GlassCard>
          <GlassCard>
            <span className="material-symbols-outlined text-[20px]" style={{ color: "var(--si-accent)" }}>post_add</span>
            <p className="text-xs font-medium mt-1" style={{ color: "var(--si-text-tertiary)" }}>{t("subject.posts")}</p>
            <p className="text-xl font-semibold" style={{ color: "var(--si-text-primary)" }}>{formatCompact(subject.post_count)}</p>
          </GlassCard>
          <GlassCard>
            <span className="material-symbols-outlined text-[20px]" style={{ color: "var(--si-accent)" }}>show_chart</span>
            <p className="text-xs font-medium mt-1" style={{ color: "var(--si-text-tertiary)" }}>{t("subject.activity")}</p>
            <p className="text-xl font-semibold" style={{ color: "var(--si-text-primary)" }}>{subject.activity_frequency.toFixed(1)}/d</p>
          </GlassCard>
          <GlassCard>
            <span className="material-symbols-outlined text-[20px]" style={{ color: "var(--si-accent)" }}>sync</span>
            <p className="text-xs font-medium mt-1" style={{ color: "var(--si-text-tertiary)" }}>{t("subject.lastSync")}</p>
            <p className="text-xl font-semibold" style={{ color: "var(--si-text-primary)" }}>{formatRelative(subject.last_synced_at)}</p>
          </GlassCard>
        </div>
      </Section>

      {/* Engagement Panel */}
      {subject.platform === "youtube" ? (
        <div className="mb-6"><YouTubeEngagementPanel subject={subject} /></div>
      ) : subject.platform === "tiktok" ? (
        <div className="mb-6"><TikTokEngagementPanel subject={subject} /></div>
      ) : (
        <div className="mb-6"><FacebookEngagementPanel subject={subject} /></div>
      )}

      {/* Charts */}
      {activity && activity.length > 0 && (
        <Section className="mb-6 space-y-4">
          <GlassCard>
            <h3 className="text-xs font-medium font-semibold mb-4" style={{ color: "var(--si-text-primary)" }}>{t("subject.followerGrowth")}</h3>
            <FollowerChart data={activity} accentColor={accentColor} />
          </GlassCard>
          <GlassCard>
            <h3 className="text-xs font-medium font-semibold mb-4" style={{ color: "var(--si-text-primary)" }}>{t("subject.activityFrequency")}</h3>
            <ActivityFrequencyChart data={activity} accentColor={accentColor} />
          </GlassCard>
        </Section>
      )}

      {/* YouTube Videos */}
      {subject.platform === "youtube" && (
        <Section title={t("video.title")} className="mb-6">
          {videosLoading ? (
            <p className="text-sm" style={{ color: "var(--si-text-secondary)" }}>{t("video.loading")}</p>
          ) : !videos || videos.length === 0 ? (
            <p className="text-sm" style={{ color: "var(--si-text-secondary)" }}>{t("video.noVideos")}</p>
          ) : (
            <div className="space-y-2">
              {videos.map((video) => (
                <a
                  key={video.id ?? video.platform_video_id}
                  href={`https://www.youtube.com/watch?v=${video.platform_video_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block no-underline"
                  onClick={() => haptics.impact("light")}
                >
                  <GlassCard>
                    <div className="flex gap-3">
                      {video.thumbnail_url && (
                        <img
                          src={video.thumbnail_url}
                          alt={video.title}
                          className="w-24 h-16 rounded-lg object-cover shrink-0"
                          loading="lazy"
                        />
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium leading-tight line-clamp-2" style={{ color: "var(--si-text-primary)" }}>{video.title}</p>
                        <p className="text-xs mt-1" style={{ color: "var(--si-text-tertiary)" }}>
                          {t("video.views", { count: formatCompact(video.view_count) })} &middot; {formatRelative(video.published_at)}
                        </p>
                        <div className="flex gap-3 mt-1">
                          <span className="text-xs" style={{ color: "var(--si-text-tertiary)" }}>
                            {t("video.likes", { count: formatCompact(video.like_count) })}
                          </span>
                          <span className="text-xs" style={{ color: "var(--si-text-tertiary)" }}>
                            {t("video.comments", { count: formatCompact(video.comment_count) })}
                          </span>
                        </div>
                      </div>
                    </div>
                  </GlassCard>
                </a>
              ))}
            </div>
          )}
        </Section>
      )}

      {/* Alerts */}
      <Section title={t("subject.alerts")} className="mb-6">
        <GlassCard className="mb-3">
          <AlertConfigPanel subjectId={id!} haptics={haptics} />
        </GlassCard>
        <AlertHistoryPanel subjectId={id!} />
      </Section>

      {/* Sync Button */}
      <div className="fixed bottom-0 left-0 right-0 p-4 z-40"
        style={{ backgroundColor: "color-mix(in srgb, var(--si-surface) 90%, transparent)" }}
      >
        <div className="max-w-[480px] mx-auto">
          <Button
            fullWidth
            size="lg"
            loading={syncMutation.isPending}
            onClick={() => {
              haptics.impact("medium");
              syncMutation.mutate(id!);
            }}
          >
            <span className="material-symbols-outlined text-lg" style={{ animation: syncMutation.isPending ? "spin 1s linear infinite" : undefined }}>
              sync
            </span>
            {syncMutation.isPending ? t("subject.syncing") : t("subject.syncNow")}
          </Button>
          {syncMutation.isSuccess && (
            <p className="text-xs text-center mt-2" style={{ color: "var(--si-text-tertiary)" }} role="status">
              {t("subject.syncScheduled", { taskId: syncMutation.data?.task_id?.slice(0, 8) ?? "" })}
            </p>
          )}
          {syncMutation.isError && (
            <p className="text-xs text-center mt-2" style={{ color: "var(--si-danger)" }} role="alert">
              {t("subject.syncFailed")}
            </p>
          )}
        </div>
      </div>
    </>
  );
}
