/**
 * axios instance + typed endpoint calls (assets: services layer — no business rules).
 * Talks EXCLUSIVELY to backend /api/v1 (frontend/AGENTS.md); VITE_API_BASE_URL overrides the
 * default for deployments.
 */

import axios, { AxiosError } from "axios";
import type {
  ActivityListResponse,
  ChatRequest,
  ChatResponse,
  ConfirmResponse,
  DashboardSummary,
  EmployeeListResponse,
  ErrorEnvelope,
  MeetingExtractRequest,
  MeetingExtractResponse,
  RejectResponse,
  Reminder,
  Task,
  TaskListResponse,
} from "../types";

export const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: { "Content-Type": "application/json" },
});

export function toErrorEnvelope(err: unknown): ErrorEnvelope {
  const axiosErr = err as AxiosError<ErrorEnvelope>;
  const body = axiosErr.response?.data;
  if (body?.error?.code) return body;
  return {
    error: {
      code: "NETWORK_ERROR",
      message: axiosErr.message ?? "The assistant backend is not reachable.",
      details: {},
    },
  };
}

// ---- chat + actions -----------------------------------------------------------------
export async function sendChat(body: ChatRequest): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>("/chat", body);
  return data;
}

export async function confirmAction(actionId: string): Promise<ConfirmResponse> {
  const { data } = await api.post<ConfirmResponse>(`/actions/${actionId}/confirm`);
  return data;
}

export async function rejectAction(actionId: string): Promise<RejectResponse> {
  const { data } = await api.post<RejectResponse>(`/actions/${actionId}/reject`);
  return data;
}

// ---- tasks ---------------------------------------------------------------------------
export async function listTasks(filters: {
  assignee_id?: string;
  status?: string;
  due_before?: string;
  due_after?: string;
}): Promise<TaskListResponse> {
  const { data } = await api.get<TaskListResponse>("/tasks", { params: filters });
  return data;
}

export async function updateTaskPatch(taskId: string, patch: Partial<Task>): Promise<Task> {
  const { data } = await api.patch<{ task: Task }>(`/tasks/${taskId}`, patch);
  return data.task;
}

export async function deleteTask(taskId: string): Promise<void> {
  await api.delete(`/tasks/${taskId}`);
}

// ---- employees / activity / dashboard --------------------------------------------------
export async function listEmployees(): Promise<EmployeeListResponse> {
  const { data } = await api.get<EmployeeListResponse>("/employees");
  return data;
}

export async function listActivity(params: { employee_id?: string }): Promise<ActivityListResponse> {
  const { data } = await api.get<ActivityListResponse>("/activity", { params });
  return data;
}

export async function getDashboard(): Promise<DashboardSummary> {
  const { data } = await api.get<DashboardSummary>("/dashboard/summary");
  return data;
}

// ---- reminders / meetings -------------------------------------------------------------
export async function listReminders(params: { employee_id?: string }): Promise<{ reminders: Reminder[] }> {
  const { data } = await api.get<{ reminders: Reminder[] }>("/reminders", { params });
  return data;
}

export async function extractMeeting(body: MeetingExtractRequest): Promise<MeetingExtractResponse> {
  const { data } = await api.post<MeetingExtractResponse>("/meetings/extract", body);
  return data;
}
