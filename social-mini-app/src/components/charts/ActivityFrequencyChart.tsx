import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useTranslation } from "../../i18n";
import { Card } from "../ui/Card";
import { useTheme } from "../../theme/ThemeProvider";
import { formatDate, resolveColor } from "../../utils/format";
import type { components } from "../../api/types";

type ActivitySnapshot = components["schemas"]["ActivitySnapshot"];

export function ActivityFrequencyChart({
  data,
  accentColor,
}: {
  data: ActivitySnapshot[];
  accentColor: string;
}) {
  const { t } = useTranslation();
  const { visualization } = useTheme();
  const reversed = [...data].reverse();
  const chartData = reversed.map((d) => ({
    date: formatDate(d.captured_at),
    frequency: d.frequency,
  }));

  const hintColor = resolveColor("--tg-hint-color", "#999999");
  const bgColor = resolveColor("--tg-bg-color", "#ffffff");
  const textColor = resolveColor("--tg-text-color", "#000000");
  const separatorColor = resolveColor(
    "--tg-section-separator-color",
    "#e8e8e8",
  );

  return (
    <Card ariaLabel={t("activity.frequency")}>
      <h3
        className="text-sm font-medium mb-3"
        style={{ color: "var(--tg-text-color)" }}
      >
        {t("activity.frequency")}
      </h3>
      <ResponsiveContainer width="100%" height={visualization.compactView ? 140 : 180}>
        {visualization.chartStyle === "line" ? (
          <LineChart data={chartData}>
            {visualization.showGrid && (
              <CartesianGrid
                strokeDasharray="3 3"
                stroke={separatorColor}
                opacity={0.3}
              />
            )}
            <XAxis
              dataKey="date"
              fontSize={10}
              tick={{ fill: hintColor }}
              axisLine={{ stroke: separatorColor }}
              tickLine={false}
            />
            <YAxis
              fontSize={10}
              tick={{ fill: hintColor }}
              axisLine={false}
              tickLine={false}
              width={32}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: bgColor,
                border: "none",
                borderRadius: 8,
                color: textColor,
                fontSize: 12,
              }}
            />
            <Line
              type="monotone"
              dataKey="frequency"
              stroke={accentColor}
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        ) : visualization.chartStyle === "area" ? (
          <AreaChart data={chartData}>
            {visualization.showGrid && (
              <CartesianGrid
                strokeDasharray="3 3"
                stroke={separatorColor}
                opacity={0.3}
              />
            )}
            <XAxis
              dataKey="date"
              fontSize={10}
              tick={{ fill: hintColor }}
              axisLine={{ stroke: separatorColor }}
              tickLine={false}
            />
            <YAxis
              fontSize={10}
              tick={{ fill: hintColor }}
              axisLine={false}
              tickLine={false}
              width={32}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: bgColor,
                border: "none",
                borderRadius: 8,
                color: textColor,
                fontSize: 12,
              }}
            />
            <Area
              type="monotone"
              dataKey="frequency"
              stroke={accentColor}
              strokeWidth={2}
              fill={accentColor}
              fillOpacity={0.15}
            />
          </AreaChart>
        ) : (
          <BarChart data={chartData}>
            {visualization.showGrid && (
              <CartesianGrid
                strokeDasharray="3 3"
                stroke={separatorColor}
                opacity={0.3}
              />
            )}
            <XAxis
              dataKey="date"
              fontSize={10}
              tick={{ fill: hintColor }}
              axisLine={{ stroke: separatorColor }}
              tickLine={false}
            />
            <YAxis
              fontSize={10}
              tick={{ fill: hintColor }}
              axisLine={false}
              tickLine={false}
              width={32}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: bgColor,
                border: "none",
                borderRadius: 8,
                color: textColor,
                fontSize: 12,
              }}
            />
            <Bar
              dataKey="frequency"
              fill={accentColor}
              opacity={0.7}
              radius={[3, 3, 0, 0]}
            />
          </BarChart>
        )}
      </ResponsiveContainer>
    </Card>
  );
}
