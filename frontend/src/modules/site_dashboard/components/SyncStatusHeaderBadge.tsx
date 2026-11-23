import React from 'react';
import { useDashboardSync } from '../orchestration/DashboardSyncProvider';
import {
  IconDatasetDatabase,
  IconUserGroup,
  IconSyncRefresh,
} from '../../../components/icons/LinealColorIcons';

export const SyncStatusHeaderBadge: React.FC = () => {
  const { syncStatus, triggerManualRefresh, isRefreshing } = useDashboardSync();

  const status = syncStatus?.sync_status || 'SYNCHRONIZED';
  const operators = syncStatus?.active_operators_count || 1;
  const snapshot = syncStatus?.snapshot_version || 'v2.11-LIVE';

  let badgeStyle = { backgroundColor: '#ECFDF5', borderColor: '#A7F3D0', color: '#047857' };
  let dotColor = '#059669';
  let statusText = 'SYNCHRONIZED';

  if (isRefreshing || status === 'REFRESHING') {
    badgeStyle = { backgroundColor: '#ECFEFF', borderColor: '#A5F3FC', color: '#0891B2' };
    dotColor = '#06B6D4';
    statusText = 'REFRESHING';
  } else if (status === 'LAGGING') {
    badgeStyle = { backgroundColor: '#FEF3C7', borderColor: '#FCD34D', color: '#B7791F' };
    dotColor = '#D97706';
    statusText = 'LAGGING';
  } else if (status === 'DISCONNECTED') {
    badgeStyle = { backgroundColor: '#FEF2F2', borderColor: '#FCA5A5', color: '#C83B4B' };
    dotColor = '#E11D48';
    statusText = 'DISCONNECTED';
  }

  return (
    <div className="flex items-center space-x-2 text-xs">
      {/* Live Status Badge */}
      <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-md border font-semibold text-[11px] uppercase tracking-wider" style={badgeStyle}>
        <span className={`w-2 h-2 rounded-full ${isRefreshing ? 'animate-ping' : ''}`} style={{ backgroundColor: dotColor }} />
        <span>{statusText}</span>
      </div>

      {/* Snapshot Version */}
      <div className="hidden md:flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-slate-50 border border-slate-200 text-xs font-medium text-slate-700">
        <IconDatasetDatabase className="w-4 h-4" />
        <span className="text-slate-500">Snapshot:</span>
        <span className="font-mono font-semibold text-slate-800">{snapshot}</span>
      </div>

      {/* Active Operators Count */}
      <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-blue-50/80 border border-blue-200/80 text-xs font-medium text-blue-900">
        <IconUserGroup className="w-4 h-4" />
        <span className="font-semibold">{operators} {operators === 1 ? 'Operator' : 'Operators'}</span>
      </div>

      {/* Manual Refresh Trigger Button */}
      <button
        onClick={triggerManualRefresh}
        disabled={isRefreshing}
        title="Trigger Dashboard Refresh"
        className="p-1.5 rounded-md bg-slate-50 border border-slate-200 text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
      >
        <IconSyncRefresh className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
      </button>
    </div>
  );
};
