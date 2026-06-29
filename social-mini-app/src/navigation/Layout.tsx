import { Outlet, useLocation } from "react-router-dom";
import { useTelegram } from "../telegram/useTelegram";
import { BottomNav } from "./BottomNav";
import { Spinner } from "../components/ui/Spinner";

export function Layout() {
  const { ready, viewportHeight, haptics } = useTelegram();
  const location = useLocation();
  const isDetail = location.pathname.includes("/subjects/") || (location.pathname.includes("/credentials/") && !location.pathname.endsWith("/credentials") && !location.pathname.endsWith("/credentials/"));

  if (!ready) {
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
      className="flex flex-col mx-auto"
      style={{
        height: viewportHeight,
        backgroundColor: "var(--tg-bg-color)",
        paddingLeft: "var(--tg-safe-area-inset-left)",
        paddingRight: "var(--tg-safe-area-inset-right)",
      }}
    >
      <main
        className="flex-1 overflow-y-auto"
        style={{
          paddingTop: "var(--tg-content-safe-area-inset-top)",
          paddingBottom: "var(--tg-content-safe-area-inset-bottom)",
        }}
      >
        <div
          className="px-4 pt-2 pb-4"
          style={{ maxWidth: "480px", marginLeft: "auto", marginRight: "auto" }}
        >
          <Outlet />
        </div>
      </main>

      {!isDetail && <BottomNav haptics={haptics} />}
    </div>
  );
}