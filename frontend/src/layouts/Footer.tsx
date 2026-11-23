import React from 'react';

export const Footer: React.FC = () => {
  return (
    <footer
      style={{
        height: 28,
        backgroundColor: '#0F172A',
        borderTop: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 16px',
        fontSize: 11,
        color: '#64748B',
      }}
    >
      <span>Fleet Control Tower Platform v1.0.0</span>
      <span>Enterprise Control Room Mode</span>
    </footer>
  );
};
