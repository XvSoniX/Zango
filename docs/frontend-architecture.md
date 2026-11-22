# Frontend Architectural Decision Record (ADR) & System Architecture

## Overview

This document outlines the architectural foundation established for the Zango React frontend application. The architecture is engineered for scalability, maintainability, type safety, modular feature boundaries, and seamless integration with backend microservices (Gateway, Auth, Discovery).

---

## 1. Directory Structure

The project implements a modular, feature-oriented directory structure under `src/`:

```text
src/
├── app/                 # Application root, routing definitions, global providers
│   ├── App.tsx          # Root application entry component
│   ├── provider.tsx     # Global provider hierarchy (ErrorBoundary, Suspense)
│   ├── router.tsx       # React Router component wrapper
│   ├── routes.tsx       # Route definitions & router factory (Browser / Memory)
│   ├── root-view.tsx    # Default root view harness
│   ├── not-found-view.tsx # 404 fallback view
│   └── index.ts         # App module barrel export
├── assets/              # Client-bundled static assets (SVG, PNG, fonts)
│   └── README.md        # Asset guidelines and import conventions
├── components/          # Reusable component library
│   ├── ui/              # Headless & design system primitives (Shadcn + Radix)
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── dialog.tsx
│   │   └── input.tsx
│   └── shared/          # Generic domain-agnostic UI composites
│       ├── error-boundary.tsx
│       ├── loading-spinner.tsx
│       └── index.ts
├── features/            # Feature modules (Vertical Slice Architecture)
│   └── README.md        # Architecture guidelines, conventions, and module boundaries
├── hooks/               # Generic reusable React hooks
│   ├── use-disclosure.ts
│   ├── use-debounce.ts
│   ├── use-is-mounted.ts
│   └── index.ts
├── lib/                 # Third-party wrappers and utility functions
│   ├── utils.ts         # Class merging (cn) helper combining clsx and twMerge
│   └── index.ts
├── services/            # Centralized API layer
│   ├── api/
│   │   ├── api-client.ts # Centralized Axios instance, interceptors, and http methods
│   │   ├── api-error.ts  # Standardized ApiError mapping RFC 7807 problem+json
│   │   └── index.ts
│   └── index.ts
├── types/               # Global TypeScript contracts
│   ├── api.ts           # HTTP types, ApiResponse, ApiErrorResponse, TokenProvider
│   ├── common.ts        # Common utility types (Nullable, PaginatedResult, AsyncState)
│   └── index.ts
├── config/              # Centralized configuration & environment parsing
│   ├── env.ts           # Type-safe environment variable parser with fallbacks
│   ├── constants.ts     # HTTP status codes, router paths, storage keys
│   └── index.ts         # Centralized frozen appConfig object
└── styles/              # Global styles & centralized design tokens
    ├── README.md        # Styling rules, token conventions, and architectural overview
    └── tokens/          # Centralized design token system
        ├── colors.css   # Brand, surface, text, border, status, sidebar, chart colors
        ├── typography.css # Font families, sizes, line heights, font weights, tracking
        ├── spacing.css  # Base unit, named scales (4xs -> 6xl), layout measurements
        ├── radius.css   # Base radius and harmonic scale (none -> full)
        ├── shadows.css  # Elevation box shadows for light and dark modes
        ├── breakpoints.css # Responsive screen breakpoints
        ├── theme.css    # Tailwind CSS v4 @theme inline and @theme bridge
        ├── index.css    # Central token manifest importing all modules
        └── index.ts     # TypeScript token constants, types, and DOM helpers
```

---

## 2. Key Architectural Decisions

### ADR-01: Application Entry Points & Provider Hierarchy (`src/app/`)
- **Decision:** Separate the DOM mounting (`main.tsx`), the root application component (`app/App.tsx`), the provider hierarchy (`app/provider.tsx`), and route declarations (`app/routes.tsx`).
- **Rationale:** Ensures clean separation of concerns. `AppProvider` centralizes global cross-cutting concerns (such as the top-level `ErrorBoundary` and `Suspense` fallbacks) without cluttering page routing or individual components.
- **Provider Order:**
  ```text
  StrictMode -> AppProvider (ErrorBoundary -> Suspense) -> AppRouter (RouterProvider)
  ```

### ADR-02: React Router Integration (`src/app/routes.tsx` & `src/app/router.tsx`)
- **Decision:** Utilize React Router v7 Data Router architecture via `createBrowserRouter` for browser environments, and provide a unified factory (`createAppRouter`) that automatically falls back to `createMemoryRouter` in non-browser/SSR/test environments or when `initialEntries` are supplied, alongside a `resetDefaultRouter()` test utility.
- **Rationale:** Provides seamless compatibility between browser execution, server-side rendering, and automated integration testing without requiring environment branching in application view code.
- **Conventions:**
  - Route configurations are declared as an array of `RouteObject`.
  - A fallback route (`path: '*'`) renders `NotFoundView` with an accessible return mechanism.

### ADR-03: Centralized API Client & Axios Architecture (`src/services/api/`)
- **Decision:** Establish a centralized Axios client (`apiClient`) with a factory function (`createApiClient`) and standardized wrapper helpers (`http.request`, `http.get`, `http.post`, etc.).
- **Interceptors:**
  - **Request Interceptor:** Automatically configures standard JSON headers (`Content-Type: application/json`, `Accept: application/json`) and supports a pluggable `TokenProvider` hook via `setAuthTokenProvider()` to inject `Authorization: Bearer <token>` dynamically without hardcoding authentication workflows prematurely. If the token provider rejects or throws, the request interceptor escalates the error as an `ApiError` rather than dispatching unauthenticated requests.
  - **Response Interceptor:** Automatically catches request/network/timeout/cancellation errors and normalizes them into a domain-specific `ApiError`.

### ADR-04: API Error Handling, Cancellation & RFC 7807 Compatibility (`src/services/api/api-error.ts`)
- **Decision:** Map all HTTP, network, timeout, and cancellation errors into an immutable `ApiError` class extending native JavaScript `Error`.
- **Backend Alignment:** Specifically aligned with the backend microservices' RFC 7807 (`application/problem+json`) responses and Gateway distributed tracing:
  - `status`: HTTP status code (or `0` for network failures/cancellations, `408` for timeouts).
  - `code`: Domain error code (e.g. `BAD_REQUEST`, `AUTHENTICATION_FAILED`, `REQUEST_CANCELED`, or `HTTP_{status}`).
  - `message`: Extracted from `detail`, `message`, or `title`.
  - `details`: Extracted from `details`, validation `errors` list, or raw array.
  - `correlationId`: Distributed tracing identifier extracted from problem JSON body or `X-Correlation-ID` response headers forwarded from the Gateway/Auth services.
  - `instance`: URI path of the failed request.
  - `type`: RFC 7807 problem type URI.
  - `isCanceled`: Boolean indicating request cancellation via `AbortController` or Axios cancellation, preventing spurious network error alerts in debounced search and unmounting views.
  - `isNetworkError`: Boolean indicating unreachable server disconnection.
  - `isTimeout`: Boolean indicating request deadline expiration.

### ADR-05: Environment Variable Strategy & Dev Server Proxy (`src/config/`, `vite.config.ts`)
- **Decision:** Encapsulate `import.meta.env` access inside `src/config/env.ts` with a pure `parseEnv()` function providing type-safe validation and sane fallbacks, with defensive support for Node/testing runtimes. Configure Vite dev server proxy for `/api` routing directly to the Spring Boot Gateway (`http://localhost:8080`).
- **Variables Supported:**
  - `VITE_API_BASE_URL`: Base URL for gateway/microservices (defaults to `/api`).
  - `VITE_APP_NAME`: Application display name (defaults to `Zango`).
  - `VITE_APP_ENV`: Environment identifier (`development` | `production` | `test`).
  - `VITE_API_TIMEOUT`: Network timeout in milliseconds (defaults to `15000` ms).
- **Security & Immutability:** All configurations are exposed via frozen, read-only objects (`appConfig`). Client bundles never contain sensitive secrets.

### ADR-06: Component Categorization & Reusability Conventions (`src/components/`)
- **Decision:** Adopt a three-tier component taxonomy:
  1. `src/components/ui/`: Atomic, headless design primitives built on Radix UI and Tailwind CSS v4 (managed via Shadcn CLI). Must remain domain-agnostic.
  2. `src/components/shared/`: Shared layout, feedback, and cross-feature composites (e.g. `ErrorBoundary` with thrown string normalization and `resetKeys` support, `LoadingSpinner`).
  3. `src/features/{feature}/components/`: Domain-specific components bound strictly to individual feature workflows.

### ADR-07: Custom Hooks Standards (`src/hooks/`)
- **Decision:** House general-purpose React hooks in `src/hooks/` adhering to strict naming (`use*`), single-responsibility principle, and explicit TypeScript contracts:
  - `useDisclosure`: Common state machine for modals, dialogs, drawers, and popovers.
  - `useDebounce`: Debouncing rapidly updating values (e.g. search and filter inputs).
  - `useIsMounted`: Safe tracking of component mount lifecycle to guard asynchronous side effects.

### ADR-08: Feature-Based Module Architecture (`src/features/`)
- **Decision:** Organize future application features following the Vertical Slice Architecture pattern.
- **Module Structure:**
  ```text
  features/{feature-name}/
  ├── components/
  ├── hooks/
  ├── services/
  ├── types/
  └── index.ts
  ```
- **Boundary Rules:**
  - External modules must only import from the feature's public barrel file (`src/features/{feature-name}/index.ts`).
  - Circular dependencies between feature slices are strictly disallowed.
  - Shared domain models or utilities must be promoted to the central layer.

### ADR-09: TypeScript Type Organization (`src/types/`)
- **Decision:** Centralize ambient and cross-cutting structural types without declaring premature business entities.
- **Separation:**
  - `src/types/common.ts`: General utilities (`Nullable`, `Optional`, `AsyncState`, `PaginationParams`, `PaginatedResult`).
  - `src/types/api.ts`: HTTP protocols, envelope models, and error responses.
  - `src/types/index.ts`: Unified barrel file.

### ADR-10: Centralized Design Token Infrastructure & Design System Readiness (`src/styles/tokens/`)
- **Decision:** Establish a centralized, modular, CSS-first design token system in `src/styles/tokens/` bridging CSS custom properties to Tailwind CSS v4 via `@theme inline` and `@theme`.
- **Decoupled Architecture:**
  - Token modules for Brand, Surface, Text, Border, Typography, Spacing, Radius, Shadows, and Breakpoints.
  - Neutral OKLCH placeholders avoid premature visual identity decisions while accommodating future design specifications.
  - Symmetrical light (`:root`) and dark (`.dark`) theme support.
  - Full compatibility with Shadcn/ui and Radix UI headless primitives.
  - TypeScript token contracts and DOM runtime helpers (`getCssVar`, `setCssVar`).
- **Comprehensive Guide:** See [Design System Integration Guide](design-tokens-guide.md).

---

## 3. Verification & Compliance Matrix

| Requirement | Implementation | Verification Status |
| --- | --- | --- |
| Application entry & global providers | `src/main.tsx`, `src/app/provider.tsx`, `src/app/App.tsx` | Verified via SSR & Client DOM mounting |
| React Router integration | `src/app/routes.tsx`, `src/app/router.tsx` | Verified on `/` and `*` routes in automated test |
| Centralized Axios API client | `src/services/api/api-client.ts` | Verified default headers, timeout, token injection |
| Environment variable strategy | `src/config/env.ts`, `.env.example` | Verified validation, parsing, and fallbacks |
| Centralized app configuration | `src/config/constants.ts`, `src/config/index.ts` | Verified frozen appConfig and constants |
| Reusable component & hook conventions | `src/components/shared/*`, `src/hooks/*` | Verified interaction, timer, and error handling |
| TypeScript type organization | `src/types/*` | Verified with `tsc -b` strict typecheck |
| Feature-based module structure | `src/features/README.md` | Documented boundaries & conventions |
| API Error handling conventions | `src/services/api/api-error.ts` | Verified RFC 7807, network, and timeout mapping |
| Design token infrastructure | `src/styles/tokens/*`, `src/index.css` | Verified via automated token suite & Tailwind v4 build |
| Architectural documentation | `docs/frontend-architecture.md`, `docs/design-tokens-guide.md` | Completed and cross-referenced |
