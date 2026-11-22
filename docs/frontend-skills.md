# Frontend Development Skills Architecture & Catalog

## Overview

To empower AI developer agents (such as Google Antigravity / Gemini Coder, Claude Code, and Cursor) to produce idiomatic, performant, and type-safe frontend code, Task 05 establishes a verified suite of **Frontend Development Skills**.

These skills follow the open `SKILL.md` format and are located at `.agents/skills/`. They adhere to **progressive disclosure**, where agents only load the skill instructions when relevant to the current user prompt or task.

---

## 1. Environment & Discovery Architecture

### Agent Environment
- **Platform:** Google Antigravity / Gemini Coder (AGY 2.0).
- **Project Root:** `D:\Zango` (repository containing `.git`).
- **Frontend Root:** `D:\Zango\frontend`.
- **Customization Root:** `D:\Zango\.agents/`.

### Discovery Mechanism
1. **Hierarchical Project Discovery:** When an agent runs in `D:\Zango` or inside subdirectories like `frontend/src/`, it traverses up to the repository root and scans `.agents/skills/`.
2. **Explicit Manifest:** `.agents/skills.json` explicitly declares the skills entry directory (`.agents/skills`), ensuring deterministic discovery across diverse agent clients.
3. **Progressive Disclosure:** Each skill's YAML frontmatter (`name` and `description`) is indexed at startup. Detailed instructions and deep references (`references/rules.md`) are loaded on-demand.

---

## 2. Configured Skills Catalog

Seven dedicated skills were designed to map 1:1 to the required development categories without overlap or duplication:

| # | Skill Identifier | Category | Tech Stack Alignment | Source Baseline |
| --- | --- | --- | --- | --- |
| 1 | `react-best-practices` | React 19 Best Practices | React 19.3, functional components, action hooks (`useActionState`, `useOptimistic`), derived state over `useEffect`, clean unmount with `AbortController`. | [React 19 Official Docs](https://react.dev) & [Vercel Agent Skills](https://github.com/vercel-labs/agent-skills) |
| 2 | `typescript-best-practices` | TypeScript Standards | TypeScript 6.0, strict mode, `erasableSyntaxOnly`, `verbatimModuleSyntax`, discriminated unions, zero `any`. | [TypeScript Handbook](https://www.typescriptlang.org) & Total TypeScript |
| 3 | `tailwind-conventions` | Tailwind CSS Conventions | Tailwind CSS v4, `@theme` configuration, static class compilation, dynamic class avoidance, class merging via `cn()`. | [Tailwind CSS v4 Docs](https://tailwindcss.com) & Mintuz Web Skills |
| 4 | `shadcn-component-development` | UI Component Development | Shadcn UI 4.23, Radix UI primitives, `components.json`, `cva` variant management, accessible compound components. | [Shadcn UI Skills](https://ui.shadcn.com/docs/skills) & Radix UI Docs |
| 5 | `frontend-architecture-maintainability` | Architecture & Maintainability | Vertical Slice Architecture (`src/features/`), barrel exports (`index.ts`), centralized Axios client with RFC 7807 `ApiError`, environment isolation. | [Zango ADRs](frontend-architecture.md) & Bulletproof React |
| 6 | `accessibility-semantic-html` | Accessibility (a11y) & Semantics | WCAG 2.2 Level AA, semantic HTML5 tags, keyboard navigation, focus trap/restore, visible focus rings, ARIA roles. | [W3C WAI-ARIA APG](https://www.w3.org/WAI/ARIA/apg/) & ACCESSIBILITY.md |
| 7 | `frontend-performance-optimization` | Web Performance | Core Web Vitals (LCP $\le 2.5\text{s}$, INP $\le 200\text{ms}$, CLS $\le 0.1$), Vite code-splitting, lazy loading, render cycle minimization, list virtualization. | [Google Web Vitals](https://web.dev/vitals) & Addy Osmani Web Quality Skills |

---

## 3. Directory Layout

```text
.agents/
├── skills.json                           # Explicit skills registration manifest
├── README.md                             # Agent customizations guide
└── skills/
    ├── react-best-practices/
    │   ├── SKILL.md                      # Main instruction runbook
    │   └── references/rules.md           # Detailed rule reference and examples
    ├── typescript-best-practices/
    │   ├── SKILL.md
    │   └── references/rules.md
    ├── tailwind-conventions/
    │   ├── SKILL.md
    │   └── references/rules.md
    ├── shadcn-component-development/
    │   ├── SKILL.md
    │   └── references/rules.md
    ├── frontend-architecture-maintainability/
    │   ├── SKILL.md
    │   └── references/rules.md
    ├── accessibility-semantic-html/
    │   ├── SKILL.md
    │   └── references/rules.md
    └── frontend-performance-optimization/
        ├── SKILL.md
        └── references/rules.md
```

---

## 4. Verification & Discoverability Testing

All skills are verified using an automated script (`frontend/scripts/verify-skills.mjs`) that performs:
1. Manifest parsing of `.agents/skills.json`.
2. Discoverability verification of every skill in `.agents/skills/`.
3. Validation of YAML frontmatter (`name`, `description`).
4. Category coverage check (100% of required categories).
5. Cross-reference validation (ensuring all linked files in `references/` exist).
6. Security checks (verifying no unauthorized executables or unknown project dependencies were injected).
