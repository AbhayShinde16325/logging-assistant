/** Reusable UI atoms (components/ per frontend/AGENTS.md). Includes the shared error banner. */

import type { ReactNode } from "react";
import type { ErrorEnvelope, ActionStatus, Priority, TaskStatus } from "../types";

export function Button({
  children,
  onClick,
  variant = "primary",
  disabled,
  type = "button",
  className = "",
  title,
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "primary" | "secondary" | "danger" | "ghost";
  disabled?: boolean;
  type?: "button" | "submit";
  className?: string;
  title?: string;
}) {
  const base =
    "px-3 py-1.5 rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed";
  const styles = {
    primary: "bg-blue-600 text-white hover:bg-blue-700",
    secondary: "bg-slate-200 text-slate-800 hover:bg-slate-300",
    danger: "bg-red-600 text-white hover:bg-red-700",
    ghost: "text-slate-600 hover:bg-slate-100",
  }[variant];
  return (
    <button type={type} onClick={onClick} disabled={disabled} title={title} className={`${base} ${styles} ${className}`}>
      {children}
    </button>
  );
}

export function Badge({ label, tone = "slate" }: { label: string; tone?: string }) {
  const cls = {
    slate: "bg-slate-200 text-slate-700",
    green: "bg-green-100 text-green-700",
    red: "bg-red-100 text-red-700",
    blue: "bg-blue-100 text-blue-700",
    amber: "bg-amber-100 text-amber-700",
  }[tone] ?? "bg-slate-200 text-slate-700";
  return <span className={`px-2 py-0.5 rounded text-xs font-semibold ${cls}`}>{label}</span>;
}

export function TaskStatusBadge({ status }: { status: TaskStatus }) {
  return <Badge label={status.replace("_", " ")} tone={status === "DONE" ? "green" : status === "BLOCKED" ? "red" : "slate"} />;
}

export function PriorityBadge({ priority }: { priority: Priority }) {
  const tone = priority === "HIGH" ? "red" : priority === "MEDIUM" ? "amber" : "slate";
  return <Badge label={priority} tone={tone} />;
}

export function BadgeForAction({ status }: { status: ActionStatus }) {
  const tone = status === "PENDING" ? "amber" : status === "EXECUTED" ? "green" : "slate";
  return <Badge label={status} tone={tone} />;
}

export function ErrorBanner({ error, onDismiss }: { error: ErrorEnvelope | null; onDismiss?: () => void }) {
  if (!error) return null;
  return (
    <div
      role="alert"
      className="mb-3 flex items-start justify-between gap-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
    >
      <div>
        <span className="font-semibold">{error.error.code}: </span>
        {error.error.message}
      </div>
      {onDismiss ? (
        <button type="button" onClick={onDismiss} aria-label="Dismiss error" className="text-red-500 hover:text-red-700">
          ×
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return <p className="py-8 text-center text-sm text-slate-400">{message}</p>;
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <p className="py-8 text-center text-sm text-slate-400" role="status" aria-live="polite">
      {label}
    </p>
  );
}
