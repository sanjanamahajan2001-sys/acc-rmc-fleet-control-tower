import { create } from 'zustand';
import { env } from '../config/env';
import { APP_CONSTANTS } from '../config/constants';
import { UserClaims } from '../types/auth';

const USER_STORAGE_KEY = 'fct_auth_user';

const getInitialUser = (): UserClaims | null => {
  try {
    const raw = localStorage.getItem(USER_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

const getInitialToken = (): string | null => {
  return (
    localStorage.getItem(APP_CONSTANTS.STORAGE_KEYS.AUTH_TOKEN) ||
    localStorage.getItem('token') ||
    null
  );
};

interface AuthState {
  token: string | null;
  user: UserClaims | null;
  isLoading: boolean;
  setAuth: (token: string, user: UserClaims) => void;
  setUser: (user: UserClaims) => void;
  clearAuth: () => void;
  fetchCurrentUser: () => Promise<UserClaims | null>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: getInitialToken(),
  user: getInitialUser(),
  isLoading: false,

  setAuth: (token: string, user: UserClaims) => {
    localStorage.setItem(APP_CONSTANTS.STORAGE_KEYS.AUTH_TOKEN, token);
    localStorage.setItem('token', token);
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
    set({ token, user });
  },

  setUser: (user: UserClaims) => {
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
    set({ user });
  },

  clearAuth: () => {
    localStorage.removeItem(APP_CONSTANTS.STORAGE_KEYS.AUTH_TOKEN);
    localStorage.removeItem('token');
    localStorage.removeItem(USER_STORAGE_KEY);
    set({ token: null, user: null });
  },

  fetchCurrentUser: async () => {
    const token = get().token;
    if (!token) return null;
    try {
      set({ isLoading: true });
      const resp = await fetch(`${env.VITE_API_BASE_URL}/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!resp.ok) {
        if (resp.status === 401) {
          get().clearAuth();
        }
        return null;
      }
      const data = await resp.json();
      if (data.success && data.data) {
        const u = data.data;
        get().setUser(u);
        return u;
      }
      return null;
    } catch {
      return null;
    } finally {
      set({ isLoading: false });
    }
  },
}));
