import React from 'react';

export interface StatusChipProps {
  label: string;
  status?: 'success' | 'warning' | 'danger' | 'info' | 'muted';
}

export const StatusChip: React.FC<StatusChipProps> = ({ label, status = 'info' }) => {
  const getColors = () => {
    switch (status) {
      case 'success':
        return { bg: 'rgba(16, 185, 129, 0.15)', text: '#10B981', border: '#10B981' };
      case 'warning':
        return { bg: 'rgba(245, 158, 11, 0.15)', text: '#F59E0B', border: '#F59E0B' };
      case 'danger':
        return { bg: 'rgba(239, 68, 68, 0.15)', text: '#EF4444', border: '#EF4444' };
      case 'muted':
        return { bg: 'rgba(100, 116, 139, 0.15)', text: '#64748B', border: '#64748B' };
      default:
        return { bg: 'rgba(56, 189, 248, 0.15)', text: '#38BDF8', border: '#38BDF8' };
    }
  };

  const colors = getColors();

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '2px 8px',
        borderRadius: 12,
        fontSize: 11,
        fontWeight: 600,
        backgroundColor: colors.bg,
        color: colors.text,
        border: `1px solid ${colors.border}`,
        letterSpacing: 0.5,
      }}
    >
      {label}
    </span>
  );
};
