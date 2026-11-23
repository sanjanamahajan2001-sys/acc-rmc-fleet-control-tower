import { env } from '../../../config/env';
import { useState, useEffect, useCallback, useRef } from 'react';
import { useDashboardFilters } from '../../site_dashboard/orchestration/DashboardFilterProvider';

export interface OperationalContextEnvelope {
  dataset_id: string;
  snapshot_version: string;
  operational_date: string;
  plant_id: string;
  customer_id: string;
  dataset_type: string;
  generated_at: string;
}

export interface ShellContextResponse {
  context: OperationalContextEnvelope;
  metadata: {
    total_dispatches: number;
    dataset_status: string;
    sync_status: string;
  };
  available_plants: Array<{ id: string; name: string; code?: string }>;
  available_customers: Array<{ id: string; name: string; code?: string }>;
}

export const useOperationalDashboardContext = () => {
  const { filters, updateMetadata } = useDashboardFilters();
  const [shellData, setShellData] = useState<ShellContextResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const activeFiltersRef = useRef(filters);
  activeFiltersRef.current = filters;

  // Stable ref for updateMetadata to prevent unnecessary re-creation of fetchContext
  const updateMetadataRef = useRef(updateMetadata);
  updateMetadataRef.current = updateMetadata;

  const fetchContext = useCallback(async () => {
    setLoading(true);
    setError(null);

    const controller = new AbortController();
    const { signal } = controller;

    try {
      const query = new URLSearchParams({
        plant_id: filters.plant_id,
        customer_id: filters.customer_id,
        dataset_type: filters.dataset_type,
      }).toString();

      const res = await fetch(env.VITE_API_BASE_URL + '/operational-dashboard/context?' + query, { signal });
      const body = await res.json();

      if (!res.ok || !body.success) {
        throw new Error(body.message || 'Failed to fetch operational shell context');
      }

      if (
        activeFiltersRef.current.plant_id !== filters.plant_id ||
        activeFiltersRef.current.customer_id !== filters.customer_id ||
        activeFiltersRef.current.dataset_type !== filters.dataset_type
      ) {
        return;
      }

      const data: ShellContextResponse = body.data;
      setShellData(data);

      if (data.context) {
        updateMetadataRef.current({
          operational_date: data.context.operational_date,
          dataset_id: data.context.dataset_id,
          import_timestamp: data.context.generated_at,
          calculation_timestamp: data.context.generated_at,
          total_dispatches: data.metadata?.total_dispatches ?? 0,
          total_trips: data.metadata?.total_dispatches ?? 0,
          dataset_status: data.metadata?.dataset_status || 'ACTIVE_PRODUCTION',
        });
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        return;
      }
      setError(err.message || 'An error occurred fetching operational context');
    } finally {
      setLoading(false);
    }
  }, [filters.plant_id, filters.customer_id, filters.dataset_type]);

  useEffect(() => {
    fetchContext();
  }, [fetchContext]);

  return {
    shellData,
    loading,
    error,
    refetchContext: fetchContext,
  };
};
