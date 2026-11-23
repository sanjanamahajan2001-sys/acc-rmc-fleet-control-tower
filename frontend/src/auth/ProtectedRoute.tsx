import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/auth';

export const ProtectedRoute: React.FC = () => {
  const token = useAuthStore((state) => state.token);
  const user = useAuthStore((state) => state.user);
  const location = useLocation();

  if (!token && typeof window !== 'undefined') {
    const devToken = localStorage.getItem('fct_auth_token') || localStorage.getItem('token');
    if (!devToken && process.env.NODE_ENV !== 'development') {
      return <Navigate to="/login" replace />;
    }
  }

  const isPasswordChangeStage = user?.auth_stage === 'PASSWORD_CHANGE_REQUIRED' || user?.must_change_password === true;
  const isForcePasswordRoute = location.pathname === '/auth/force-password-change';

  if (isPasswordChangeStage && !isForcePasswordRoute) {
    return <Navigate to="/auth/force-password-change" replace />;
  }

  return <Outlet />;
};

