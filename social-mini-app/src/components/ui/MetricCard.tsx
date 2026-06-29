import { Card } from "./Card";

export interface MetricCardProps {
  label: string;
  value: string;
}

export function MetricCard({ label, value }: MetricCardProps) {
  return (
    <Card className="!p-3">
      <p className="text-xs" style={{ color: "var(--tg-hint-color)" }}>
        {label}
      </p>
      <p
        className="text-lg font-semibold mt-0.5"
        style={{ color: "var(--tg-text-color)" }}
      >
        {value}
      </p>
    </Card>
  );
}
