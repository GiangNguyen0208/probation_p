import { Input } from "../ui/Input";
import type { ConfigSchemaField } from "../../api/admin-types";

interface DynamicCredentialFormProps {
  configSchema: Record<string, ConfigSchemaField>;
  values: Record<string, string>;
  onChange: (key: string, value: string) => void;
}

export function DynamicCredentialForm({ configSchema, values, onChange }: DynamicCredentialFormProps) {
  const fields = Object.entries(configSchema);

  if (fields.length === 0) {
    return (
      <p className="text-sm" style={{ color: "var(--tg-hint-color)" }}>
        No configuration fields required for this platform.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {fields.map(([key, field]) => (
        <Input
          key={key}
          label={`${field.label}${field.required ? " *" : ""}`}
          type={field.sensitive ? "password" : "text"}
          placeholder={field.label}
          value={values[key] ?? ""}
          onChange={(e) => onChange(key, e.target.value)}
          autoComplete="off"
        />
      ))}
    </div>
  );
}
