import React from 'react';
import { RouteObject, Link } from 'react-router-dom';
import { LoginPage } from '../auth/LoginPage';
import { ForcePasswordChangePage } from '../auth/ForcePasswordChangePage';

const PublicPlaceholderPage: React.FC<{ title: string; description: string }> = ({ title, description }) => (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', backgroundColor: '#0F172A', color: '#F8FAFC' }}>
    <div className="glass-card" style={{ padding: 32, textAlign: 'center', maxWidth: 400 }}>
      <h2>{title}</h2>
      <p style={{ color: '#94A3B8', marginTop: 8, marginBottom: 16 }}>{description}</p>
      <Link to="/" style={{ color: '#38BDF8', textDecoration: 'none', fontSize: 13 }}>
        Return to Platform Home
      </Link>
    </div>
  </div>
);

export const publicRoutes: RouteObject[] = [
  {
    path: '/fleet/login',
    element: <LoginPage />,
  },
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/auth/force-password-change',
    element: <ForcePasswordChangePage />,
  },

  {
    path: '/unauthorized',
    element: <PublicPlaceholderPage title="403 Unauthorized Access" description="You do not have permission to access this resource." />,
  },
  {
    path: '/not-found',
    element: <PublicPlaceholderPage title="404 Page Not Found" description="The requested route does not exist." />,
  },
  {
    path: '*',
    element: <PublicPlaceholderPage title="404 Page Not Found" description="The requested route does not exist." />,
  },
];
