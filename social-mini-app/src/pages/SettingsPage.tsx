import { useTelegram } from "../telegram/useTelegram";
import {
  useTheme,
  type ChartStyle,
  type ThemeMode,
} from "../theme/ThemeProvider";
import { useTranslation, type Language, type TranslationKey } from "../i18n";
import { Card, CardHeader } from "../components/ui/Card";
import { Toggle } from "../components/ui/Toggle";
import { Select } from "../components/ui/Select";
import { Section } from "../components/ui/Section";

const themeOptions: { value: string; label: TranslationKey }[] = [
  { value: "system", label: "settings.system" },
  { value: "light", label: "settings.light" },
  { value: "dark", label: "settings.dark" },
];

const chartStyleOptions: { value: string; label: TranslationKey }[] = [
  { value: "line", label: "settings.lineChart" },
  { value: "bar", label: "settings.barChart" },
  { value: "area", label: "settings.areaChart" },
];

const languageOptions: { value: string; label: TranslationKey }[] = [
  { value: "en", label: "settings.english" },
  { value: "vi", label: "settings.vietnamese" },
];

export default function SettingsPage() {
  const { haptics } = useTelegram();
  const { t, language, setLanguage } = useTranslation();
  const {
    mode,
    isDark,
    visualization,
    setMode,
    setVisualization,
  } = useTheme();

  return (
    <div className="flex flex-col gap-4">
      <h1
        className="text-xl font-bold"
        style={{ color: "var(--tg-text-color)" }}
      >
        {t("settings.title")}
      </h1>

      <Section title={t("settings.appearance")}>
        <Card>
          <CardHeader title={t("settings.theme")} />
          <Select
            id="theme-mode"
            label={t("settings.colorScheme")}
            options={themeOptions.map((o) => ({ value: o.value, label: t(o.label) }))}
            value={mode}
            onChange={(e) => {
              haptics.selection();
              setMode(e.target.value as ThemeMode);
            }}
          />
          <p
            className="text-xs mt-2"
            style={{ color: "var(--tg-hint-color)" }}
          >
            {t("settings.currentMode", { mode: isDark ? t("settings.dark") : t("settings.light") })}
          </p>
        </Card>

        <Card className="mt-3">
          <CardHeader title={t("settings.language")} />
          <Select
            id="app-language"
            label={t("settings.selectLanguage")}
            options={languageOptions.map((o) => ({ value: o.value, label: t(o.label) }))}
            value={language}
            onChange={(e) => {
              haptics.selection();
              setLanguage(e.target.value as Language);
            }}
          />
        </Card>
      </Section>

      <Section title={t("settings.charts")}>
        <Card>
          <CardHeader title={t("settings.chartStyle")} />
          <Select
            id="chart-style"
            label={t("settings.defaultChart")}
            options={chartStyleOptions.map((o) => ({ value: o.value, label: t(o.label) }))}
            value={visualization.chartStyle}
            onChange={(e) => {
              haptics.selection();
              setVisualization({
                chartStyle: e.target.value as ChartStyle,
              });
            }}
          />
          <div className="mt-3">
            <Toggle
              label={t("settings.showGrid")}
              description={t("settings.showGridDesc")}
              checked={visualization.showGrid}
              onChange={(checked) => {
                haptics.impact("light");
                setVisualization({ showGrid: checked });
              }}
            />
          </div>
          <div className="mt-2">
            <Toggle
              label={t("settings.compactView")}
              description={t("settings.compactViewDesc")}
              checked={visualization.compactView}
              onChange={(checked) => {
                haptics.impact("light");
                setVisualization({ compactView: checked });
              }}
            />
          </div>
        </Card>
      </Section>

      <Section title={t("settings.about")}>
        <Card>
          <div className="flex flex-col gap-2 text-sm">
            <div
              className="flex justify-between items-center"
              style={{ color: "var(--tg-text-color)" }}
            >
              <span>{t("settings.version")}</span>
              <span style={{ color: "var(--tg-hint-color)" }}>0.1.0</span>
            </div>
            <div
              className="flex justify-between items-center"
              style={{ color: "var(--tg-text-color)" }}
            >
              <span>{t("settings.platform")}</span>
              <span style={{ color: "var(--tg-hint-color)" }}>
                {t("settings.telegramMiniApp")}
              </span>
            </div>
          </div>
        </Card>
      </Section>
    </div>
  );
}