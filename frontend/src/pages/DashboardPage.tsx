/** DashboardPage — team summary grid + per-employee cards. */

import { EmployeeCard } from "../features/dashboard/EmployeeCard";
import { EmptyState, ErrorBanner, Spinner } from "../components/ui";
import { useDashboard } from "../hooks/useTasks";

export function DashboardPage() {
  const dashboard = useDashboard();

  if (dashboard.isLoading) return <Spinner label="Loading dashboard…" />;
  if (dashboard.error) return <ErrorBanner error={dashboard.error} />;
  if (!dashboard.data) return <EmptyState message="No dashboard data yet." />;

  const { team, employees } = dashboard.data;

  return (
    <div>
      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Open tasks" value={team.total_open} />
        <StatTile label="Due this week" value={team.due_this_week} />
        <StatTile label="Overdue" value={team.overdue} tone={typeof team.overdue === "number" && team.overdue > 0 ? "red" : undefined} />
        <StatTile label="Completed (7d)" value={team.completed_7d} tone="green" />
      </div>

      <h2 className="mb-2 text-sm font-semibold uppercase text-slate-400">By employee</h2>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {employees.map((summary) => (
          <EmployeeCard key={summary.employee_id} summary={summary} />
        ))}
      </div>
    </div>
  );
}

function StatTile({
  label,
  value,
  tone,
}: {
  label: string;
  value: number | undefined;
  tone?: "red" | "green";
}) {
  const num = typeof value === "number" ? value : "—";
  const color = tone === "red" ? "text-red-600" : tone === "green" ? "text-green-600" : "text-slate-800";
  return (
    <div className="rounded-md border border-slate-200 bg-white p-4">
      <p className="text-xs uppercase text-slate-400">{label}</p>
      <p className={`text-2xl font-semibold ${color}`}>{num}</p>
    </div>
  );
}
