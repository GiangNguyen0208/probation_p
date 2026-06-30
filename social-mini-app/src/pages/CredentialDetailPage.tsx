import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useCredential, useRevokeCredential, useUpdateCredential, usePlatforms } from "../api/credential-hooks";
import type { ConfigSchemaField } from "../api/admin-types";
import { DynamicCredentialForm } from "../components/credentials/DynamicCredentialForm";
import StateViews from "../components/state/StateViews";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { Section } from "../components/ui/Section";
import { useTranslation } from "../i18n";
import { useTelegram } from "../telegram/useTelegram";
import { formatRelative } from "../utils/format";

export default function CredentialDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { haptics, back } = useTelegram();
  const { t } = useTranslation();
  const revokeMutation = useRevokeCredential();
  const updateMutation = useUpdateCredential();

  const { data: credential, isLoading, isError, error, refetch } = useCredential(id!);
  const { data: platforms } = usePlatforms(true);

  const [isEditing, setIsEditing] = useState(false);
  const [editLabel, setEditLabel] = useState("");
  const [editValues, setEditValues] = useState<Record<string, string>>({});

  useEffect(() => {
    back.show();
    return () => back.hide();
  }, [back]);

  useEffect(() => {
    const cb = () => window.history.back();
    back.onClick(cb);
    return () => back.offClick(cb);
  }, [back]);

  useEffect(() => {
    if (credential) {
      setEditLabel(credential.label);
    }
  }, [credential]);

  const platform = platforms?.find((p) => p.id === credential?.platform_id);
  const configSchema = (platform?.config_schema ?? {}) as Record<string, ConfigSchemaField>;

  const handleRevoke = () => {
    haptics.impact("medium");
    revokeMutation.mutate(id!, {
      onSuccess: () => {
        navigate("/credentials");
      },
    });
  };

  const handleSave = () => {
    if (!editLabel.trim()) return;
    haptics.impact("medium");
    updateMutation.mutate(
      {
        credentialId: id!,
        body: {
          ...(editLabel !== credential?.label ? { label: editLabel.trim() } : {}),
          ...(Object.keys(editValues).length > 0 ? { credentials: editValues } : {}),
        },
      },
      {
        onSuccess: () => {
          setIsEditing(false);
          setEditValues({});
        },
      },
    );
  };

  if (isLoading) return <StateViews.Loading count={2} />;
  if (isError) {
    return (
      <StateViews.Error
        message={error?.message ?? t("common.error")}
        retry={() => refetch()}
        retryLabel={t("common.retry")}
      />
    );
  }
  if (!credential) return <StateViews.Empty />;

  const isRevoked = credential.status === "revoked" || !credential.is_active;

  const statusVariant = isRevoked ? "danger" : credential.status === "active" ? "success" : "warning";

  return (
    <div className="flex flex-col gap-3">
      <Section>
        <Card className="!p-4">
          <div className="flex items-center justify-between mb-2">
            <h2
              className="font-semibold text-base"
              style={{ color: "var(--tg-text-color)" }}
            >
              {credential.label}
            </h2>
            <Badge variant={statusVariant}>
              {isRevoked ? t("credentials.revokedStatus") : t("credentials.activeStatus")}
            </Badge>
          </div>
          <p className="text-xs" style={{ color: "var(--tg-hint-color)" }}>
            {t("credentials.platform", { slug: credential.platform_slug })}
          </p>
          <p className="text-xs" style={{ color: "var(--tg-hint-color)" }}>
            {t("credentials.created", { time: formatRelative(credential.created_at) })}
          </p>
          {credential.last_verified_at && (
            <p className="text-xs" style={{ color: "var(--tg-hint-color)" }}>
              {t("credentials.lastVerified", { time: formatRelative(credential.last_verified_at) })}
            </p>
          )}
        </Card>
      </Section>

      <Section title={t("credentials.configuredFields")}>
        <Card className="!p-4">
          {credential.configured_fields.length === 0 ? (
            <p className="text-sm" style={{ color: "var(--tg-hint-color)" }}>
              {t("credentials.noFields")}
            </p>
          ) : (
            <div className="flex flex-col gap-2">
              {credential.configured_fields.map((field) => (
                <div
                  key={field}
                  className="flex items-center justify-between"
                >
                  <span
                    className="text-sm"
                    style={{ color: "var(--tg-text-color)" }}
                  >
                    {configSchema[field]?.label ?? field}
                  </span>
                  <span
                    className="text-xs"
                    style={{ color: "var(--tg-hint-color)" }}
                  >
                    • • • • • • • •
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </Section>

      {isEditing && (
        <Section title={t("credentials.edit")}>
          <Card className="!p-4 flex flex-col gap-3">
            <Input
              label={t("credentials.label")}
              value={editLabel}
              onChange={(e) => setEditLabel(e.target.value)}
            />

            <DynamicCredentialForm
              configSchema={configSchema}
              values={editValues}
              onChange={(key, value) => setEditValues((prev) => ({ ...prev, [key]: value }))}
            />

            <div className="flex gap-2">
              <Button
                variant="secondary"
                className="flex-1"
                onClick={() => {
                  setIsEditing(false);
                  setEditValues({});
                  setEditLabel(credential.label);
                }}
              >
                {t("credentials.cancel")}
              </Button>
              <Button
                className="flex-1"
                loading={updateMutation.isPending}
                disabled={updateMutation.isPending}
                onClick={handleSave}
              >
                {t("credentials.save")}
              </Button>
            </div>

            {updateMutation.isError && (
              <p
                className="text-xs"
                style={{ color: "var(--tg-destructive-text-color)" }}
                role="alert"
              >
                {updateMutation.error?.message ?? t("common.error")}
              </p>
            )}
          </Card>
        </Section>
      )}

      <div className="flex flex-col gap-2 mt-2">
        {!isRevoked && (
          <Button
            variant="secondary"
            fullWidth
            onClick={() => setIsEditing(true)}
          >
            {t("credentials.edit")}
          </Button>
        )}

        {!isRevoked && (
          <Button
            variant="secondary"
            fullWidth
            loading={revokeMutation.isPending}
            onClick={handleRevoke}
            style={{
              color: "var(--tg-destructive-text-color)",
              border: "1px solid var(--tg-destructive-text-color)",
            }}
          >
            {revokeMutation.isPending ? t("credentials.revoking") : t("credentials.revoke")}
          </Button>
        )}
      </div>
    </div>
  );
}
