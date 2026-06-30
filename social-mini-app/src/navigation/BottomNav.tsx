import { NavLink } from "react-router-dom";
import { useTelegram } from "../telegram/useTelegram";
import { useTranslation } from "../i18n";

type Haptics = ReturnType<typeof useTelegram>["haptics"];

const navItems = [
  {
    path: "/",
    translationKey: "nav.subjects" as const,
    end: true,
    icon: (
      <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M20 7L12 3 4 7l8 4 8-4z" />
        <path d="M4 7v10l8 4 8-4V7" />
        <path d="M12 11v10" />
      </svg>
    ),
  },
  {
    path: "/dashboard",
    translationKey: "nav.dashboard" as const,
    icon: (
      <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <rect x="3" y="3" width="7" height="9" rx="1" />
        <rect x="14" y="3" width="7" height="5" rx="1" />
        <rect x="14" y="12" width="7" height="9" rx="1" />
        <rect x="3" y="16" width="7" height="5" rx="1" />
      </svg>
    ),
  },
  {
    path: "/credentials",
    translationKey: "nav.credentials" as const,
    icon: (
      <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
      </svg>
    ),
  },
  {
    path: "/settings",
    translationKey: "nav.settings" as const,
    icon: (
      <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
      </svg>
    ),
  },
];

export function BottomNav({ haptics, isAdmin }: { haptics: Haptics; isAdmin: boolean }) {
  const { t } = useTranslation();

  const visibleItems = navItems.filter((item) => {
    if (item.path === "/credentials") return isAdmin;
    return true;
  });

  return (
    <nav
      className="flex items-stretch justify-around"
      aria-label="Main navigation"
      style={{
        backgroundColor: "var(--tg-section-bg-color)",
        borderTop: "1px solid var(--tg-section-separator-color)",
        paddingBottom: "var(--tg-safe-area-inset-bottom)",
      }}
    >
      {visibleItems.map((item) => {
        const label = t(item.translationKey);
        return (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.end}
            className="flex flex-col items-center justify-center gap-0.5 py-2 flex-1 no-underline"
            style={({ isActive }) => ({
              color: isActive
                ? "var(--tg-link-color)"
                : "var(--tg-hint-color)",
            })}
            onClick={() => haptics.selection()}
            aria-label={label}
          >
            {item.icon}
            <span className="text-xs font-medium">{label}</span>
          </NavLink>
        );
      })}
    </nav>
  );
}