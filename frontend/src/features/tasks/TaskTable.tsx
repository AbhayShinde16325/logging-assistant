/** TaskTable — list view with mandatory loading/empty/error states and quick status actions. */

import { Button, EmptyState, ErrorBanner, PriorityBadge, Spinner, TaskStatusBadge } from "../../components/ui";
import { useDeleteTask, useUpdateTask } from "../../hooks/useTasks";
import type { ErrorEnvelope, Task, TaskStatus } from "../../types";

const OPEN_STATUSES: TaskStatus[] = ["TODO", "IN_PROGRESS", "BLOCKED"];

function formatDue(due: string | null, status: TaskStatus): { text: string; overdue: boolean } {
  if (!due) return { text: "—", overdue: false };
  const overdue = new Date(due) < new Date() && OPEN_STATUSES.includes(status);
  return { text: due, overdue };
}

export function TaskTableControlled({
  tasks,
  isLoading,
  error,
  total,
}: {
  tasks: Task[];
  isLoading: boolean;
  error: ErrorEnvelope | null;
  total: number;
}) {
  const update = useUpdateTask();
  const remove = useDeleteTask();

  if (isLoading) return <Spinner label="Loading tasks…" />;
  if (error) return <ErrorBanner error={error} />;
  if (tasks.length === 0) return <EmptyState message="No tasks found. Create one via chat!" />;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-slate-200 text-xs uppercase text-slate-400">
          <tr>
            <th className="px-3 py-2">Task</th>
            <th className="px-3 py-2">Assignee</th>
            <th className="px-3 py-2">Status</th>
            <th className="px-3 py-2">Priority</th>
            <th className="px-3 py-2">Due</th>
            <th className="px-3 py-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((task) => {
            const due = formatDue(task.due_date, task.status);
            return (
              <tr key={task.task_id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="px-3 py-2">
                  <span className="font-medium text-slate-800">{task.title}</span>
                  <span className="block font-mono text-xs text-slate-400">{task.task_id}</span>
                </td>
                <td className="px-3 py-2 text-slate-600">{task.assignee_id}</td>
                <td className="px-3 py-2"><TaskStatusBadge status={task.status} /></td>
                <td className="px-3 py-2"><PriorityBadge priority={task.priority} /></td>
                <td className={`px-3 py-2 ${due.overdue ? "font-semibold text-red-600" : "text-slate-600"}`}>
                  {due.text}
                </td>
                <td className="px-3 py-2">
                  <div className="flex gap-1">
                    {OPEN_STATUSES.includes(task.status) ? (
                      <Button
                        variant="ghost"
                        disabled={update.isPending}
                        onClick={() => update.mutate({ taskId: task.task_id, patch: { status: "DONE" } })}
                        title="Mark done"
                      >
                        ✓
                      </Button>
                    ) : null}
                    <Button
                      variant="ghost"
                      disabled={remove.isPending}
                      onClick={() => remove.mutate(task.task_id)}
                      title="Delete"
                    >
                      🗑
                    </Button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="px-3 py-2 text-xs text-slate-400">{total} task(s) total</p>
    </div>
  );
}
