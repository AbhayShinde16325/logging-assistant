# frontend/src — folder responsibilities

Implementation starts at Milestone 1 (`../tasks.md`, tasks T-040+). Until then each folder carries a
`.gitkeep`; one-line responsibility per folder (details: [`../AGENTS.md`](../AGENTS.md)):

| Folder | Responsibility |
|---|---|
| `components/` | Reusable presentational atoms (Button, Badge, Modal, EmptyState, ErrorBanner). |
| `pages/` | Route-level views: ChatPage, TasksPage, DashboardPage. |
| `features/` | Feature widgets composing components + hooks: chat (MessageList, proposed-action cards), tasks (table/detail), dashboard (cards). |
| `hooks/` | React Query hooks wrapping `services/` — all server state lives here. |
| `services/` | Axios instance (`VITE_API_BASE_URL`) + typed functions for each `/api/v1` endpoint. |
| `store/` | Zustand: selected `employee_id`, current `conversation_id`, UI prefs. |
| `types/` | TypeScript mirrors of `../../contracts/*.schema.json` — do not invent fields. |
| `utils/` | Formatting/helpers; no API calls, no business rules. |
