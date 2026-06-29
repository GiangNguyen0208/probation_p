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
import { Card } from "../ui/Card";
import { useTheme } from "../../theme/ThemeProvider";

function resolveColor(varName: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const value = getComputedStyle(document.documentElement)
    .getPropertyValue(varName)
    .trim();
  return value || fallback;
}

function formatDate(str: string): string {
  return new Date(str).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

export interface TimelineChartProps {
  title: string;
  dataKey: string;
  data: { captured_at: string }[];
  accentColor: string;
  ariaLabel?: string;
}

export function TimelineChart({ title, dataKey, data, accentColor, ariaLabel }: TimelineChartProps) {
  const { visualization } = useTheme();
  const reversed = [...data].reverse();
  const chartData = reversed.map((d) => ({
    date: formatDate(d.captured_at),
    value: (d as unknown as Record<string, number>)[dataKey],
  }));

  const hintColor = resolveColor("--tg-hint-color", "#999999");
  const bgColor = resolveColor("--tg-bg-color", "#ffffff");
  const textColor = resolveColor("--tg-text-color", "#000000");
  const separatorColor = resolveColor(
    "--tg-section-separator-color",
    "#e8e8e8",
  );

  return (
    <Card ariaLabel={ariaLabel}>
      <h3
        className="text-sm font-medium mb-3"
        style={{ color: "var(--tg-text-color)" }}
      >
        {title}
      </h3>
      <ResponsiveContainer width="100%" height={visualization.compactView ? 140 : 180}>
        {visualization.chartStyle === "bar" ? (
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
              width={40}
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
              dataKey="value"
              fill={accentColor}
              opacity={0.7}
              radius={[3, 3, 0, 0]}
            />
          </BarChart>
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
              width={40}
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
              dataKey="value"
              stroke={accentColor}
              strokeWidth={2}
              fill={accentColor}
              fillOpacity={0.15}
            />
          </AreaChart>
        ) : (
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
              width={40}
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
              dataKey="value"
              stroke={accentColor}
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        )}
      </ResponsiveContainer>
    </Card>
  );
}
