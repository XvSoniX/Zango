# Styling Architecture & Design Token System

The frontend leverages **Tailwind CSS v4** with a centralized, modular, CSS-first design token architecture.

## Directory Structure

```text
src/styles/
├── README.md                          # Styling rules and token conventions
└── tokens/
    ├── colors.css                     # Brand, surface, text, border, status, sidebar, chart colors (:root & .dark)
    ├── typography.css                 # Font families, sizes, line heights, font weights, letter spacing
    ├── spacing.css                    # Base spacing unit, named scales (4xs -> 6xl), and layout measurements
    ├── radius.css                     # Base radius and harmonic scale (none -> full)
    ├── shadows.css                    # Elevation box shadows for light (:root) and dark (.dark) modes
    ├── breakpoints.css                # Responsive screen breakpoints (:root custom properties & Tailwind @theme)
    ├── theme.css                      # Tailwind CSS v4 @theme inline and @theme bridge
    ├── index.css                      # Central token manifest importing all modules
    └── index.ts                       # TypeScript token constants, types, and DOM helper utilities
```

## Key Integration Points

- `src/index.css`: Main entry point configured in `components.json`. Imports Tailwind v4, tw-animate-css, Shadcn CSS, font assets, and `@import './styles/tokens/index.css';`.
- `src/styles/tokens/`: Central single source of truth for all design tokens.
- `src/styles/tokens/index.ts`: TypeScript contracts (`COLOR_TOKENS`, `BREAKPOINTS`, etc.) and helper utilities (`getCssVar`, `setCssVar`).

## Rules & Conventions

1. **Semantic Tokens First**: Always use semantic utility classes (`bg-background`, `text-foreground`, `bg-brand`, `border-border`) rather than hardcoded palette colors (`bg-blue-600`).
2. **Dynamic Class Merging**: Utilize the `cn()` utility (`@/lib/utils`) for conditional styling and class overrides.
3. **Symmetrical Light & Dark Mode**: Handled via class strategy with OKLCH theme variables declared symmetrically in `:root` and `.dark`.
4. **Single Source of Truth**: Never duplicate token definitions across config files. Mutate tokens exclusively in `src/styles/tokens/`.

## Translation Guide

For full step-by-step procedures on translating external design specifications (Figma/Penpot) into design tokens, refer to the [Design System Integration Guide](../../docs/design-tokens-guide.md).
