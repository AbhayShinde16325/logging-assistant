/**
 * TypeScript mirrors of ../contracts/*.schema.json (frontend/AGENTS.md: single source is
 * contracts/). Field names and enums must match exactly — changing a field requires the
 * coordinated contracts PR (JSON Schema + Pydantic + TypeScript together).
 */

// ---- task.schema.json ------------------------------------------------------------
export type TaskStatus = "TODO" | "IN_PROGRESS" | "BLOCKED" | "DONE" | "CANCELLED";
export type Priority = "LOW" | "MEDIUM" | "HIGH";
export type RecordSource = "CHAT" | "VOICE" | "MEETING" | "MANUAL_SHEET" | "API";

export interface Task {
  task_id: string;
  title: string;
  description: string | null;
  assignee_id: string;
  created_by: string;
  status: TaskStatus;
  priority: Priority;
  due_date: string | null; // YYYY-MM-DD
  created_at: string; // ISO 8601 UTC
  updated_at: string;
  source: RecordSource;
  external_reference: string | null;
}

export interface Employee {
  employee_id: string;
  name: string;
  email: string;
  role: string;
  created_at: string;
}

// ---- agent-action.schema.json ------------------------------------------------------
export type ActionType =
  | "CREATE_TASK"
  | "UPDATE_TASK"
  | "DELETE_TASK"
  | "COMPLETE_TASK"
  | "ASSIGN_TASK"
  | "CREATE_REMINDER"
  | "QUERY";
export type ActionStatus = "PENDING" | "EXECUTED" | "REJECTED" | "EXPIRED";

export interface ProposedAction {
  action_id: string;
  conversation_id?: string;
  action_type: ActionType;
  payload: Record<string, string | null>;
  status: ActionStatus;
}

// ---- chat-request / chat-response ----------------------------------------------------
export interface ChatRequest {
  message: string;
  employee_id?: string | null;
  conversation_id?: string | null;
}

export interface TaskListResult {
  kind?: "TASKS";
  tasks?: Task[];
  [key: string]: unknown; // contract allows extra inline-result keys (generic branch)
}

export interface ChatResponse {
  conversation_id: string;
  message: string;
  requires_confirmation: boolean;
  proposed_actions: ProposedAction[];
  result?: TaskListResult | null;
}

export interface ConfirmResponse {
  status: "EXECUTED";
  action_id: string;
  result: { task?: Task; reminder?: Reminder } | null;
}

export interface RejectResponse {
  status: "REJECTED";
  action_id: string;
}

// ---- Activity_Log -------------------------------------------------------------------
export type ActivityType =
  | "TASK_CREATED"
  | "TASK_UPDATED"
  | "TASK_DELETED"
  | "TASK_COMPLETED"
  | "REMINDER_SET"
  | "REMINDER_SENT"
  | "MEETING_EXTRACTED"
  | "MANUAL_SHEET_EDIT"
  | "NOTE_SUBMITTED";

export interface ActivityEntry {
  activity_id: string;
  employee_id: string;
  task_id: string | null;
  activity_type: ActivityType;
  description: string;
  timestamp: string;
  source: RecordSource;
}

export interface ActivityListResponse {
  activity: ActivityEntry[];
  total: number;
}

// ---- Reminders ---------------------------------------------------------------------
export type ReminderStatus = "SCHEDULED" | "DUE" | "SENT" | "CANCELLED";

export interface Reminder {
  reminder_id: string;
  task_id: string;
  employee_id: string;
  scheduled_at: string;
  status: ReminderStatus;
  created_at: string;
}

// ---- Dashboard ---------------------------------------------------------------------
export interface DashboardEmployeeSummary {
  employee_id: string;
  name: string;
  open_tasks: number;
  overdue: number;
  completed_7d: number;
}

export interface DashboardSummary {
  team: {
    [key: string]: unknown;
    total_open?: number;
    due_this_week?: number;
    overdue?: number;
    completed_7d?: number;
    by_status?: Record<TaskStatus, number>;
  };
  employees: DashboardEmployeeSummary[];
}

// ---- Meetings -----------------------------------------------------------------------
export interface MeetingExtractRequest {
  title?: string | null;
  employee_id: string;
  text: string;
  date?: string | null;
}

export interface MeetingExtractResponse {
  summary: string | null;
  proposed_actions: ProposedAction[];
  requires_confirmation: boolean;
  decisions: string[];
  items: string[];
}

// ---- Health -------------------------------------------------------------------------
export interface HealthResponse {
  status: string;
  version: string;
  components: Record<string, string>;
}

// ---- Shared error envelope (root AGENTS.md §3) ----------------------------------------
export interface ErrorEnvelope {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

export interface TaskListResponse {
  tasks: Task[];
  total: number;
}

export interface EmployeeListResponse {
  employees: Employee[];
}
