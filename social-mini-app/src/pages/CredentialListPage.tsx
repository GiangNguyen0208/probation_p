import { useNavigate, useSearchParams } from "react-router-dom";
import { useCredentials } from "../api/admin-hooks";
import { CredentialCard } from "../components/credentials/CredentialCard";
import StateViews from "../components/state/StateViews";
import { PageHeader } from "../components/ui/PageHeader";
import { Button } from "../components/ui/Button";
import { useTranslation } from "../i18n";
import { useTelegram } from "../telegram/useTelegram";

export default function CredentialListPage() {
  const navigate = useNavigate();
  const { haptics } = useTelegram();
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();

  const created = searchParams.get("created");

  const { data, isLoading, isError, error, refetch } = useCredentials();

  return (
    <div className="flex flex-col gap-3">
      <PageHeader title={t("credentials.title")} />

      {created && (
        <div
          className="rounded-xl px-3 py-2 text-sm text-center"
          style={{
            backgroundColor: "rgba(52,199,89,0.15)",
            color: "#34c759",
          }}
          role="status"
        >
          {t("credentials.createdSuccess")}
        </div>
      )}

      {isLoading && <StateViews.Loading count={3} />}
      {isError && (
        <StateViews.Error
          message={error?.message ?? t("common.error")}
          retry={() => refetch()}
          retryLabel={t("common.retry")}
        />
      )}
      {!isLoading && !isError && (!data || data.length === 0) && (
        <StateViews.Empty
          message={t("credentials.empty")}
          action={() => navigate("/credentials/new")}
          actionLabel={t("credentials.add")}
        />
      )}

      {data && data.length > 0 && (
        <div className="flex flex-col gap-2" role="list" aria-label="Credentials">
          {data.map((cred) => (
            <div role="listitem" key={cred.id}>
              <CredentialCard
                credential={cred}
                onClick={() => {
                  haptics.impact("light");
                  navigate(`/credentials/${cred.id}`);
                }}
              />
            </div>
          ))}
        </div>
      )}

      <Button
        fullWidth
        size="lg"
        onClick={() => {
          haptics.impact("medium");
          navigate("/credentials/new");
        }}
      >
        {t("credentials.add")}
      </Button>
    </div>
  );
}
