/**
 * ChatPage — the primary surface: chat turns + explicit proposal confirm/reject.
 * Employee identity comes from the Zustand store (frontend/AGENTS.md hard rule).
 */

import { useEffect, useRef, useState } from "react";
import { ChatComposer } from "../features/chat/ChatComposer";
import { MessageList, type ChatTurn } from "../features/chat/MessageList";
import { ErrorBanner } from "../components/ui";
import { useEmployees } from "../hooks/useTasks";
import { useChat } from "../hooks/useChat";
import { toErrorEnvelope } from "../services/apiClient";
import { useUiStore } from "../store/uiStore";
import type { ChatResponse, ErrorEnvelope } from "../types";

export function ChatPage() {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [error, setError] = useState<ErrorEnvelope | null>(null);
  const chat = useChat();
  const employees = useEmployees();
  const { selectedEmployeeId, selectEmployee } = useUiStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, chat.isPending]);

  const send = (message: string) => {
    setError(null);
    setTurns((prev) => [...prev, { role: "user", text: message }]);
    chat.mutate(message, {
      onSuccess: (response: ChatResponse) => {
        setTurns((prev) => [...prev, { role: "assistant", response }]);
      },
      onError: (err) => setError(toErrorEnvelope(err)),
    });
  };

  const hasEmployees = (employees.data?.employees.length ?? 0) > 0;

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex flex-wrap items-center gap-2 text-sm">
        <label htmlFor="employee-select" className="text-slate-500">
          Acting as:
        </label>
        {employees.isLoading ? (
          <span className="text-slate-400">loading employees…</span>
        ) : hasEmployees ? (
          <select
            id="employee-select"
            value={selectedEmployeeId ?? ""}
            onChange={(e) => selectEmployee(e.target.value || null)}
            className="rounded border border-slate-300 px-2 py-1"
          >
            <option value="">— choose an employee —</option>
            {employees.data?.employees.map((emp) => (
              <option key={emp.employee_id} value={emp.employee_id}>
                {emp.name} ({emp.employee_id})
              </option>
            ))}
          </select>
        ) : (
          <span className="text-slate-400">No employees configured yet.</span>
        )}
        {employees.error ? <ErrorBanner error={employees.error} /> : null}
      </div>

      {error ? <ErrorBanner error={error} onDismiss={() => setError(null)} /> : null}

      <div className="flex-1 overflow-y-auto rounded-md border border-slate-200 bg-white p-4">
        {turns.length === 0 && !chat.isPending ?
          <p className="py-8 text-center text-sm text-slate-400">
            Say what you need — e.g. “I need to research competitors by Wednesday” — and I&apos;ll propose
            the task for your confirmation.
          </p>
        : null}
        <MessageList turns={turns} sending={chat.isPending} />
        <div ref={bottomRef} />
      </div>

      <div className="mt-3">
        <ChatComposer onSend={send} sending={chat.isPending} />
      </div>
    </div>
  );
}
