import { usePlatforms } from "../../api/admin-hooks";
import { Select, type SelectOption } from "../ui/Select";

interface PlatformPickerProps {
  value: string;
  onChange: (slug: string) => void;
}

export function PlatformPicker({ value, onChange }: PlatformPickerProps) {
  const { data: platforms, isLoading, isError } = usePlatforms(true);

  const options: SelectOption[] = [
    { value: "", label: "Select a platform…" },
    ...(platforms?.map((p) => ({ value: p.slug, label: p.name })) ?? []),
  ];

  if (isLoading) {
    return (
      <div
        className="rounded-xl px-3 py-2.5 text-sm"
        style={{
          backgroundColor: "var(--tg-section-bg-color)",
          color: "var(--tg-hint-color)",
          border: "1px solid var(--tg-section-separator-color, transparent)",
        }}
      >
        Loading platforms…
      </div>
    );
  }

  if (isError || !platforms?.length) {
    return (
      <p className="text-xs" style={{ color: "var(--tg-destructive-text-color)" }}>
        No platforms available
      </p>
    );
  }

  return (
    <Select
      id="platform-slug"
      label="Platform"
      options={options}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}
