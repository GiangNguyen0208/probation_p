import { useNavigate } from "react-router-dom";
import { useDashboardStats } from "../api/hooks";
import StateViews from "../components/state/StateViews";
import { useTranslation } from "../i18n";
import { useTelegram } from "../telegram/useTelegram";
import { formatCompact, formatRelative } from "../utils/format";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { PageHeader } from "../components/ui/PageHeader";
import { Section } from "../components/ui/Section";

export default function DashboardPage() {
  const navigate = useNavigate();
  const { haptics } = useTelegram();
  const { t } = useTranslation();
  const { data, isLoading, isError, error, refetch } = useDashboardStats();

  if (isLoading) return <StateViews.Loading count={2} />;
  if (isError) {
    return (
      <StateViews.Error
        message={error?.message ?? t("common.error")}
        retry={() => refetch()}
        retryLabel={t("common.retry")}
      />
    );
  }
  if (!data) return <StateViews.Empty />;

  return (
    <div className="flex flex-col gap-3">
      <PageHeader title={t("dashboard.title")} />

      <Section title={t("dashboard.overview")}>
        <div className="grid grid-cols-2 gap-2" role="region" aria-label={t("dashboard.overview")}>
          <KpiCard
            label={t("dashboard.totalSubjects")}
            value={formatCompact(data.totalSubjects)}
            accent
          />
          <KpiCard
            label={t("dashboard.mostActive")}
            value={
              data.mostActivePlatform === "facebook" ? t("dashboard.facebook")
                : data.mostActivePlatform === "youtube" ? t("dashboard.youtube")
                : t("dashboard.tiktok")
            }
            subtitle={
              t("dashboard.tracked", {
                count: formatCompact(
                  data.mostActivePlatform === "facebook"
                    ? data.facebookCount
                    : data.mostActivePlatform === "youtube"
                    ? data.youtubeCount
                    : data.tiktokCount ?? 0,
                ),
              })
            }
          />
          <KpiCard
            label={t("dashboard.facebook")}
            value={formatCompact(data.facebookCount)}
          />
          <KpiCard
            label={t("dashboard.youtube")}
            value={formatCompact(data.youtubeCount)}
          />
          <KpiCard
            label={t("dashboard.tiktok")}
            value={formatCompact(data.tiktokCount ?? 0)}
          />
        </div>
      </Section>

      {data.lastSyncTimestamp && (
        <Card className="text-center">
          <p className="text-xs" style={{ color: "var(--tg-hint-color)" }}>
            {t("dashboard.lastSync", { time: formatRelative(data.lastSyncTimestamp) })}
          </p>
        </Card>
      )}

      <Button
        variant="secondary"
        fullWidth
        onClick={() => {
          haptics.impact("light");
          navigate("/");
        }}
      >
        {t("dashboard.browseSubjects")}
      </Button>
    </div>
  );
}

function KpiCard({
  label,
  value,
  subtitle,
  accent,
}: {
  label: string;
  value: string;
  subtitle?: string;
  accent?: boolean;
}) {
  return (
    <Card className="!p-4">
      <p className="text-xs" style={{ color: "var(--tg-hint-color)" }}>
        {label}
      </p>
      <p
        className="text-2xl font-bold mt-1"
        style={{
          color: accent
            ? "var(--tg-accent-text-color)"
            : "var(--tg-text-color)",
        }}
      >
        {value}
      </p>
      {subtitle && (
        <p
          className="text-xs mt-1"
          style={{ color: "var(--tg-subtitle-text-color)" }}
        >
          {subtitle}
        </p>
      )}
    </Card>
  );
}