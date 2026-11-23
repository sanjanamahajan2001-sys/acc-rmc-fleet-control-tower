import React from 'react';

export interface CardProps {
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export const AppCard: React.FC<CardProps> = ({ children, className = '', style }) => (
  <div className={`glass-card ${className}`} style={{ padding: 16, ...style }}>
    {children}
  </div>
);

export const CardHeader: React.FC<{ title: React.ReactNode; subtitle?: React.ReactNode; action?: React.ReactNode }> = ({
  title,
  subtitle,
  action,
}) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
    <div>
      <h3 style={{ fontSize: 14, fontWeight: 600, color: '#F8FAFC' }}>{title}</h3>
      {subtitle && <p style={{ fontSize: 12, color: '#94A3B8', marginTop: 2 }}>{subtitle}</p>}
    </div>
    {action && <div>{action}</div>}
  </div>
);

export const CardBody: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ fontSize: 13, color: '#F8FAFC' }}>{children}</div>
);

export const CardFooter: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ marginTop: 12, paddingTop: 8, borderTop: '1px solid rgba(255,255,255,0.08)', fontSize: 12, color: '#94A3B8' }}>
    {children}
  </div>
);
