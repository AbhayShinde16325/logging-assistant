/** EmployeeCard — per-person dashboard summary (open/overdue/completed_7d). */

import type { DashboardEmployeeSummary } from "../../types";

export function EmployeeCard({ summary }: { summary: DashboardEmployeeSummary }) {
  const { employee_id, name, open_tasks, overdue, completed_7d } = summary;
  return (
    <div className="rounded-md border border-slate-200 bg-white p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-semibold text-slate-800">{name}</span>
        <span className="font-mono text-xs text-slate-400">{employee_id}</span>
      </div>
      <dl className="grid grid-cols-3 gap-2 text-center text-sm">
        <div>
          <dt className="text-xs text-slate-400">Open</dt>
          <dd className="text-lg font-semibold text-slate-700">{open_tasks}</dd>
        </div>
        <div>
          <dt className="text-xs text-slate-400">Overdue</dt>
          <dd className={`text-lg font-semibold ${overdue > 0 ? "text-red-600" : "text-slate-700"}`}>
            {overdue}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-400">Done (7d)</dt>
          <dd className="text-lg font-semibold text-green-600">{completed_7d}</dd>
        </div>
      </dl>
    </div>
  );
}
