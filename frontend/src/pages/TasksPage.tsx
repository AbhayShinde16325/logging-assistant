/** TasksPage — task list with filters (assignee/status); quick complete/delete inline. */

import { useState } from "react";
import { TaskTableControlled } from "../features/tasks/TaskTable";
import type { TaskStatus } from "../types";
import { useEmployees, useTasks } from "../hooks/useTasks";

const STATUS_OPTIONS: TaskStatus[] = ["TODO", "IN_PROGRESS", "BLOCKED", "DONE", "CANCELLED"];

export function TasksPage() {
  const [assignee, setAssignee] = useState<string>("");
  const [status, setStatus] = useState<TaskStatus | "">("");
  const employees = useEmployees();
  const tasks = useTasks({
    assignee_id: assignee || undefined,
    status: status || undefined,
  });

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-3 text-sm">
        <label className="flex items-center gap-2 text-slate-500">
          Assignee
          <select
            value={assignee}
            onChange={(e) => setAssignee(e.target.value)}
            className="rounded border border-slate-300 px-2 py-1"
          >
            <option value="">All</option>
            {employees.data?.employees.map((emp) => (
              <option key={emp.employee_id} value={emp.employee_id}>
                {emp.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 text-slate-500">
          Status
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as TaskStatus | "")}
            className="rounded border border-slate-300 px-2 py-1"
          >
            <option value="">All</option>
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s.replace("_", " ")}
              </option>
            ))}
          </select>
        </label>
      </div>

      <TaskTableControlled
        tasks={tasks.data?.tasks ?? []}
        isLoading={tasks.isLoading}
        error={tasks.error ?? null}
        total={tasks.data?.total ?? 0}
      />
    </div>
  );
}
