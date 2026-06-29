import { useAlertLogs } from "../../api/hooks";
import { useTranslation } from "../../i18n";
import type { components } from "../../api/types";
import StateViews from "../state/StateViews";
import { Card } from "../ui/Card";

type AlertLog = components["schemas"]["AlertLog"];

const RULE_LABELS: Record<string, string> = {
  follower_spike: "Follower Spike",
  follower_drop: "Follower Drop",
  activity_spike: "Activity Spike",
  activity_silence: "Activity Silence",
  status_change: "Status Change",
};

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function AlertHistoryPanel({ subjectId }: { subjectId: string }) {
  const { t } = useTranslation();
  const { data: logs, isLoading } = useAlertLogs(subjectId);

  if (isLoading) {
    return <StateViews.Loading />;
  }

  if (!logs || logs.length === 0) {
    return (
      <p
        className="text-xs mt-2"
        style={{ color: "var(--tg-hint-color)" }}
      >
        {t("alert.noLogs")}
      </p>
    );
  }

  return (
    <div className="mt-3 space-y-2">
      <h4
        className="text-xs font-semibold uppercase tracking-wide"
        style={{ color: "var(--tg-hint-color)" }}
      >
        {t("alert.historyTitle")}
      </h4>
      {logs.map((log: AlertLog) => (
        <Card key={log.id} className="p-3">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <p
                className="text-sm font-medium truncate"
                style={{ color: "var(--tg-text-color)" }}
              >
                {RULE_LABELS[log.rule_type] ?? log.rule_type}
              </p>
              <p
                className="text-xs mt-0.5"
                style={{ color: "var(--tg-hint-color)" }}
              >
                {formatTime(log.triggered_at)}
              </p>
              <p
                className="text-xs mt-1"
                style={{ color: "var(--tg-text-color)" }}
              >
                {log.message
                  .replace(/<[^>]*>/g, "")
                  .split("\n")
                  .slice(0, 3)
                  .join(" \u00b7 ")}
              </p>
            </div>
            <span
              className={`shrink-0 text-xs font-medium px-1.5 py-0.5 rounded ${
                log.delivered
                  ? "bg-[var(--tg-success-bg-color)] text-[var(--tg-success-text-color)]"
                  : "bg-[var(--tg-danger-bg-color)] text-[var(--tg-danger-text-color)]"
              }`}
            >
              {log.delivered ? "Sent" : "Failed"}
            </span>
          </div>
        </Card>
      ))}
    </div>
  );
}
