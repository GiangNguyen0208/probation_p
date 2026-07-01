import { NavLink } from "react-router-dom";
import { useTelegram } from "../telegram/useTelegram";
import { useTranslation } from "../i18n";

type Haptics = ReturnType<typeof useTelegram>["haptics"];

interface NavItem {
  path: string;
  translationKey: string;
  end?: boolean;
  icon: string;
}

const navItems: NavItem[] = [
  { path: "/", translationKey: "nav.subjects", end: true, icon: "layers" },
  { path: "/dashboard", translationKey: "nav.dashboard", icon: "grid_view" },
  { path: "/credentials", translationKey: "nav.credentials", icon: "shield" },
  { path: "/settings", translationKey: "nav.settings", icon: "settings" },
];

export function BottomNav({
  haptics,
  isAdmin,
}: {
  haptics: Haptics;
  isAdmin: boolean;
}) {
  const { t } = useTranslation();

  const visibleItems = navItems.filter((item) => {
    if (item.path === "/credentials") return isAdmin;
    return true;
  });

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 rounded-t-xl"
      style={{
        backgroundColor: "color-mix(in srgb, var(--si-canvas) 90%, transparent)",
        borderTop: "1px solid var(--si-border)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
      }}
      aria-label="Main navigation"
    >
      <div
        className="flex justify-around items-center w-full max-w-[600px] mx-auto h-16 px-3"
        style={{ paddingBottom: "var(--tg-safe-area-inset-bottom, 0px)" }}
      >
        {visibleItems.map((item) => {
          const label = t(item.translationKey as never);
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.end}
              className="flex flex-col items-center justify-center gap-0.5 px-3 py-1 rounded-xl transition-all duration-200 active:scale-90"
              style={({ isActive }: { isActive: boolean }) => ({
                backgroundColor: isActive ? "var(--si-accent-tint)" : "transparent",
              })}
              onClick={() => haptics.selection()}
              aria-label={label}
            >
              {({ isActive }: { isActive: boolean }) => (
                <>
                  <span
                    className="material-symbols-outlined"
                    style={{
                      color: isActive ? "var(--si-accent)" : "var(--si-text-tertiary)",
                      fontVariationSettings: isActive ? "'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24" : "'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 24",
                    }}
                  >
                    {item.icon}
                  </span>
                  <span
                    className="text-xs mt-0.5 font-medium"
                    style={{
                      color: isActive ? "var(--si-accent)" : "var(--si-text-tertiary)",
                    }}
                  >
                    {label}
                  </span>
                </>
              )}
            </NavLink>
          );
        })}
      </div>
    </nav>
  );
}
