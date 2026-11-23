import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorBoundary } from '../providers/ErrorBoundary';
import { NotificationProvider, useNotification } from '../providers/NotificationProvider';
import { ThemeProvider, useTheme } from '../theme/provider';
import { useAppStore } from '../store/app';
import { useAuthStore } from '../store/auth';

const ProblemChild = () => {
  throw new Error('Test boundary crash');
};

const TestNotificationComponent = () => {
  const { showNotification } = useNotification();
  return <button onClick={() => showNotification('Test toast', 'success')}>Trigger Toast</button>;
};

const TestThemeComponent = () => {
  const { mode, toggleTheme } = useTheme();
  return <button onClick={toggleTheme}>Mode: {mode}</button>;
};

describe('Framework Providers & Hooks Coverage', () => {
  it('renders ErrorBoundary fallback on component throw', () => {
    render(
      <ErrorBoundary>
        <ProblemChild />
      </ErrorBoundary>
    );
    expect(screen.getByText(/System Operational Fault/i)).toBeInTheDocument();
  });

  it('triggers toast notifications cleanly', () => {
    render(
      <NotificationProvider>
        <TestNotificationComponent />
      </NotificationProvider>
    );
    fireEvent.click(screen.getByText(/Trigger Toast/i));
    expect(screen.getByText(/Test toast/i)).toBeInTheDocument();
  });

  it('toggles theme state between dark and light', () => {
    render(
      <ThemeProvider>
        <TestThemeComponent />
      </ThemeProvider>
    );
    const btn = screen.getByText(/Mode: dark/i);
    fireEvent.click(btn);
    expect(screen.getByText(/Mode: light/i)).toBeInTheDocument();
  });

  it('updates Zustand AppStore sidebar state', () => {
    useAppStore.getState().setSidebarCollapsed(true);
    expect(useAppStore.getState().isSidebarCollapsed).toBe(true);
    useAppStore.getState().toggleSidebar();
    expect(useAppStore.getState().isSidebarCollapsed).toBe(false);
  });

  it('manages Zustand AuthStore session state', () => {
    useAuthStore.getState().setAuth('token_xyz', {
      sub: 'u2',
      jti: 'j2',
      type: 'access',
      exp: 100,
      iat: 50,
    });
    expect(useAuthStore.getState().token).toBe('token_xyz');
    useAuthStore.getState().clearAuth();
    expect(useAuthStore.getState().token).toBeNull();
  });
});
