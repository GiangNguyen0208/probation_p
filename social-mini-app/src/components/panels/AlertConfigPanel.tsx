import { useState } from "react";
import {
  useAlerts,
  useCreateAlert,
  useDeleteAlert,
  useUpdateAlert,
} from "../../api/hooks";
import { useTranslation } from "../../i18n";
import type { useTelegram } from "../../telegram/useTelegram";
import type { components } from "../../api/types";
import StateViews from "../state/StateViews";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";
import { Section } from "../ui/Section";

type AlertRule = components["schemas"]["AlertRule"];
type AlertRuleType = components["schemas"]["AlertRuleType"];

export function AlertConfigPanel({
  subjectId,
  haptics,
}: {
  subjectId: string;
  haptics?: ReturnType<typeof useTelegram>["haptics"];
}) {
  const { data: alerts, isLoading } = useAlerts(subjectId);
  const createAlert = useCreateAlert(subjectId);
  const updateAlert = useUpdateAlert(subjectId);
  const deleteAlert = useDeleteAlert(subjectId);

  const { t } = useTranslation();

  const RULE_TYPES: { value: AlertRuleType; label: string }[] = [
    { value: "follower_spike", label: t("alert.followerGrowthLabel") },
    { value: "follower_drop", label: t("alert.followerDrop") },
    { value: "activity_spike", label: t("alert.activityDrop") },
    { value: "activity_silence", label: t("alert.activityDrop") },
    { value: "status_change", label: "Status Change" },
  ];

  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [ruleType, setRuleType] = useState<AlertRuleType>("follower_spike");
  const [threshold, setThreshold] = useState("");
  const [cooldown, setCooldown] = useState("3600");
  const [channel, setChannel] = useState("");

  const resetForm = () => {
    setRuleType("follower_spike");
    setThreshold("");
    setCooldown("3600");
    setChannel("");
    setShowForm(false);
    setEditingId(null);
  };

  const handleSubmit = async () => {
    if (!threshold || isNaN(Number(threshold)) || Number(threshold) < 0) {
      haptics?.notification("error");
      return;
    }
    const body = {
      rule_type: ruleType,
      threshold: Number(threshold),
      cooldown_seconds: Math.max(0, Number(cooldown) || 3600),
      channel_id: channel || "@default",
    };

    try {
      if (editingId) {
        await updateAlert.mutateAsync({ ruleId: editingId, body });
      } else {
        await createAlert.mutateAsync(body);
      }
      haptics?.notification("success");
      resetForm();
    } catch {
      haptics?.notification("error");
    }
  };

  const handleEdit = (rule: AlertRule) => {
    setEditingId(rule.id!);
    setRuleType(rule.rule_type);
    setThreshold(String(rule.threshold));
    setCooldown(String(rule.cooldown_seconds));
    setChannel(rule.channel_id);
    setShowForm(true);
  };

  if (isLoading) return <StateViews.Loading count={2} />;

  return (
    <Section title={t("alert.configTitle")}>
      <div className="flex items-center justify-between mb-2">
        <span
          className="text-sm font-medium"
          style={{ color: "var(--tg-text-color)" }}
        >
          {showForm
            ? editingId
              ? t("alert.editRule")
              : t("alert.newRule")
            : `${alerts?.length ?? 0} ${t("alert.configTitle").toLowerCase()}`}
        </span>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            haptics?.impact("light");
            if (showForm) {
              resetForm();
            } else {
              setShowForm(true);
            }
          }}
          aria-expanded={showForm}
        >
          {showForm ? t("credentials.cancel") : t("alert.addRule")}
        </Button>
      </div>

      {showForm && (
        <Card className="!p-3 flex flex-col gap-2">
          <Select
            label={t("alert.ruleType")}
            options={RULE_TYPES}
            value={ruleType}
            onChange={(e) => {
              haptics?.selection();
              setRuleType(e.target.value as AlertRuleType);
            }}
          />

          <Input
            type="number"
            min="0"
            label={t("alert.threshold")}
            placeholder="e.g. 1000"
            value={threshold}
            onChange={(e) => setThreshold(e.target.value)}
          />

          <Input
            type="number"
            min="0"
            label={t("alert.cooldown")}
            value={cooldown}
            onChange={(e) => setCooldown(e.target.value)}
          />

          <Input
            type="text"
            label={t("alert.channel")}
            placeholder="e.g. @ops"
            value={channel}
            onChange={(e) => setChannel(e.target.value)}
          />

          <Button
            fullWidth
            loading={createAlert.isPending || updateAlert.isPending}
            onClick={handleSubmit}
          >
            {editingId ? t("credentials.save") : t("alert.addRule")}
          </Button>

          {(createAlert.isError || updateAlert.isError) && (
            <p
              className="text-xs"
              style={{ color: "var(--tg-destructive-text-color)" }}
              role="alert"
            >
              {(createAlert.error ?? updateAlert.error)?.message ??
                t("common.error")}
            </p>
          )}
        </Card>
      )}

      {alerts && alerts.length > 0 && !showForm && (
        <div className="flex flex-col gap-2">
          {alerts.map((rule) => (
            <Card key={rule.id} className="!p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p
                    className="text-sm font-medium"
                    style={{ color: "var(--tg-text-color)" }}
                  >
                    {RULE_TYPES.find((r) => r.value === rule.rule_type)?.label ??
                      rule.rule_type}
                  </p>
                  <p
                    className="text-xs mt-0.5"
                    style={{ color: "var(--tg-hint-color)" }}
                  >
                    {t("alert.threshold")}: {rule.threshold} · {t("alert.cooldown")}:{" "}
                    {rule.cooldown_seconds}s · {rule.channel_id}
                  </p>
                </div>
                <div className="flex gap-1 shrink-0">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      haptics?.impact("light");
                      handleEdit(rule);
                    }}
                    aria-label={`${t("alert.editRule")} ${rule.rule_type}`}
                  >
                    {t("credentials.edit")}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      haptics?.notification("warning");
                      deleteAlert.mutate(rule.id!);
                    }}
                    aria-label={`${t("alert.deleteRule")} ${rule.rule_type}`}
                  >
                    {t("alert.deleteRule")}
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </Section>
  );
}