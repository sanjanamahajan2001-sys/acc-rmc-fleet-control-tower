import { env } from '../../../config/env';
import React, { createContext, useContext, useEffect, useState, useRef } from 'react';

export interface SyncStatusData {
  sync_status: 'SYNCHRONIZED' | 'REFRESHING' | 'LAGGING' | 'DISCONNECTED';
  last_sync_timestamp: string;
  snapshot_version: string;
  pending_events_count: number;
  active_operators_count: number;
  e_tag: string;
}

interface DashboardSyncContextType {
  syncStatus: SyncStatusData | null;
  triggerManualRefresh: () => Promise<void>;
  isRefreshing: boolean;
}

const DashboardSyncContext = createContext<DashboardSyncContextType>({
  syncStatus: null,
  triggerManualRefresh: async () => {},
  isRefreshing: false,
});

export const useDashboardSync = () => useContext(DashboardSyncContext);

interface DashboardSyncProviderProps {
  children: React.ReactNode;
  onRefreshNeeded: () => void;
}

export const DashboardSyncProvider: React.FC<DashboardSyncProviderProps> = ({ children, onRefreshNeeded }) => {
  const [syncStatus, setSyncStatus] = useState<SyncStatusData | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // 300ms Debounced Refresh Function
  const triggerDebouncedRefresh = () => {
    setIsRefreshing(true);
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    debounceTimerRef.current = setTimeout(() => {
      onRefreshNeeded();
      fetchSyncStatus();
      setTimeout(() => setIsRefreshing(false), 300);
    }, 300);
  };

  const fetchSyncStatus = async () => {
    try {
      const res = await fetch(env.VITE_API_BASE_URL + '/site-dashboard/sync/status');
      const data = await res.json();
      if (data.success && data.data) {
        setSyncStatus(data.data);
      }
    } catch (e) {
      setSyncStatus((prev) =>
        prev ? { ...prev, sync_status: 'DISCONNECTED' } : null
      );
    }
  };

  const triggerManualRefresh = async () => {
    setIsRefreshing(true);
    try {
      await fetch(env.VITE_API_BASE_URL + '/site-dashboard/sync/refresh', { method: 'POST' });
      triggerDebouncedRefresh();
    } catch (e) {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchSyncStatus();

    // 1. Setup Server-Sent Events (SSE) stream
    let eventSource: EventSource | null = null;

    try {
      eventSource = new EventSource(env.VITE_API_BASE_URL + '/site-dashboard/sync/events');

      eventSource.addEventListener('sync_event', (e: MessageEvent) => {
        try {
          const evt = JSON.parse(e.data);
          const type = evt.event_type;

          if (
            type === 'ERP_IMPORT_COMPLETED' ||
            type === 'ERP_RESET_COMPLETED' ||
            type === 'SNAPSHOT_INVALIDATED' ||
            type === 'SNAPSHOT_REGENERATED'
          ) {
            triggerDebouncedRefresh();
          }
        } catch (err) {
          // Ignore parse errors
        }
      });

      eventSource.onerror = () => {
        setSyncStatus((prev) =>
          prev ? { ...prev, sync_status: 'DISCONNECTED' } : null
        );
      };
    } catch (e) {
      setSyncStatus((prev) =>
        prev ? { ...prev, sync_status: 'DISCONNECTED' } : null
      );
    }

    // 2. Setup 30s Polling Fallback
    const intervalId = setInterval(() => {
      fetchSyncStatus();
    }, 30000);

    return () => {
      if (eventSource) {
        eventSource.close();
      }
      clearInterval(intervalId);
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  return (
    <DashboardSyncContext.Provider
      value={{
        syncStatus,
        triggerManualRefresh,
        isRefreshing,
      }}
    >
      {children}
    </DashboardSyncContext.Provider>
  );
};
