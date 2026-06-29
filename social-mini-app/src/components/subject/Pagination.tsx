import { useTranslation } from "../../i18n";
import { Button } from "../ui/Button";
import type { useTelegram } from "../../telegram/useTelegram";

export function Pagination({
  page,
  hasMore,
  onPageChange,
  haptics,
}: {
  page: number;
  hasMore: boolean;
  onPageChange: (page: number) => void;
  haptics?: ReturnType<typeof useTelegram>["haptics"];
}) {
  const { t } = useTranslation();

  return (
    <nav
      className="flex items-center justify-center gap-4 py-3"
      aria-label={t("common.previous")}
    >
      <Button
        variant="secondary"
        size="sm"
        disabled={page <= 1}
        onClick={() => {
          haptics?.impact("light");
          onPageChange(page - 1);
        }}
        aria-label={t("common.previous")}
      >
        {t("common.previous")}
      </Button>

      <span
        className="text-sm tabular-nums"
        style={{ color: "var(--tg-hint-color)" }}
        aria-current="page"
      >
        {t("subjects.title")} {page}
      </span>

      <Button
        variant="secondary"
        size="sm"
        disabled={!hasMore}
        onClick={() => {
          haptics?.impact("light");
          onPageChange(page + 1);
        }}
        aria-label={t("common.next")}
      >
        {t("common.next")}
      </Button>
    </nav>
  );
}