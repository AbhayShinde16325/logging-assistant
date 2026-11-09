/**
 * ProposedActionCard — explicit confirm/reject (frontend/AGENTS.md hard rule: consequential
 * actions are never auto-fired, never batch-fired; one card per action).
 */

import { useConfirmAction, useRejectAction } from "../../hooks/useChat";
import { BadgeForAction, Button } from "../../components/ui";
import { toErrorEnvelope } from "../../services/apiClient";
import type { ProposedAction } from "../../types";
import { useState } from "react";

const ACTION_LABELS: Record<ProposedAction["action_type"], string> = {
  CREATE_TASK: "Create task",
  UPDATE_TASK: "Update task",
  DELETE_TASK: "Delete task",
  COMPLETE_TASK: "Complete task",
  ASSIGN_TASK: "Assign task",
  CREATE_REMINDER: "Set reminder",
  QUERY: "Query",
};

export function ProposedActionCard({ action }: { action: ProposedAction }) {
  const confirm = useConfirmAction();
  const reject = useRejectAction();
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<"EXECUTED" | "REJECTED" | null>(action.status === "EXECUTED" ? "EXECUTED" : action.status === "REJECTED" ? "REJECTED" : null);

  const onConfirm = async () => {
    setError(null);
    try {
      await confirm.mutateAsync(action.action_id);
      setDone("EXECUTED");
    } catch (err) {
      setError(toErrorEnvelope(err).error.message);
    }
  };

  const onReject = async () => {
    setError(null);
    try {
      await reject.mutateAsync(action.action_id);
      setDone("REJECTED");
    } catch (err) {
      setError(toErrorEnvelope(err).error.message);
    }
  };

  const pending = action.status === "PENDING" && done === null;

  return (
    <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm">
      <div className="mb-1 flex items-center gap-2">
        <span className="font-semibold">{ACTION_LABELS[action.action_type]}</span>
        <BadgeForAction status={done ?? action.status} />
      </div>
      <ul className="mb-2 list-disc pl-4 text-slate-700">
        {Object.entries(action.payload)
          .filter(([, value]) => value !== null && value !== "")
          .map(([key, value]) => (
            <li key={key}>
              <span className="text-slate-500">{camelToLabel(key)}:</span> {String(value)}
            </li>
          ))}
      </ul>
      {error ? <p className="mb-2 text-xs text-red-600">{error}</p> : null}
      {pending ? (
        <div className="flex gap-2">
          <Button onClick={() => void onConfirm()} disabled={confirm.isPending}>
            {confirm.isPending ? "Confirming…" : "Confirm"}
          </Button>
          <Button variant="secondary" onClick={() => void onReject()} disabled={reject.isPending}>
            Reject
          </Button>
        </div>
      ) : (
        <p className="text-xs text-slate-500">
          {done === "EXECUTED" ? "Confirmed — the change is saved." : done === "REJECTED" ? "Rejected — nothing changed." : `Status: ${action.status}`}
        </p>
      )}
    </div>
  );
}

function camelToLabel(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
