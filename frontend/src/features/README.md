# Feature-Based Architecture Guidelines

This directory houses application feature modules following the **Vertical Slice Architecture** convention.

## Directory Layout Convention

When introducing new business domains, structure each feature under `src/features/{feature-name}/` according to the following convention:

```text
src/features/{feature-name}/
├── components/          # Feature-scoped UI components (not intended for cross-feature use)
├── hooks/               # Feature-scoped React hooks
├── services/            # Feature-scoped API client calls, queries, and mutations
├── types/               # Feature-specific TypeScript interfaces and types
└── index.ts             # Public API / barrel export of the feature module
```

## Architectural Boundaries & Rules

1. **Explicit Public Interface (`index.ts`)**:
   - External code (other features, `app/`, etc.) must **only** import from `src/features/{feature-name}` (the barrel file).
   - Internal implementation details (sub-components, internal helpers) stay unexported from `index.ts`.

2. **No Circular Feature Dependencies**:
   - Feature A must not import from Feature B if Feature B imports from Feature A.
   - If two features share logic, promote the shared primitive to `src/components/shared`, `src/hooks`, `src/services`, `src/types`, or `src/lib`.

3. **Global vs. Feature Scope**:
   - `src/components/ui/`: Headless design-system primitives (e.g. Radix + Shadcn).
   - `src/components/shared/`: Domain-agnostic reusable components (e.g. error boundary, loading spinner).
   - `src/features/{feature}/components/`: Domain-specific components bound to feature workflows.

4. **Self-Containment**:
   - Each feature encapsulates its own API requests, caching strategies, validation schemas, and view models.
