# Zango Frontend

React 19 + Vite 8 + TypeScript application for the Zango platform.

## Available Scripts

In the `frontend` directory or repository root, you can run:

- `npm run dev`: Starts the Vite development server on port 3000.
- `npm run build`: Runs TypeScript type-checking (`tsc -b`) and builds the production bundle.
- `npm run preview`: Locally previews the production build on port 3000.
- `npm run lint`: Runs ESLint across all TypeScript and React source files.
- `npm run format`: Formats source files using Prettier.
- `npm test`: Runs the component integration and architecture verification test suites.
- `npm run ui -- <command>`: Executes the Shadcn CLI (e.g. `npm run ui -- add <component>`).

## Architecture & Directory Structure

```text
src/
├── app/                 # Application entry point, global providers, and router
├── assets/              # Client-bundled static assets
├── components/          # Reusable component library
│   ├── ui/              # Headless UI primitives (Shadcn + Radix)
│   └── shared/          # Generic reusable composites (ErrorBoundary, LoadingSpinner)
├── features/            # Feature-based vertical slices
├── hooks/               # Generic custom hooks (useDisclosure, useDebounce, useIsMounted)
├── lib/                 # Utility functions (cn, clsx, twMerge)
├── services/            # Centralized API client & HTTP utilities
├── types/               # TypeScript interfaces and structural contracts
├── config/              # Centralized environment parsing and constants
└── styles/              # Global styles and styling guidelines
```

For full Architectural Decision Records (ADRs), refer to [docs/frontend-architecture.md](../docs/frontend-architecture.md).

## Core Capabilities

- **Router:** React Router v7 data routing architecture with automated client/SSR/memory fallback.
- **API Client:** Centralized Axios instance with request/response interceptors, pluggable token provider, and RFC 7807 (`application/problem+json`) error handling via `ApiError`.
- **Environment Strategy:** Type-safe environment validation via `parseEnv()` with fallback defaults.
- **Component System:** Headless primitives in `components/ui/`, composite layouts in `components/shared/`, and domain features in `features/`.
- **Global Providers:** `AppProvider` centralizing `ErrorBoundary` and `Suspense` fallbacks.
- **Styling:** Tailwind CSS v4 CSS-first design system tokens in `src/index.css`.
