# frontend/ — AGENTS.md

Owner: **Developer C**. Refines the root [`../AGENTS.md`](../AGENTS.md) without contradicting it.

## Module purpose

The only UI: chat with the assistant (text + voice capture), the confirm/reject interface, the task
list/detail views, and the dashboard. The frontend talks **exclusively** to the backend `/api/v1`
API and contains no business rules.

## Read before coding

1. Root [`../AGENTS.md`](../AGENTS.md)
2. [`../skills/frontend-development/SKILL.md`](../skills/frontend-development/SKILL.md)
3. [`../docs/api-contracts.md`](../docs/api-contracts.md) + [`../contracts/`](../contracts/) (types must mirror)
4. [`../docs/prototype-roadmap.md`](../docs/prototype-roadmap.md) (scope: what belongs in this milestone)

## Layout

```text
frontend/src/
├── components/   ← reusable UI atoms (Button, Badge, Modal, EmptyState, ErrorBanner…)
├── pages/        ← route-level views (ChatPage, TasksPage, DashboardPage)
├── features/     ← feature-composed widgets (chat/MessageList, chat/ProposedActionCard,
│                    tasks/TaskTable, dashboard/EmployeeCard)
├── hooks/        ← React Query hooks (useChat, useTasks, useDashboard) — all server state here
├── services/     ← axios instance (VITE_API_BASE_URL) + typed endpoint calls
├── store/        ← Zustand store: selected employee_id, conversation_id, UI prefs
├── types/        ← TypeScript mirrors of ../contracts/*.schema.json (single source: contracts/)
└── utils/        ← date formatting, tiny helpers — no API calls, no business rules
```

## Hard module rules

- **Contract fidelity**: field names/types match `../contracts/` exactly (see `../contracts/README.md`
  mapping); changing fields requires the coordinated contracts PR, never a frontend-only rename.
- Server state lives in React Query; ephemeral UI state in Zustand; no duplicate task models —
  always derive from `types/`.
- Errors: every request path renders the error envelope (`error.code/message`) in a user-readable
  banner/toast; loading/empty states are mandatory for list views.
- Employee identity: the selected `employee_id` (EMP-…) is sent with chat/activity requests;
  nothing is derived client-side beyond display.
- **Confirmation is explicit**: consequential proposed actions render a card with Confirm/Reject —
  they are never auto-fired, never batch-fired.
- No credentials in this app. Google/Sheets/Ollama are never reachable from the browser bundle.
- MVP voice = Web Speech API in-browser (Chrome); unsupported browsers get a graceful message
  (task T-110); do not import cloud STT SDKs.

## Conventions

- TypeScript strict; no `any` unless absolutely unavoidable (comment why).
- Functional components + hooks; PascalCase components, camelCase helpers, `use*` hooks.
- Tests: component tests with mocked services (fixtures from `../contracts/` examples where given).
- Quality gates: `npm run lint`, `npx tsc --noEmit`, `npm run build` must pass before PRs (CI runs them).
