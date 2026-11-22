/**
 * Design Tokens TypeScript Definitions & Utilities
 * Provides type contracts, token constants, and runtime helpers for CSS variables.
 */

export const BRAND_SCALE = [
  '50',
  '100',
  '200',
  '300',
  '400',
  '500',
  '600',
  '700',
  '800',
  '900',
  '950',
] as const

export type BrandScaleStep = (typeof BRAND_SCALE)[number]

export const COLOR_TOKENS = {
  // Base surfaces
  background: '--background',
  foreground: '--foreground',
  card: '--card',
  cardForeground: '--card-foreground',
  popover: '--popover',
  popoverForeground: '--popover-foreground',

  // Actions & States
  primary: '--primary',
  primaryForeground: '--primary-foreground',
  secondary: '--secondary',
  secondaryForeground: '--secondary-foreground',
  muted: '--muted',
  mutedForeground: '--muted-foreground',
  accent: '--accent',
  accentForeground: '--accent-foreground',
  destructive: '--destructive',
  destructiveForeground: '--destructive-foreground',

  // Borders & Rings
  border: '--border',
  input: '--input',
  ring: '--ring',

  // Brand Tokens
  brand: '--brand',
  brandForeground: '--brand-foreground',
  brandHover: '--brand-hover',
  brandActive: '--brand-active',
  brandSubtle: '--brand-subtle',
  brandSubtleForeground: '--brand-subtle-foreground',
  brandMuted: '--brand-muted',
  brandMutedForeground: '--brand-muted-foreground',
  brandEmphasis: '--brand-emphasis',
  brandSecondary: '--brand-secondary',
  brandSecondaryForeground: '--brand-secondary-foreground',

  // Brand Scale Tokens
  brand50: '--brand-50',
  brand100: '--brand-100',
  brand200: '--brand-200',
  brand300: '--brand-300',
  brand400: '--brand-400',
  brand500: '--brand-500',
  brand600: '--brand-600',
  brand700: '--brand-700',
  brand800: '--brand-800',
  brand900: '--brand-900',
  brand950: '--brand-950',

  // Chart Tokens
  chart1: '--chart-1',
  chart2: '--chart-2',
  chart3: '--chart-3',
  chart4: '--chart-4',
  chart5: '--chart-5',

  // Sidebar Tokens
  sidebar: '--sidebar',
  sidebarForeground: '--sidebar-foreground',
  sidebarPrimary: '--sidebar-primary',
  sidebarPrimaryForeground: '--sidebar-primary-foreground',
  sidebarAccent: '--sidebar-accent',
  sidebarAccentForeground: '--sidebar-accent-foreground',
  sidebarBorder: '--sidebar-border',
  sidebarRing: '--sidebar-ring',

  // Surface Hierarchy
  surfaceCanvas: '--surface-canvas',
  surfaceCard: '--surface-card',
  surfaceElevated: '--surface-elevated',
  surfaceMuted: '--surface-muted',
  surfaceSubtle: '--surface-subtle',
  surfaceSunken: '--surface-sunken',
  surfaceOverlay: '--surface-overlay',

  // Text Hierarchy
  textPrimary: '--text-primary',
  textSecondary: '--text-secondary',
  textTertiary: '--text-tertiary',
  textDisabled: '--text-disabled',
  textInverse: '--text-inverse',
  textLink: '--text-link',
  textLinkHover: '--text-link-hover',
  textStatusSuccess: '--text-status-success',
  textStatusWarning: '--text-status-warning',
  textStatusDanger: '--text-status-danger',
  textStatusInfo: '--text-status-info',

  // Border Hierarchy
  borderSubtle: '--border-subtle',
  borderDefault: '--border-default',
  borderStrong: '--border-strong',
  borderInteractive: '--border-interactive',
  borderFocus: '--border-focus',
  borderDisabled: '--border-disabled',
} as const

export type ColorTokenKey = keyof typeof COLOR_TOKENS
export type ColorTokenCssVar = (typeof COLOR_TOKENS)[ColorTokenKey]

export const FONT_FAMILIES = {
  sans: '--font-family-sans',
  heading: '--font-family-heading',
  mono: '--font-family-mono',
  serif: '--font-family-serif',
} as const

export type FontFamilyKey = keyof typeof FONT_FAMILIES

export const FONT_SIZES = {
  '2xs': '--font-size-2xs',
  xs: '--font-size-xs',
  sm: '--font-size-sm',
  base: '--font-size-base',
  lg: '--font-size-lg',
  xl: '--font-size-xl',
  '2xl': '--font-size-2xl',
  '3xl': '--font-size-3xl',
  '4xl': '--font-size-4xl',
  '5xl': '--font-size-5xl',
  '6xl': '--font-size-6xl',
} as const

export type FontSizeKey = keyof typeof FONT_SIZES

export const FONT_WEIGHTS = {
  thin: '--font-weight-thin',
  light: '--font-weight-light',
  normal: '--font-weight-normal',
  medium: '--font-weight-medium',
  semibold: '--font-weight-semibold',
  bold: '--font-weight-bold',
  extrabold: '--font-weight-extrabold',
} as const

export type FontWeightKey = keyof typeof FONT_WEIGHTS

export const LINE_HEIGHTS = {
  '2xs': '--line-height-2xs',
  xs: '--line-height-xs',
  sm: '--line-height-sm',
  base: '--line-height-base',
  lg: '--line-height-lg',
  xl: '--line-height-xl',
  '2xl': '--line-height-2xl',
  '3xl': '--line-height-3xl',
  '4xl': '--line-height-4xl',
  '5xl': '--line-height-5xl',
  '6xl': '--line-height-6xl',
} as const

export type LineHeightKey = keyof typeof LINE_HEIGHTS

export const LETTER_SPACING = {
  tighter: '--letter-spacing-tighter',
  tight: '--letter-spacing-tight',
  normal: '--letter-spacing-normal',
  wide: '--letter-spacing-wide',
  wider: '--letter-spacing-wider',
} as const

export type LetterSpacingKey = keyof typeof LETTER_SPACING

export const BRAND_SCALE_TOKENS = {
  '50': '--brand-50',
  '100': '--brand-100',
  '200': '--brand-200',
  '300': '--brand-300',
  '400': '--brand-400',
  '500': '--brand-500',
  '600': '--brand-600',
  '700': '--brand-700',
  '800': '--brand-800',
  '900': '--brand-900',
  '950': '--brand-950',
} as const

export const SPACING_TOKENS = {
  base: '--spacing-base',
  '4xs': '--spacing-4xs',
  '3xs': '--spacing-3xs',
  '2xs': '--spacing-2xs',
  xs: '--spacing-xs',
  sm: '--spacing-sm',
  md: '--spacing-md',
  lg: '--spacing-lg',
  xl: '--spacing-xl',
  '2xl': '--spacing-2xl',
  '3xl': '--spacing-3xl',
  '4xl': '--spacing-4xl',
  '5xl': '--spacing-5xl',
  '6xl': '--spacing-6xl',
  gutter: '--spacing-gutter',
  containerPadding: '--spacing-container-padding',
  headerHeight: '--spacing-header-height',
  sidebarWidth: '--spacing-sidebar-width',
} as const

export type SpacingTokenKey = keyof typeof SPACING_TOKENS

export const RADIUS_TOKENS = {
  base: '--radius',
  none: '--radius-none',
  '2xs': '--radius-2xs',
  xs: '--radius-xs',
  sm: '--radius-sm',
  md: '--radius-md',
  lg: '--radius-lg',
  xl: '--radius-xl',
  '2xl': '--radius-2xl',
  '3xl': '--radius-3xl',
  '4xl': '--radius-4xl',
  full: '--radius-full',
} as const

export type RadiusTokenKey = keyof typeof RADIUS_TOKENS

export const SHADOW_TOKENS = {
  none: '--shadow-none',
  '2xs': '--shadow-2xs',
  xs: '--shadow-xs',
  sm: '--shadow-sm',
  md: '--shadow-md',
  lg: '--shadow-lg',
  xl: '--shadow-xl',
  '2xl': '--shadow-2xl',
  inner: '--shadow-inner',
} as const

export type ShadowTokenKey = keyof typeof SHADOW_TOKENS

export const BREAKPOINTS = {
  '2xs': '24rem', // 384px
  xs: '30rem', // 480px
  sm: '40rem', // 640px
  md: '48rem', // 768px
  lg: '64rem', // 1024px
  xl: '80rem', // 1280px
  '2xl': '96rem', // 1536px
} as const

export type BreakpointKey = keyof typeof BREAKPOINTS

/**
 * Normalizes a token name to ensure it starts with the CSS custom property '--' prefix.
 */
export function normalizeCssVarName(name: string): string {
  return name.startsWith('--') ? name : `--${name}`
}

/**
 * Retrieves the evaluated computed value of a CSS custom property from the DOM.
 * Accepts token names with or without the leading '--' prefix.
 */
export function getCssVar(name: string, element?: Element): string {
  if (typeof window === 'undefined') return ''
  const propName = normalizeCssVarName(name)
  const target = element ?? document.documentElement
  return window.getComputedStyle(target).getPropertyValue(propName).trim()
}

/**
 * Sets a CSS custom property on an element (defaults to :root / documentElement).
 * Accepts token names with or without the leading '--' prefix.
 */
export function setCssVar(
  name: string,
  value: string,
  element?: HTMLElement | SVGElement | null,
): void {
  if (typeof document === 'undefined') return
  const propName = normalizeCssVarName(name)
  const target = (element ?? document.documentElement) as HTMLElement | SVGElement | undefined
  if (target && typeof target.style?.setProperty === 'function') {
    target.style.setProperty(propName, value)
  }
}
