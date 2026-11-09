/** Server state hooks for tasks / employees / dashboard / activity. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  deleteTask,
  getDashboard,
  listActivity,
  listEmployees,
  listTasks,
  toErrorEnvelope,
  updateTaskPatch,
} from "../services/apiClient";
import type { Task, TaskListResponse, EmployeeListResponse, DashboardSummary, ActivityListResponse, ErrorEnvelope } from "../types";

export function useTasks(filters: { assignee_id?: string; status?: string }) {
  return useQuery<TaskListResponse, ErrorEnvelope>({
    queryKey: ["tasks", filters],
    queryFn: async () => {
      try {
        return await listTasks(filters);
      } catch (err) {
        throw toErrorEnvelope(err);
      }
    },
  });
}

export function useEmployees() {
  return useQuery<EmployeeListResponse, ErrorEnvelope>({
    queryKey: ["employees"],
    queryFn: async () => {
      try {
        return await listEmployees();
      } catch (err) {
        throw toErrorEnvelope(err);
      }
    },
    staleTime: 5 * 60_000,
  });
}

export function useDashboard() {
  return useQuery<DashboardSummary, ErrorEnvelope>({
    queryKey: ["dashboard"],
    queryFn: async () => {
      try {
        return await getDashboard();
      } catch (err) {
        throw toErrorEnvelope(err);
      }
    },
  });
}

export function useActivity(params: { employee_id?: string }) {
  return useQuery<ActivityListResponse, ErrorEnvelope>({
    queryKey: ["activity", params],
    queryFn: async () => {
      try {
        return await listActivity(params);
      } catch (err) {
        throw toErrorEnvelope(err);
      }
    },
  });
}

export function useUpdateTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, patch }: { taskId: string; patch: Partial<Task> }) =>
      updateTaskPatch(taskId, patch),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useDeleteTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (taskId: string) => deleteTask(taskId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
