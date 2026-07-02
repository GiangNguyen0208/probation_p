import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCreateCredential, usePlatforms } from "../../api/credential-hooks";
import type { ConfigSchemaField } from "../../api/admin-types";
import { PlatformPicker } from "../../components/credentials/PlatformPicker";
import { DynamicCredentialForm } from "../../components/credentials/DynamicCredentialForm";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { PageHeader } from "../../components/ui/PageHeader";
import { useTranslation } from "../../i18n";
import { useTelegram } from "../../telegram/useTelegram";

export default function CredentialFormPage() {
  const navigate = useNavigate();
  const { haptics, back } = useTelegram();
  const { t } = useTranslation();
  const createMutation = useCreateCredential();
  const { data: platforms } = usePlatforms(true);

  const [platformSlug, setPlatformSlug] = useState("");
  const [label, setLabel] = useState("");
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({});

  useEffect(() => {
    back.show();
    return () => back.hide();
  }, [back]);

  useEffect(() => {
    const cb = () => window.history.back();
    back.onClick(cb);
    return () => back.offClick(cb);
  }, [back]);

  const selectedPlatform = platforms?.find((p) => p.slug === platformSlug);
  const configSchema = (selectedPlatform?.config_schema ?? {}) as Record<string, ConfigSchemaField>;

  const resetFields = () => {
    setFieldValues({});
  };

  const handlePlatformChange = (slug: string) => {
    setPlatformSlug(slug);
    resetFields();
  };

  const handleFieldChange = (key: string, value: string) => {
    setFieldValues((prev) => ({ ...prev, [key]: value }));
  };

  const requiredFields = Object.entries(configSchema)
    .filter(([, field]) => field.required)
    .map(([key]) => key);

  const missingRequired = requiredFields.filter((key) => !fieldValues[key]?.trim());
  const canSubmit = platformSlug && label.trim() && missingRequired.length === 0;

  const handleSubmit = () => {
    if (!canSubmit) return;
    haptics.impact("medium");

    createMutation.mutate(
      {
        platform_slug: platformSlug,
        label: label.trim(),
        credentials: fieldValues,
      },
      {
        onSuccess: () => {
          navigate("/credentials?created=1");
        },
      },
    );
  };

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title={t("credentials.newTitle")} />

      <PlatformPicker value={platformSlug} onChange={handlePlatformChange} />

      {platformSlug && (
        <>
          <Input
            label={t("credentials.label")}
            placeholder={t("credentials.placeholderLabel")}
            value={label}
            onChange={(e) => setLabel(e.target.value)}
          />

          <DynamicCredentialForm
            configSchema={configSchema}
            values={fieldValues}
            onChange={handleFieldChange}
          />
        </>
      )}

      {createMutation.isError && (
        <p
          className="text-xs"
          style={{ color: "var(--tg-destructive-text-color)" }}
          role="alert"
        >
          {createMutation.error?.message ?? "Failed to create credential"}
        </p>
      )}

      {platformSlug && (
        <Button
          fullWidth
          size="lg"
          disabled={!canSubmit}
          loading={createMutation.isPending}
          onClick={handleSubmit}
        >
          {createMutation.isPending ? t("credentials.creating") : t("credentials.create")}
        </Button>
      )}
    </div>
  );
}
