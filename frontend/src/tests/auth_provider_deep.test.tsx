import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { useAuth } from '../auth/AuthProvider';
import { AuthProvider } from '../auth/AuthProvider';

const UserConsumerComponent = () => {
  const { user } = useAuth();
  return <div>User: {user ? user.sub : 'None'}</div>;
};

describe('AuthProvider Deep Coverage', () => {
  it('throws error when useAuth is used outside AuthProvider', () => {
    expect(() => render(<UserConsumerComponent />)).toThrow('useAuth must be used within an AuthProvider');
  });

  it('renders child components cleanly with user state', () => {
    render(
      <AuthProvider>
        <UserConsumerComponent />
      </AuthProvider>
    );
    expect(screen.getByText(/User: None/i)).toBeInTheDocument();
  });
});
