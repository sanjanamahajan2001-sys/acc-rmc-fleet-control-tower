import React from 'react';
import { QueryProvider } from '../providers/QueryProvider';
import { ThemeProvider } from '../theme/provider';
import { NotificationProvider } from '../providers/NotificationProvider';
import { AuthProvider } from '../auth/AuthProvider';
import { ErrorBoundary } from '../providers/ErrorBoundary';

export const AppProviders: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <QueryProvider>
          <AuthProvider>
            <NotificationProvider>{children}</NotificationProvider>
          </AuthProvider>
        </QueryProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
};
