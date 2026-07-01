import { Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import { useTelegram } from "../telegram/useTelegram";
import { BottomNav } from "./BottomNav";
import { TopAppBar } from "./TopAppBar";
import { TopAppBarProvider, useTopAppBar } from "./TopAppBarContext";
import { Spinner } from "../components/ui/Spinner";

function LayoutContent() {
  const { ready, viewportHeight, haptics } = useTelegram();
  const { isLoading: authLoading, isAdmin } = useAuth();
  const { config } = useTopAppBar();
  const location = useLocation();
  const isDetail =
    location.pathname.includes("/subjects/") ||
    (location.pathname.includes("/credentials/") &&
      !location.pathname.endsWith("/credentials") &&
      !location.pathname.endsWith("/credentials/"));

  const topBarHeight = config ? 56 : 0;

  if (!ready || authLoading) {
    return (
      <div
        className="flex items-center justify-center"
        style={{ height: viewportHeight }}
      >
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div
      className="flex flex-col mx-auto relative"
      style={{
        height: viewportHeight,
        paddingLeft: "var(--tg-safe-area-inset-left)",
        paddingRight: "var(--tg-safe-area-inset-right)",
      }}
    >
      <TopAppBar />

      <main
        className="flex-1 overflow-y-auto"
        id="main-scroll"
        style={{
          paddingTop: topBarHeight,
          paddingBottom: isDetail ? "var(--tg-content-safe-area-inset-bottom)" : undefined,
        }}
      >
        <div className="px-4 pb-6 mx-auto" style={{ maxWidth: "480px" }}>
          <Outlet />
        </div>
      </main>

      {!isDetail && <BottomNav haptics={haptics} isAdmin={isAdmin} />}
    </div>
  );
}

export function Layout() {
  return (
    <TopAppBarProvider>
      <LayoutContent />
    </TopAppBarProvider>
  );
}
