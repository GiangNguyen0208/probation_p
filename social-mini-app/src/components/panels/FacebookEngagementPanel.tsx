import { useTranslation } from "../../i18n";
import { Section } from "../ui/Section";
import type { components } from "../../api/types";

type Subject = components["schemas"]["Subject"];

export function FacebookEngagementPanel({ subject }: { subject: Subject }) {
  const { t } = useTranslation();
  const ext = subject.extended_data?.facebook;
  if (!ext) {
    return null;
  }

  return (
    <Section title={t("engagement.section")}>
      <div className="flex flex-col gap-2">
        <p className="text-sm" style={{ color: "var(--tg-hint-color)" }}>{t("common.noData")}</p>
      </div>
    </Section>
  );
}
