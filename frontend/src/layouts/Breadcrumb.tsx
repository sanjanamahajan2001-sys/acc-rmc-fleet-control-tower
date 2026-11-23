import React from 'react';
import { useLocation } from 'react-router-dom';

export const Breadcrumb: React.FC = () => {
  const location = useLocation();
  const pathnames = location.pathname.split('/').filter((x) => x);

  return (
    <nav style={{ display: 'flex', gap: 8, fontSize: 12, color: '#94A3B8', marginBottom: 12 }}>
      <span>Platform</span>
      {pathnames.map((name, index) => {
        const routeTo = '/${pathnames.slice(0, index + 1).join('/')}';
        const isLast = index === pathnames.length - 1;
        return (
          <React.Fragment key={routeTo}>
            <span>/</span>
            <span style={{ color: isLast ? '#F8FAFC' : '#94A3B8', textTransform: 'capitalize' }}>
              {name.replace('-', ' ')}
            </span>
          </React.Fragment>
        );
      })}
    </nav>
  );
};
