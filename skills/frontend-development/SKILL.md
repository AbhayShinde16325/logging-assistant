# SKILL: Frontend Development

> **DE (skill-steward):** Developer C · Applies to: `frontend/**` contributors.

## 1. Skill purpose

Build the React UI: chat with confirmation cards, tasks views (list/detail), dashboard, API service
layer, and state management — with honest loading/error/empty states and strict contract fidelity.

## 2. When the agent should use this skill

Any task touching `frontend/**` (components, pages, hooks, services, store, voice UI).

## 3. Relevant directories and files

- Code: `frontend/src/` (`components/`, `pages/`, `features/`, `hooks/`, `services/`, `store/`, `types/`, `utils/`)
- Contracts: `../contracts/README.md` mapping table + `../docs/api-contracts.md` (field names!)
- Root `AGENTS.md` + `frontend/AGENTS.md`
- Tests: `frontend/src/**` component tests (Vitest) + `../tests/contract/` when API shapes change

## 4. Technology-specific implementation rules

- **Server state = React Query** (`@tanstack/react-query`): one hook per endpoint family
  (`useChat`, `useTasks`, `useTask`, `useEmployees`, `useActivity`, `useReminders`, `useDashboardSummary`,
  `useConfirmAction`, `useRejectAction`); mutations invalidate precisely (`tasks` after confirm).
- **Ephemeral state = Zustand** (`store/`): selected `employee_id`, active `conversation_id`, nav
  state; persist `employee_id` with a light storage adapter.
- **Services**: a typed axios instance (`services/apiClient.ts`) reading `import.meta.env.VITE_API_BASE_URL`;
  one module per resource; every call typed with `types/` interfaces; interceptors unwrap the
  standardized error envelope and rethrow a typed `ApiError` so the UI renders `error.code/message`.
- **Chat feature**: messages appended (user + assistant), pending `proposed_actions` render as
  cards showing extracted fields (title, assignee, due date, priority) with **Confirm / Reject**
  buttons wired to the two endpoints; after a reply/render, scroll to newest; input disable states
  while requests are in flight.
- **Confirmation fidelity**: consequential actions are never auto-executed; optimistic UI only for
  harmless state (e.g. showing "sent") — never for task data.
- **Tasks UI**: list view w/ filters (assignee, status) and due-date sorting; rows link to a detail
  view; completion button issues PATCH with status `DONE`.
- **Voice**: Web Speech API (`webkitSpeechRecognition` where available) with feature detection;
  result text lands in the chat input for user review **before** sending; unsupported browsers get
  a friendly disabled state — never a fake transcription.
- **Vite proxy/dev mode**: enable a dev proxy or env-driven base URL so browser CORS works in dev
  (backend sets `CORS_ORIGINS`; frontend just uses `VITE_API_BASE_URL`).

## 5. Coding conventions

TypeScript strict mode; no `any` without justification; functional components; feature folders
own their widgets; components take typed props; Tailwind classes in JSX (no dead CSS files);
PascalCase files for components.

## 6. Dependencies and interfaces

- Stack locked by contract (root AGENTS.md §1): React, Vite, TS, Tailwind, Axios, React Query,
  Zustand. Adding UI libs (e.g. charts) requires a PR stating purpose and size impact.
- **Contract sync rule**: field/enum changes go hand-in-hand with backend + `contracts/` — never a
 customers-only rename; if types mismatch the build breaks.

## 7. Common mistakes to avoid

| Mistake | Correct |
|---|---|
| Duplicating enums/TS types in components | Single source in `types/` mirroring `contracts/` |
| Business logic in components | Derived values in `utils/`; server logic stays server-side |
| Optimistic task mutations | Confirm round-trips cause actual data; keep mutations explicit |
| Auto-sending voice text | Transcription is editable in input before send |
| Silent catch on errors | Always render envelope info; escalate `502/503` with retry affordance |
| Hardcoded employee names/IDs anywhere | Use the employees endpoint fetched by the store's selector |

## 8. Testing requirements

- Component tests with mocked services/fixtures (Vitest + `@testing-library/react` when wire-up
  starts); render states: loading/empty/error/list.
- **Contract-typing check**: one test asserts that fixture JSON from `contracts/` typechecks against
  `types/` — belt & braces for schema sync.
- CI gates: `npm run lint`, `npx tsc --noEmit`, `npm run build` (green before merge).

## 9. Completion checklist

- [ ] Loading/empty/error states for every new data view
- [ ] Confirmation UI cannot be bypassed for consequential actions
- [ ] Types synced with `contracts/` (validated by fixture type test)
- [ ] lint + typecheck + build green; component tests added
- [ ] No credentials/tokens in the bundle (only `VITE_API_BASE_URL`)
