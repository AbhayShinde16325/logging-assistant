/**
 * MessageList — one entry per chat turn; proposals render inside the assistant turn via
 * ProposedActionCard (explicit confirm/reject, never auto-fired per frontend/AGENTS.md).
 */

import { ProposedActionCard } from "./ProposedActionCard";
import type { ChatResponse } from "../../types";

export type ChatTurn =
  | { role: "user"; text: string }
  | { role: "assistant"; response: ChatResponse };

export function MessageList({ turns, sending }: { turns: ChatTurn[]; sending: boolean }) {
  return (
    <div className="flex flex-col gap-3" role="log" aria-label="Conversation">
      {turns.map((turn, i) =>
        turn.role === "user" ? (
          <div key={i} className="self-end max-w-[80%] rounded-md bg-blue-600 px-3 py-2 text-sm text-white">
            {turn.text}
          </div>
        ) : (
          <div key={i} className="self-start max-w-[85%] rounded-md bg-slate-100 px-3 py-2 text-sm">
            <p className="whitespace-pre-wrap text-slate-700">{turn.response.message || "…"}</p>
            {turn.response.proposed_actions.length > 0 ? (
              <div className="mt-2 flex flex-col gap-2">
                {turn.response.proposed_actions.map((action) => (
                  <ProposedActionCard key={action.action_id} action={action} />
                ))}
              </div>
            ) : null}
          </div>
        ),
      )}
      {sending ? <p className="self-start text-sm text-slate-400">Thinking…</p> : null}
    </div>
  );
}
