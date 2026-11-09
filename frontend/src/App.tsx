/**
 * App shell — router-less navigation via the Zustand `page` state (MVP; Vite single page).
 */

import { ChatPage } from "./pages/ChatPage";
import { DashboardPage } from "./pages/DashboardPage";
import { TasksPage } from "./pages/TasksPage";
import { useUiStore, type Page } from "./store/uiStore";

const NAV: Array<{ id: Page; label: string }> = [
  { id: "chat", label: "Chat" },
  { id: "tasks", label: "Tasks" },
  { id: "dashboard", label: "Dashboard" },
];

export default function App() {
  const page = useUiStore((s) => s.page);
  const setPage = useUiStore((s) => s.setPage);
  const setConversation = useUiStore((s) => s.setConversation);
  const clearConversation = () => setConversation(null);

  return (
    <div className="flex h-screen flex-col bg-slate-50 text-slate-900">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-2">
        <h1 className="text-sm font-semibold">AI Project Management Agent</h1>
        <button
          type="button"
          onClick={clearConversation}
          className="text-xs text-slate-400 hover:text-slate-600"
          title="Start a fresh assistant conversation"
        >
          New conversation
        </button>
      </header>
      <nav className="flex gap-1 border-b border-slate-200 bg-white px-4">
        {NAV.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setPage(item.id)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm ${
              page === item.id
                ? "border-blue-600 font-semibold text-blue-700"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {item.label}
          </button>
        ))}
      </nav>
      <main className="mx-auto w-full max-w-4xl flex-1 overflow-y-auto p-4">
        {page === "chat" ? <ChatPage /> : page === "tasks" ? <TasksPage /> : <DashboardPage />}
      </main>
    </div>
  );
}
