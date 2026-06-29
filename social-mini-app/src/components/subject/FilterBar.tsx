import { useTranslation } from "../../i18n";
import type { useTelegram } from "../../telegram/useTelegram";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";

export function FilterBar({
  platform,
  status,
  q,
  onFilterChange,
  haptics,
}: {
  platform: string | null;
  status: string | null;
  q: string | null;
  onFilterChange: (key: string, value: string | null) => void;
  haptics?: ReturnType<typeof useTelegram>["haptics"];
}) {
  const { t } = useTranslation();

  const platformOptions = [
    { value: "", label: t("filter.all") },
    { value: "facebook", label: t("dashboard.facebook") },
    { value: "youtube", label: t("dashboard.youtube") },
  ];

  const statusOptions = [
    { value: "", label: t("filter.all") },
    { value: "active", label: t("subject.active") },
    { value: "inactive", label: t("subject.inactive") },
    { value: "suspended", label: t("subject.suspended") },
  ];

  return (
    <div className="flex flex-col gap-2" role="search">
      <div className="flex gap-2">
        <div className="flex-1">
          <Select
            options={platformOptions}
            value={platform ?? ""}
            onChange={(e) => {
              haptics?.selection();
              onFilterChange("platform", e.target.value || null);
            }}
            aria-label={t("filter.platform")}
            style={{ minWidth: 0 }}
          />
        </div>

        <div className="flex-1">
          <Select
            options={statusOptions}
            value={status ?? ""}
            onChange={(e) => {
              haptics?.selection();
              onFilterChange("status", e.target.value || null);
            }}
            aria-label={t("filter.status")}
            style={{ minWidth: 0 }}
          />
        </div>
      </div>

      <Input
        type="search"
        value={q ?? ""}
        placeholder={t("filter.searchPlaceholder")}
        aria-label={t("filter.search")}
        onChange={(e) => onFilterChange("q", e.target.value || null)}
      />
    </div>
  );
}