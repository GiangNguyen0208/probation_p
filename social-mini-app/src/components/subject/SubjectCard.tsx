import { useNavigate } from "react-router-dom";
import { formatCompact, formatRelative } from "../../utils/format";
import type { useTelegram } from "../../telegram/useTelegram";
import { Badge } from "../ui/Badge";
import {
  type Subject,
  platformColors,
  platformLabels,
  statusConfig,
} from "../../types/platform";

export function SubjectCard({
  subject,
  onClick,
  haptics,
}: {
  subject: Subject;
  onClick: () => void;
  haptics?: ReturnType<typeof useTelegram>["haptics"];
}) {
  const navigate = useNavigate();
  const platformColor = platformColors[subject.platform] ?? "#666";
  const platformInitial = (platformLabels[subject.platform] ?? subject.platform).charAt(0).toUpperCase();
  const status = statusConfig[subject.status] ?? statusConfig.inactive;
  const cardOnClick = onClick ?? (() => navigate(`/subjects/${subject.id}`));

  return (
    <div
      role="listitem"
      onClick={() => {
        haptics?.impact("light");
        cardOnClick();
      }}
      className="rounded-2xl p-3 flex items-center gap-3 cursor-pointer active:opacity-80 transition-opacity"
      style={{
        backgroundColor: "var(--tg-section-bg-color)",
        boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
      }}
      aria-label={`${subject.display_name}, ${status.label}, ${formatCompact(
        subject.followers,
      )} followers`}
    >
      <div
        className="rounded-full flex items-center justify-center text-white font-semibold text-sm shrink-0"
        style={{
          width: 40,
          height: 40,
          backgroundColor: platformColor,
        }}
      >
        {platformInitial}
      </div>

      <div className="flex-1 min-w-0">
        <h3
          className="font-medium text-sm truncate"
          style={{ color: "var(--tg-text-color)" }}
        >
          {subject.display_name}
        </h3>
        <p
          className="text-xs"
          style={{ color: "var(--tg-hint-color)" }}
        >
          {formatCompact(subject.followers)} followers
          {/* {subject.extended_data?.view_count !== undefined && subject.extended_data?.view_count !== null
            ? ` · ${formatCompact(Number(subject.extended_data.view_count))} views`
            : ""} */}
          {" · "}
          {formatRelative(subject.last_synced_at)}
        </p>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <span
          className="text-xs"
          style={{ color: "var(--tg-hint-color)" }}
        >
          {subject.activity_frequency.toFixed(1)}/d
        </span>
        <Badge variant={status.variant}>{status.label}</Badge>
      </div>
    </div>
  );
}