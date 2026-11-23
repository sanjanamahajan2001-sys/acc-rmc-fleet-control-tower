import React, { createContext, useContext } from 'react';
import { useAuthStore } from '../store/auth';
import { UserClaims } from '../types/auth';

interface AuthContextType {
  token: string | null;
  user: UserClaims | null;
  isAuthenticated: boolean;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { token, user, clearAuth } = useAuthStore();

  const logout = () => {
    clearAuth();
  };

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        isAuthenticated: Boolean(token),
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
