import React from 'react';
import { Download } from 'lucide-react';
import { Button } from '../components/inputs/Button';

interface TopToolbarProps {
  leftSlot?: React.ReactNode;
  centerSlot?: React.ReactNode;
  rightSlot?: React.ReactNode;
  statusSlot?: React.ReactNode;
  actionsSlot?: React.ReactNode;
  onExport?: () => void;
}


export const TopToolbar: React.FC<TopToolbarProps> = ({
  leftSlot,
  centerSlot,
  rightSlot,
  statusSlot,
  actionsSlot,
  onExport,
}) => {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px 16px',
        backgroundColor: '#F8FAFC',
        borderBottom: '1px solid #E2E8F0',
        fontSize: 12,
        color: '#475569',
        gap: 16,
      }}
    >
      <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
        {leftSlot}
        {centerSlot}
      </div>
      <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
        {rightSlot}
        {statusSlot}
        {actionsSlot}
        {onExport && (
          <Button variant="secondary" onClick={onExport} icon={<Download size={14} />}>
            Export
          </Button>
        )}
      </div>
    </div>
  );
};
