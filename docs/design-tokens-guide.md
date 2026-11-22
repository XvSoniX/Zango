# Design System Integration & Token Infrastructure Guide

This document provides complete architectural specifications, token catalogs, and actionable translation procedures for integrating external design specifications into the Zango frontend application.

---

## 1. Architecture Overview

The design token infrastructure is built on a **CSS-First, centralized token architecture** powered by **Tailwind CSS v4** and **Shadcn UI (radix-nova style)**.

### Core Principles

1. **Centralized Single Source of Truth**: All design tokens are defined in a dedicated directory (`src/styles/tokens/`). No token values are hardcoded in application pages or scattered across multiple configuration files.
2. **Design-Agnostic Placeholders**: The token architecture accommodates brand colors, surfaces, typography, spacing, border radii, shadows, and breakpoints using neutral OKLCH placeholders and standard harmonic scales without predetermining the visual identity.
3. **Decoupled Application Layer**: UI components consume semantic CSS variables and Tailwind utilities (`bg-brand`, `bg-background`, `text-primary`, `p-md`, `rounded-lg`), ensuring zero code changes in pages or components when the final design is delivered.
4. **Symmetrical Theme Support**: Both light (`:root`) and dark (`.dark`) themes are fully supported with matching token keys. Theme switching is handled via Tailwind's `@custom-variant dark (&:is(.dark *));`.
5. **Shadcn/ui & Radix Compatibility**: All 19 foundation variables expected by Shadcn UI primitives (`Button`, `Card`, `Dialog`, `Input`, etc.) remain fully functional and mapped to the centralized token system.
6. **Strict Type Safety**: TypeScript token constants, key types, and DOM helpers (`getCssVar`, `setCssVar`) are provided in `src/styles/tokens/index.ts` under `erasableSyntaxOnly` and `verbatimModuleSyntax` compiler compliance.

---

## 2. Directory & Modular File Organization

The token system is located under `frontend/src/styles/tokens/`:

```text
frontend/src/styles/
├── README.md                          # Styling rules, token conventions, and architectural overview
└── tokens/
    ├── colors.css                     # Brand, surface, text, border, status, sidebar, and chart colors (:root and .dark)
    ├── typography.css                 # Font families, font sizes, line heights, font weights, and tracking
    ├── spacing.css                    # Base unit, named spacing scale (4xs -> 6xl), and layout measurements
    ├── radius.css                     # Base radius and harmonic scale (none -> full)
    ├── shadows.css                    # Elevation box shadows for light (:root) and dark (.dark) modes
    ├── breakpoints.css                # Responsive breakpoints declared as CSS custom properties
    ├── theme.css                      # Tailwind CSS v4 @theme inline and @theme bridge registering utilities
    ├── index.css                      # Central aggregator importing all token modules
    └── index.ts                       # TypeScript token constants, types, and DOM helper utilities
```

### Entry Point Integration

In `frontend/src/index.css`:

```css
@import 'tailwindcss';
@import 'tw-animate-css';
@import 'shadcn/tailwind.css';
@import '@fontsource-variable/geist';

/* Centralized Design Token System */
@import './styles/tokens/index.css';

@custom-variant dark (&:is(.dark *));

@layer base {
  * {
    @apply border-border outline-ring/50;
  }
  body {
    @apply bg-background text-foreground;
  }
  html {
    @apply font-sans;
  }
}
```

---

## 3. Design Token Catalog & Specifications

### 3.1 Brand Colors

Brand tokens accommodate the primary brand identity, interaction states, and an 11-step numerical scale (50–950):

| Token CSS Variable | Tailwind Utility | Placeholder Light | Placeholder Dark | Purpose |
|---|---|---|---|---|
| `--brand` | `bg-brand`, `text-brand` | `var(--primary)` | `var(--primary)` | Primary brand color |
| `--brand-foreground` | `text-brand-foreground` | `var(--primary-foreground)` | `var(--primary-foreground)` | Text on brand surface |
| `--brand-hover` | `hover:bg-brand-hover` | `oklch(0.3 0 0)` | `oklch(0.85 0 0)` | Interactive hover state |
| `--brand-active` | `active:bg-brand-active` | `oklch(0.15 0 0)` | `oklch(0.95 0 0)` | Interactive active/pressed state |
| `--brand-subtle` | `bg-brand-subtle` | `oklch(0.97 0 0)` | `oklch(0.25 0 0)` | Low-emphasis brand backgrounds |
| `--brand-subtle-foreground` | `text-brand-subtle-foreground`| `oklch(0.205 0 0)` | `oklch(0.95 0 0)` | Text on subtle brand backgrounds |
| `--brand-muted` | `bg-brand-muted` | `oklch(0.92 0 0)` | `oklch(0.30 0 0)` | Muted brand badges or chips |
| `--brand-muted-foreground` | `text-brand-muted-foreground` | `oklch(0.556 0 0)` | `oklch(0.708 0 0)` | Subdued brand labels |
| `--brand-emphasis` | `bg-brand-emphasis` | `oklch(0.145 0 0)` | `oklch(0.985 0 0)` | High-contrast brand elements |
| `--brand-secondary` | `bg-brand-secondary` | `var(--secondary)` | `var(--secondary)` | Secondary brand accent |
| `--brand-secondary-foreground` | `text-brand-secondary-foreground` | `var(--secondary-foreground)` | `var(--secondary-foreground)` | Text on secondary brand |
| `--brand-50` ... `--brand-950` | `bg-brand-50` ... `bg-brand-950` | `oklch(0.985 0 0)` -> `oklch(0.145 0 0)` | `oklch(0.985 0 0)` -> `oklch(0.145 0 0)` | 11-step numerical shade scale (50 = lightest tint -> 950 = darkest shade, non-inverted across themes) |

### 3.2 Background & Surface Colors

Surfaces are structured into a semantic hierarchy:

| Token CSS Variable | Tailwind Utility | Light Value | Dark Value | Purpose |
|---|---|---|---|---|
| `--background` | `bg-background` | `oklch(1 0 0)` | `oklch(0.145 0 0)` | Main application background (canvas) |
| `--card` | `bg-card` | `oklch(1 0 0)` | `oklch(0.205 0 0)` | Card containers and elevated panels |
| `--popover` | `bg-popover` | `oklch(1 0 0)` | `oklch(0.205 0 0)` | Dialogs, menus, tooltips, popovers |
| `--muted` | `bg-muted` | `oklch(0.97 0 0)` | `oklch(0.269 0 0)` | Muted panels and inactive containers |
| `--accent` | `bg-accent` | `oklch(0.97 0 0)` | `oklch(0.269 0 0)` | Hover highlights and accented surfaces |
| `--surface-canvas` | `bg-surface-canvas` | `var(--background)` | `var(--background)` | Alias for application canvas |
| `--surface-card` | `bg-surface-card` | `var(--card)` | `var(--card)` | Alias for card container |
| `--surface-elevated` | `bg-surface-elevated` | `var(--popover)` | `var(--popover)` | Floating panels and modals |
| `--surface-subtle` | `bg-surface-subtle` | `oklch(0.985 0 0)` | `oklch(0.18 0 0)` | Subtle table zebra-striping |
| `--surface-sunken` | `bg-surface-sunken` | `oklch(0.95 0 0)` | `oklch(0.10 0 0)` | Inset wells and code blocks |
| `--surface-overlay` | `bg-surface-overlay` | `oklch(0 0 0 / 0.5)` | `oklch(0 0 0 / 0.7)` | Modal backdrop dimmers |

### 3.3 Text Colors

| Token CSS Variable | Tailwind Utility | Light Value | Dark Value | Purpose |
|---|---|---|---|---|
| `--foreground` | `text-foreground` | `oklch(0.145 0 0)` | `oklch(0.985 0 0)` | Default high-contrast text |
| `--muted-foreground` | `text-muted-foreground` | `oklch(0.556 0 0)` | `oklch(0.708 0 0)` | Subdued text, hints, captions |
| `--text-primary` | `text-primary`, `text-text-primary` | `var(--foreground)` | `var(--foreground)` | Explicit semantic primary text |
| `--text-secondary` | `text-secondary`, `text-text-secondary` | `var(--muted-foreground)` | `var(--muted-foreground)` | Explicit semantic secondary text |
| `--text-tertiary` | `text-tertiary`, `text-text-tertiary` | `oklch(0.65 0 0)` | `oklch(0.55 0 0)` | Low-contrast tertiary metadata |
| `--text-disabled` | `text-disabled`, `text-text-disabled` | `oklch(0.75 0 0)` | `oklch(0.40 0 0)` | Disabled labels and placeholders |
| `--text-inverse` | `text-inverse`, `text-text-inverse` | `var(--background)` | `var(--background)` | Inverse text for dark badges |
| `--text-link` | `text-link`, `text-text-link` | `var(--primary)` | `var(--primary)` | Anchor hyperlink text |
| `--text-link-hover` | `text-link-hover`, `text-text-link-hover` | `oklch(0.35 0 0)` | `oklch(0.80 0 0)` | Anchor hyperlink hover |
| `--text-status-success` | `text-status-success`, `text-text-status-success` | `oklch(0.62 0.17 145)` | `oklch(0.75 0.16 145)` | Success messages & badges |
| `--text-status-warning` | `text-status-warning`, `text-text-status-warning` | `oklch(0.75 0.15 75)` | `oklch(0.82 0.14 75)` | Warning messages & badges |
| `--text-status-danger` | `text-status-danger`, `text-text-status-danger` | `var(--destructive)` | `var(--destructive)` | Danger/error messages |
| `--text-status-info` | `text-status-info`, `text-text-status-info` | `oklch(0.60 0.15 240)` | `oklch(0.75 0.14 240)` | Informational messages |

### 3.4 Border Colors

| Token CSS Variable | Tailwind Utility | Light Value | Dark Value | Purpose |
|---|---|---|---|---|
| `--border` | `border-border` | `oklch(0.922 0 0)` | `oklch(1 0 0 / 10%)` | Default container border |
| `--input` | `border-input` | `oklch(0.922 0 0)` | `oklch(1 0 0 / 15%)` | Form field outline |
| `--ring` | `ring-ring` | `oklch(0.708 0 0)` | `oklch(0.556 0 0)` | Focus indicator ring |
| `--border-subtle` | `border-subtle`, `border-border-subtle` | `oklch(0.95 0 0)` | `oklch(1 0 0 / 6%)` | Subtle dividers and row lines |
| `--border-default` | `border-border-default` | `var(--border)` | `var(--border)` | Alias for default container border |
| `--border-strong` | `border-strong`, `border-border-strong` | `oklch(0.75 0 0)` | `oklch(1 0 0 / 22%)` | Emphasized structural borders |
| `--border-interactive` | `border-interactive`, `border-border-interactive` | `var(--input)` | `var(--input)` | Interactive control borders |
| `--border-focus` | `border-focus`, `border-border-focus` | `var(--ring)` | `var(--ring)` | Focus highlight border |
| `--border-disabled` | `border-disabled`, `border-border-disabled` | `oklch(0.96 0 0)` | `oklch(1 0 0 / 5%)` | Disabled control borders |

### 3.5 Typography (Families, Scales, Weights, Tracking)

#### Font Families
- `--font-family-sans`: `'Geist Variable', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif` -> `font-sans`
- `--font-family-heading`: `var(--font-family-sans)` -> `font-heading`
- `--font-family-mono`: `ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace` -> `font-mono`
- `--font-family-serif`: `ui-serif, Georgia, Cambria, 'Times New Roman', Times, serif` -> `font-serif`

#### Typographic Scale
| Step | Font Size Variable | Line Height Variable | Size Value | Line Height Value | Tailwind Class |
|---|---|---|---|---|---|
| `2xs` | `--font-size-2xs` | `--line-height-2xs` | `0.6875rem` (11px) | `0.875rem` (14px) | `text-2xs` |
| `xs` | `--font-size-xs` | `--line-height-xs` | `0.75rem` (12px) | `1rem` (16px) | `text-xs` |
| `sm` | `--font-size-sm` | `--line-height-sm` | `0.875rem` (14px) | `1.25rem` (20px) | `text-sm` |
| `base` | `--font-size-base` | `--line-height-base` | `1rem` (16px) | `1.5rem` (24px) | `text-base` |
| `lg` | `--font-size-lg` | `--line-height-lg` | `1.125rem` (18px) | `1.75rem` (28px) | `text-lg` |
| `xl` | `--font-size-xl` | `--line-height-xl` | `1.25rem` (20px) | `1.75rem` (28px) | `text-xl` |
| `2xl` | `--font-size-2xl` | `--line-height-2xl` | `1.5rem` (24px) | `2rem` (32px) | `text-2xl` |
| `3xl` | `--font-size-3xl` | `--line-height-3xl` | `1.875rem` (30px) | `2.25rem` (36px) | `text-3xl` |
| `4xl` | `--font-size-4xl` | `--line-height-4xl` | `2.25rem` (36px) | `2.5rem` (40px) | `text-4xl` |
| `5xl` | `--font-size-5xl` | `--line-height-5xl` | `3rem` (48px) | `1` | `text-5xl` |
| `6xl` | `--font-size-6xl` | `--line-height-6xl` | `3.75rem` (60px) | `1` | `text-6xl` |

#### Font Weights
- `100` (`--font-weight-thin` -> `font-thin`)
- `300` (`--font-weight-light` -> `font-light`)
- `400` (`--font-weight-normal` -> `font-normal`)
- `500` (`--font-weight-medium` -> `font-medium`)
- `600` (`--font-weight-semibold` -> `font-semibold`)
- `700` (`--font-weight-bold` -> `font-bold`)
- `800` (`--font-weight-extrabold` -> `font-extrabold`)

#### Letter Spacing
- `--letter-spacing-tighter` (`-0.05em`) -> `tracking-tighter`
- `--letter-spacing-tight` (`-0.025em`) -> `tracking-tight`
- `--letter-spacing-normal` (`0em`) -> `tracking-normal`
- `--letter-spacing-wide` (`0.025em`) -> `tracking-wide`
- `--letter-spacing-wider` (`0.05em`) -> `tracking-wider`

### 3.6 Spacing & Layout

- Base unit: `--spacing-base: 0.25rem;` (4px).
- Scaled tokens:
  - `4xs` (`0.125rem` / 2px)
  - `3xs` (`0.25rem` / 4px)
  - `2xs` (`0.375rem` / 6px)
  - `xs` (`0.5rem` / 8px)
  - `sm` (`0.75rem` / 12px)
  - `md` (`1rem` / 16px)
  - `lg` (`1.5rem` / 24px)
  - `xl` (`2rem` / 32px)
  - `2xl` (`2.5rem` / 40px)
  - `3xl` (`3rem` / 48px)
  - `4xl` (`4rem` / 64px)
  - `5xl` (`5rem` / 80px)
  - `6xl` (`6rem` / 96px)
- Semantic layout tokens:
  - `--spacing-gutter: var(--spacing-md);` (16px grid gutter)
  - `--spacing-container-padding: var(--spacing-lg);` (24px page padding)
  - `--spacing-header-height: 3.5rem;` (56px top app bar)
  - `--spacing-sidebar-width: 16rem;` (256px navigation sidebar)

### 3.7 Border Radius

Derived harmonically from baseline `--radius: 0.625rem;` (10px):

| Step | Expression | Value | Tailwind Class |
|---|---|---|---|
| `none` | `0px` | `0px` | `rounded-none` |
| `2xs` | `calc(var(--radius) * 0.4)` | `4px` | `rounded-2xs` |
| `xs` | `calc(var(--radius) * 0.5)` | `5px` | `rounded-xs` |
| `sm` | `calc(var(--radius) * 0.6)` | `6px` | `rounded-sm` |
| `md` | `calc(var(--radius) * 0.8)` | `8px` | `rounded-md` |
| `lg` | `var(--radius)` | `10px` | `rounded-lg` |
| `xl` | `calc(var(--radius) * 1.4)` | `14px` | `rounded-xl` |
| `2xl` | `calc(var(--radius) * 1.8)` | `18px` | `rounded-2xl` |
| `3xl` | `calc(var(--radius) * 2.2)` | `22px` | `rounded-3xl` |
| `4xl` | `calc(var(--radius) * 2.6)` | `26px` | `rounded-4xl` |
| `full` | `9999px` | `9999px` | `rounded-full` |

### 3.8 Shadows & Spatial Elevation

| Step | Tailwind Class | Light Mode Elevation | Dark Mode Elevation |
|---|---|---|---|
| `none` | `shadow-none` | `0 0 #0000` | `0 0 #0000` |
| `2xs` | `shadow-2xs` | `0 1px 2px 0 rgb(0 0 0 / 0.05)` | `0 1px 2px 0 rgb(0 0 0 / 0.35)` |
| `xs` | `shadow-xs` | `0 1px 3px 0 rgb(0 0 0 / 0.08), 0 1px 2px -1px rgb(0 0 0 / 0.08)` | `0 1px 3px 0 rgb(0 0 0 / 0.4), 0 1px 2px -1px rgb(0 0 0 / 0.4)` |
| `sm` | `shadow-sm` | `0 2px 4px -1px rgb(0 0 0 / 0.06), 0 4px 6px -1px rgb(0 0 0 / 0.08)` | `0 2px 4px -1px rgb(0 0 0 / 0.35), 0 4px 6px -1px rgb(0 0 0 / 0.45)` |
| `md` | `shadow-md` | `0 4px 6px -2px rgb(0 0 0 / 0.05), 0 10px 15px -3px rgb(0 0 0 / 0.08)` | `0 4px 6px -2px rgb(0 0 0 / 0.35), 0 10px 15px -3px rgb(0 0 0 / 0.45)` |
| `lg` | `shadow-lg` | `0 10px 15px -3px rgb(0 0 0 / 0.05), 0 20px 25px -5px rgb(0 0 0 / 0.08)` | `0 10px 15px -3px rgb(0 0 0 / 0.35), 0 20px 25px -5px rgb(0 0 0 / 0.45)` |
| `xl` | `shadow-xl` | `0 25px 50px -12px rgb(0 0 0 / 0.18)` | `0 25px 50px -12px rgb(0 0 0 / 0.55)` |
| `2xl` | `shadow-2xl` | `0 35px 60px -15px rgb(0 0 0 / 0.22)` | `0 35px 60px -15px rgb(0 0 0 / 0.65)` |
| `inner` | `shadow-inner`| `inset 0 2px 4px 0 rgb(0 0 0 / 0.05)` | `inset 0 2px 4px 0 rgb(0 0 0 / 0.3)` |

### 3.9 Responsive Breakpoints

Centralized in `breakpoints.css` as a single source of truth declaring both `:root` custom properties and Tailwind CSS v4 `@theme` media queries (preventing token duplication across files):

| Token | Min Width | Pixels | Media Query Usage |
|---|---|---|---|
| `2xs` | `24rem` | 384px | `@media (width >= 24rem)` / `2xs:...` |
| `xs` | `30rem` | 480px | `@media (width >= 30rem)` / `xs:...` |
| `sm` | `40rem` | 640px | `@media (width >= 40rem)` / `sm:...` |
| `md` | `48rem` | 768px | `@media (width >= 48rem)` / `md:...` |
| `lg` | `64rem` | 1024px | `@media (width >= 64rem)` / `lg:...` |
| `xl` | `80rem` | 1280px | `@media (width >= 80rem)` / `xl:...` |
| `2xl` | `96rem` | 1536px | `@media (width >= 96rem)` / `2xl:...` |

---

## 4. Translating Future Design Specifications

When the final design specification arrives (e.g. from Figma, Penpot, or a brand style guide), follow this step-by-step translation process.

### Step 1: Converting Design Colors to OKLCH

We recommend **OKLCH** color format for perceptually uniform lightness across color palettes:
- `L`: Lightness (0% to 100% or 0 to 1)
- `C`: Chroma / saturation (0 to ~0.37)
- `H`: Hue angle (0 to 360 degrees)

If the design specification provides HEX or RGB colors (e.g., `#2563EB`):
1. Convert `#2563EB` to OKLCH: `oklch(0.55 0.22 254)`
2. For light mode (`:root` in `colors.css`):
   ```css
   --brand: oklch(0.55 0.22 254);
   --brand-foreground: oklch(0.99 0 0);
   --brand-hover: oklch(0.48 0.22 254);
   --brand-active: oklch(0.42 0.22 254);
   ```
3. For dark mode (`.dark` in `colors.css`):
   ```css
   --brand: oklch(0.68 0.20 254);
   --brand-foreground: oklch(0.12 0.05 254);
   --brand-hover: oklch(0.74 0.18 254);
   ```
4. If the design provides an 11-step brand ramp (50–950), replace `--brand-50` through `--brand-950` in `colors.css`.

### Step 2: Translating Font Families & Typography

1. **Install font packages** (e.g. via `@fontsource` or self-hosted variable woff2):
   ```bash
   npm --prefix frontend install @fontsource-variable/inter
   ```
2. **Import font in `src/index.css`**:
   ```css
   @import '@fontsource-variable/inter';
   ```
3. **Update `--font-family-*` in `src/styles/tokens/typography.css`**:
   ```css
   --font-family-sans: 'Inter Variable', sans-serif;
   --font-family-heading: 'Cabinet Grotesk Variable', sans-serif;
   ```
4. **Adjust font size and line height steps** in `typography.css` if the design uses custom scale multipliers (e.g., Major Third 1.25x or Perfect Fourth 1.333x).

### Step 3: Translating Spacing & Radius

1. If the design system uses an **8px grid** rather than 4px:
   In `src/styles/tokens/spacing.css`:
   ```css
   --spacing-base: 0.5rem; /* 8px */
   ```
2. If the design system specifies a **brand corner radius** (e.g. 12px or pill-shaped 9999px):
   In `src/styles/tokens/radius.css`:
   ```css
   --radius: 0.75rem; /* 12px */
   ```
   All derived radius variants (`rounded-sm`, `rounded-md`, `rounded-lg`, `rounded-xl`) will automatically recalculate!

### Step 4: Translating Shadows & Elevation

1. Copy the box shadow blur, spread, and color definitions from Figma.
2. In `src/styles/tokens/shadows.css`, update `--shadow-xs`, `--shadow-sm`, `--shadow-md`, `--shadow-lg`, `--shadow-xl`.
3. In `.dark`, increase shadow opacity or add subtle ambient illumination.

### Step 5: Verification & Production Build

Always verify changes with the built-in automated test suite:

```bash
# Run complete verification (Shadcn primitives, architecture, skills, design tokens)
npm test

# Run TypeScript typecheck and production build
npm --prefix frontend run build
```

---

## 5. TypeScript Usage & DOM Helpers

The token infrastructure exports typed contracts and DOM manipulation utilities from `@/styles/tokens`:

```tsx
import {
  COLOR_TOKENS,
  SPACING_TOKENS,
  BREAKPOINTS,
  getCssVar,
  setCssVar,
} from '@/styles/tokens';

// Access evaluated CSS variable at runtime (e.g., for Canvas or Chart.js)
const primaryColor = getCssVar(COLOR_TOKENS.primary);

// Dynamically override a theme variable (e.g., in a tenant theme switcher)
setCssVar(COLOR_TOKENS.brand, 'oklch(0.6 0.25 150)');

// Type-safe breakpoint reference for custom matchMedia hooks
const isMobile = window.matchMedia(`(max-width: ${BREAKPOINTS.sm})`).matches;
```

---

## 6. Prohibited Anti-Patterns

1. **NO Hardcoded Palette Colors in Application Code**: Never write `bg-blue-600` or `text-gray-900` in UI components. Use `bg-primary`, `bg-brand`, or `text-foreground`.
2. **NO Arbitrary Pixel Spacing Hacks**: Never write `p-[19px]`. Use standard spacing classes (`p-md`, `p-4`, `gap-xs`).
3. **NO Direct Mutation of Multiple CSS Files**: Do not define color values in `components.json` or `vite.config.ts`. The single source of truth is `src/styles/tokens/`.
4. **NO Invented Brand Identifiers**: Do not declare ad-hoc color names like `--color-flamingo` or `--color-mint`. Map all brand variations to the semantic `--brand-*` tokens.
