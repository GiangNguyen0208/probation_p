# social-mini-app

Telegram Mini App for the Social Intelligence Platform.

## Setup

```bash
npm install
npm run dev        # http://localhost:5173
```

## Commands

```bash
npm run lint       # ESLint (flat config)
npm run typecheck  # tsc --noEmit
npm run build      # typecheck + Vite build
```

## Environment

Copy `.env.example` to `.env.local`:

| Variable | Description |
|---|---|
| `VITE_API_BASE_URL` | Gateway URL (e.g. `https://abc123.ngrok-free.app`) |
| `VITE_INTERNAL_API_KEY` | Internal-tier API key for read/write |
| `VITE_TELEGRAM_BOT_USERNAME` | Bot username from BotFather |

## Architecture

- **Routing:** `react-router-dom` — list, detail, dashboard, settings pages
- **Data fetching:** `@tanstack/react-query` — caching, pagination, loading/error states
- **Charts:** `recharts` — SVG-based follower/activity charts (line/bar/area, configurable)
- **Types:** Generated from gateway OpenAPI via `openapi-typescript`
- **Telegram SDK:** `@telegram-apps/sdk` v2.x — theme, back button, viewport, haptics, closing confirmation
- **Theme system:** `ThemeProvider` — system/light/dark mode with localStorage persistence, syncs with Telegram theme params in real-time
- **UI primitives:** Custom Telegram-themed design system (`Button`, `Card`, `Badge`, `Input`, `Select`, `Toggle`, `Spinner`)

## Project Structure

```
src/
  components/
    ui/           # Reusable design system primitives
      Button.tsx      # Primary/secondary/ghost/destructive variants, loading state
      Card.tsx        # Surface container with CardHeader
      Badge.tsx       # Status badges (success/warning/danger/neutral) with icon
      Input.tsx       # Text input with label, hint, error, leading/trailing icons
      Select.tsx      # Styled select dropdown with label support
      Toggle.tsx      # iOS-style switch (role=switch, 44px touch target)
      Spinner.tsx     # Loading indicator
      PageHeader.tsx  # Page title + Section wrapper
      index.ts        # Barrel export
    state/        # Loading/Empty/Error states
      StateViews.tsx  # Skeleton loading, empty with action, error with retry
    subject/      # Subject-domain components
      SubjectCard.tsx  # Platform badge, status, followers, activity freq
      FilterBar.tsx    # Platform/status select + search input
      Pagination.tsx   # Prev/next page navigation
    charts/       # Data visualization (recharts)
      FollowerChart.tsx           # Configurable line/bar/area chart
      ActivityFrequencyChart.tsx   # Configurable line/bar/area chart
    panels/       # Complex composed panels
      AlertConfigPanel.tsx  # CRUD alert rules with form
  navigation/     # App shell + navigation
    Layout.tsx        # Safe-area-aware shell, viewport height, content max-width
    BottomNav.tsx     # 3-tab bottom navigation (Subjects/Dashboard/Settings)
  pages/          # Route-level pages
    SubjectListPage.tsx   # Browse + filter + paginate subjects
    SubjectDetailPage.tsx  # Metrics, charts, alert config, sync trigger
    DashboardPage.tsx      # KPI summary + last sync
    SettingsPage.tsx       # Theme mode, chart style, grid toggle, compact view
  theme/          # Theme system
    theme.css           # Telegram CSS variables + dark mode fallbacks + design tokens
    ThemeProvider.tsx   # Context provider for theme + visualization settings
  telegram/       # Telegram SDK integration
    useTelegram.ts  # ready(), haptics, back button, closing confirmation, main button, viewport
  api/            # API client + hooks
    client.ts      # Fetch wrapper with X-API-Key auth
    hooks.ts       # React Query hooks (subjects, activity, alerts, dashboard, sync)
    types.ts       # Generated OpenAPI types
    openapi.json   # OpenAPI spec
  utils/
    format.ts      # formatCompact, formatRelative
  routes.tsx      # Router configuration
  main.tsx        # App entry (QueryClient + ThemeProvider + Router)
  styles.css      # Global styles, resets, accessibility, animations
```

## Pages

| Path | Page | Description |
|---|---|---|
| `/` | SubjectListPage | Browse + filter subjects with search, platform/status filters |
| `/subjects/:id` | SubjectDetailPage | Metrics, charts (line/bar/area), alert rules, sync trigger |
| `/dashboard` | DashboardPage | KPI summary: total/FB/YT counts, most active platform |
| `/settings` | SettingsPage | Theme mode, chart style, grid toggle, compact view, about |

## Settings & Theme

The Settings page (`/settings`) provides user preferences persisted to `localStorage`:

- **Color scheme:** System (follows Telegram), Light, or Dark
  - In System mode, the app syncs with Telegram's color scheme in real-time via `themeParams.isDark()`
  - Applies to Telegram's header, background, and bottom bar via `miniApp.setHeaderColor/setBackgroundColor/setBottomBarColor`
  - Dark mode CSS variable fallbacks via `[data-theme="dark"]` for non-Telegram environments
- **Chart style:** Line (default), Bar, or Area — applies to all charts instantly
- **Show grid lines:** Toggle background grid visibility in charts
- **Compact view:** Reduces chart height (180px → 140px) to fit more data

## Telegram Platform Integration

- **`miniApp.ready()`** — dismisses loading placeholder early
- **HapticFeedback** — impact (light/medium/heavy) on taps, notification (success/error/warning) on mutations, selection on dropdown changes
- **BackButton** — shown on detail pages, uses native Telegram back button
- **ClosingConfirmation** — enabled during sync operations to prevent accidental close
- **Viewport** — expands to full height, subscribes to height changes for dynamic layout
- **SwipeBehavior** — vertical swipes enabled for natural Telegram navigation
- **Safe Area** — all four insets (top/bottom/left/right) + content safe area respected
- **MainButton** — native Telegram bottom button support via `useTelegram().mainButton.set()`
- **Theme colors** — header, background, and bottom bar colors actively set to match user's theme

## BotFather Config

1. Open [@BotFather](https://t.me/botfather)
2. `/mybots` → select your bot
3. **Bot Settings → Menu Button:** Title = "Social Intelligence", URL = your ngrok/Vite URL
4. **Bot Settings → Domain:** Set to your ngrok domain

## Webhook Setup

```bash
# 1. Start gateway locally
cd social-api-gateway
uvicorn social_api_gateway.main:app --reload --host 0.0.0.0 --port 8000

# 2. Start ngrok
ngrok http 8000   # → https://abc123.ngrok-free.app

# 3. Register webhook
cd scripts
python setup_webhook.py --token <BOT_TOKEN> --url https://abc123.ngrok-free.app/api/telegram-webhook

# 4. Verify
python webhook_info.py --token <BOT_TOKEN>
```

## WebView Test (Manual)

- Open the bot in Telegram
- Send `/start` → welcome message with Mini App button
- Tap the button → Mini App opens, theme matches Telegram
- Browse subjects, tap one for detail + charts
- Create/update/delete alert rules
- Test back button navigation
- Open Settings → toggle dark/light mode, change chart style
- Test dark/light theme switching in Telegram (Settings should reflect changes)