import { create } from 'zustand';
import { APP_CONSTANTS } from '../config/constants';

interface AppState {
  isSidebarCollapsed: boolean;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  isSidebarCollapsed: localStorage.getItem(APP_CONSTANTS.STORAGE_KEYS.SIDEBAR_COLLAPSED) === 'true',
  toggleSidebar: () =>
    set((state) => {
      const next = !state.isSidebarCollapsed;
      localStorage.setItem(APP_CONSTANTS.STORAGE_KEYS.SIDEBAR_COLLAPSED, String(next));
      return { isSidebarCollapsed: next };
    }),
  setSidebarCollapsed: (collapsed: boolean) => {
    localStorage.setItem(APP_CONSTANTS.STORAGE_KEYS.SIDEBAR_COLLAPSED, String(collapsed));
    set({ isSidebarCollapsed: collapsed });
  },
}));
