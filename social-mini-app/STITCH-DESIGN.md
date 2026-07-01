# Stitch Design System: SocialMonitor Dark

Extracted from Google Stitch Dark Mode screens (Dashboard Overview, Intelligence Channels, Credentials List).

---

## 1. Visual Atmosphere

Dark, command-center interface with confident asymmetric layouts. The aesthetic is surveillant yet premium — like a SOC dashboard designed by an editorial studio. Density is balanced (5/10), variance moderate (6/10), motion fluid-subtle (5/10). Each element earns its place. No decoration.

## 2. Color Palette (Dark Mode — Unified Core Dark)

- **Obsidian Canvas** (#121318) — Root background. Deep navy-charcoal
- **Surface Container** (#1e1f25) — Card and container fill (Level 1)
- **Surface Elevated** (#292a2f) — Input fields, elevated surfaces, hover states (Level 2)
- **Surface Highest** (#34343a) — Modals, popovers, highest tonal layer
- **Surface Low** (#1a1b21) — Lower-priority containers
- **Surface Lowest** (#0d0e13) — Deepest background tonal
- **Border/Variant** (#404752) — 1px card/container borders, dividers
- **Outline** (#89919d) — Tertiary text, disabled states, secondary outlines
- **Off-White Text** (#e3e1e9) — Primary headings, emphasis text (AAA contrast)
- **Muted Slate** (#bfc7d4) — Body text, descriptions, secondary labels
- **Azure Accent** (#319cf5) — Primary accent for CTAs, active indicators, focus rings
- **Accent Tint** (rgba(49,156,245,0.12)) — Pill backgrounds, status chip fills
- **Light Blue Primary** (#9dcaff) — Primary color for highlights, active nav
- **Green Pulse** (#34c759) — Success, active status, positive delta
- **Amber Warm** (#ff9f0a) — Warning, expiring, medium severity
- **Soft Red** (#ffb4ab) — Danger, revoked, suspended, high severity
- **Error Container** (#93000a) — Error state backgrounds

### Banned
- Pure black (#000000)
- Neon/glow shadows or outer glows
- Purple/violet gradients ("AI aesthetic")
- Oversaturated accents above 80% saturation
- Emoji in any UI context

## 3. Typography

- **Display/Headlines:** Hanken Grotesk — Weight 700, track-tight (-0.02em), `clamp(1.5rem, 4vw, 2rem)`. Sharp, contemporary, authoritative. Hierarchy through weight, not size
- **Body:** Inter — Weight 400, 14px/16px scale, relaxed leading (1.5), Muted Slate color
- **Labels/Metadata:** Geist — Weight 500, 12px, 0.05em letter-spacing. Precise, developer-friendly utility for technical labels and data points

### Banned
- System font stack as primary — use Hanken Grotesk / Inter / Geist
- Generic serif fonts (Times New Roman, Georgia, Garamond)
- Decorative or display fonts for body text

## 4. Component Stylings

- **Cards:** Rounded-2xl (16px), Surface Dark fill, 1px Surface Border, no shadow in dark mode. Internal padding 16px (p-4). Click cards get active:scale-[0.98] push feedback
- **Status Chips:** Rounded-full pill, 8px horizontal padding, accent tint bg (12% opacity), accent text color. 6px gap between dot and label. Dot is 6px (w-1.5 h-1.5) filled circle, pulsing when active
- **Filter Pills:** Rounded-full, Surface Elevated bg for inactive, accent bg for active. Compact padding (px-3 py-1), text-label-sm
- **Search Bar:** Rounded-xl, Surface Elevated bg, search icon left-inset, no border border until focus. Placeholder in Dim Gray
- **Metric Cards:** Compact 2-column grid. Stat label top (text-label-sm, Dim Gray), large number (text-headline-lg or text-3xl, bold), optional delta badge
- **Page Header:** Bold title (text-lg, weight 700), optional action icons (bell, more_vert)
- **Bottom Nav:** Rounded-t, backdrop-blur, icons + labels, active state with filled icon weight
- **Buttons:** Overline/accent-fill for primary CTA. FAB-style floating button for "Add New" actions (bottom-anchored, accent bg)
- **Loaders:** Skeleton shimmer matching card dimensions and rounded corners. Never circular spinners
- **Empty States:** Icon (3xl) + title + description (max-w-xs) + CTA button

## 5. Layout Principles

- **Mobile First:** All screens designed for 375px–480px viewports (Telegram WebView). Single column layouts only
- **Content Width:** Max 480px, centered, px-4 horizontal padding
- **Section Headers:** Uppercase, tracking-wider (letter-spacing), text-label-sm, Muted Silver color, with optional count badge
- **Card Lists:** Stacked single column, 12px gap (gap-3)
- **Grid Splits:** 2-column metric grid (grid-cols-2) with 12px gap for stat cards
- **No Horizontal Scroll:** Critical constraint — all content must fit viewport width
- **Touch Targets:** Minimum 44px for all interactive elements
- **Safe Areas:** Respect --tg-safe-area-inset-bottom for bottom nav offset

## 6. Motion & Interaction

- **Spring Physics:** Active state scale(0.98) on press. Release springs back. Duration ~200ms, ease-out
- **Perpetual Micro:** Status dot pulse animation (1.5s ease-in-out infinite) for active/live indicators
- **Staggered Mount:** Lists cascade via --index multiplier on animation-delay (subtle, ~50ms per item)
- **Performance:** Animate only transform and opacity. Never animat top, left, width, height

## 7. Screen Mapping

| Stitch Screen | Mini-App Page | Primary Function |
|---|---|---|
| Dashboard Overview | /dashboard | System health, aggregate metrics, intelligence logs |
| Intelligence Channels | / | Subject/channel list, search, filter, status overview |
| Credentials List | /credentials | Platform credential management, add/revoke |

## 8. Anti-Patterns (Banned)

- No emojis anywhere in UI
- No pure black (#000000) backgrounds
- No neon shadows or outer glows
- No overlapping elements — clean spatial separation
- No circular spinners — skeleton shimmer only
- No "Loading..." text states — skeleton layout
- No generic placeholder names (Acme, John Doe)
- No AI copywriting clichés (Elevate, Seamless, Unleash)
- No broken image URLs — fallback to initial avatars
- No horizontal scroll on mobile
- No h-screen — use min-h / dvh units
