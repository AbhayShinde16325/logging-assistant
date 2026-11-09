/** Ephemeral UI state (frontend/AGENTS.md): employee identity, conversation continuity, page. */

import { create } from "zustand";

export type Page = "chat" | "tasks" | "dashboard";

interface UiStore {
  page: Page;
  selectedEmployeeId: string | null;
  conversationId: string | null;
  setPage: (page: Page) => void;
  selectEmployee: (employeeId: string | null) => void;
  setConversation: (conversationId: string | null) => void;
}

export const useUiStore = create<UiStore>((set) => ({
  page: "chat",
  selectedEmployeeId: null,
  conversationId: null,
  setPage: (page) => set({ page }),
  selectEmployee: (selectedEmployeeId) => set({ selectedEmployeeId }),
  setConversation: (conversationId) => set({ conversationId }),
}));
