/** Server state for chat + action lifecycle (hooks/ per frontend/AGENTS.md). */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { confirmAction, rejectAction, sendChat, toErrorEnvelope } from "../services/apiClient";
import type { ChatRequest, ChatResponse, ErrorEnvelope } from "../types";
import { useUiStore } from "../store/uiStore";

export function useChat() {
  const queryClient = useQueryClient();
  const { selectedEmployeeId, conversationId, setConversation } = useUiStore();

  const mutation = useMutation<ChatResponse, ErrorEnvelope, string>({
    mutationFn: async (message: string) => {
      const body: ChatRequest = {
        message,
        employee_id: selectedEmployeeId ?? undefined,
        conversation_id: conversationId ?? undefined,
      };
      try {
        return await sendChat(body);
      } catch (err) {
        throw toErrorEnvelope(err); // rendered by onError paths / banner
      }
    },
    onSuccess: (data) => {
      if (data.conversation_id) setConversation(data.conversation_id);
      // proposals may mutate tasks/activity once confirmed; refresh server views
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
  return mutation;
}

export function useConfirmAction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (actionId: string) => confirmAction(actionId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      void queryClient.invalidateQueries({ queryKey: ["activity"] });
    },
  });
}

export function useRejectAction() {
  return useMutation({
    mutationFn: (actionId: string) => rejectAction(actionId),
  });
}
