import { env } from '../../../config/env';
import { useState, useEffect, useCallback, useRef } from 'react';
import { useDashboardFilters } from '../../site_dashboard/orchestration/DashboardFilterProvider';

export enum KPIStatusEnum {
  OPTIMAL = 'OPTIMAL',
  WARNING = 'WARNING',
  CRITICAL = 'CRITICAL',
  NEUTRAL = 'NEUTRAL',
}

export enum AvailabilityEnum {
  AVAILABLE = 'AVAILABLE',
  SOURCE_UNAVAILABLE = 'SOURCE_UNAVAILABLE',
  BASELINE_UNAVAILABLE = 'BASELINE_UNAVAILABLE',
  NO_OBSERVATIONS = 'NO_OBSERVATIONS',
}

export interface KPICardItemDTO {
  key: string;
  label: string;
  current_value: number | null;
  unit: string;
  target?: number | null;
  variance?: number | null;
  total_volume_m3?: number | null;
  status: KPIStatusEnum;
  availability: AvailabilityEnum;
}

export interface KPIRibbonContainerDTO {
  dispatch_accuracy: KPICardItemDTO;
  swi: KPICardItemDTO;
  dpi: KPICardItemDTO;
  fui: KPICardItemDTO;
  total_dispatches: KPICardItemDTO;
}

export interface KPIRibbonResponseDTO {
  context: {
    dataset_id: string;
    snapshot_version: string;
    operational_date: string;
    plant_id: string;
    customer_id: string;
    dataset_type: string;
    generated_at: string;
  };
  kpis: KPIRibbonContainerDTO;
}

export const useExecutiveKPIs = () => {
  const { filters } = useDashboardFilters();
  const [kpiData, setKpiData] = useState<KPIRibbonResponseDTO | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const activeFiltersRef = useRef(filters);
  activeFiltersRef.current = filters;

  const fetchKPIs = useCallback(async () => {
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

      const res = await fetch(env.VITE_API_BASE_URL + '/operational-dashboard/kpis?' + query, { signal });
      const body = await res.json();

      if (!res.ok || !body.success) {
        throw new Error(body.message || 'Failed to fetch executive KPIs');
      }

      if (
        activeFiltersRef.current.plant_id !== filters.plant_id ||
        activeFiltersRef.current.customer_id !== filters.customer_id ||
        activeFiltersRef.current.dataset_type !== filters.dataset_type
      ) {
        return;
      }

      setKpiData(body.data);
    } catch (err: any) {
      if (err.name === 'AbortError') {
        return;
      }
      setError(err.message || 'An error occurred fetching executive KPIs');
    } finally {
      setLoading(false);
    }
  }, [filters.plant_id, filters.customer_id, filters.dataset_type]);

  useEffect(() => {
    fetchKPIs();
  }, [fetchKPIs]);

  return {
    kpiData,
    loading,
    error,
    refetchKPIs: fetchKPIs,
  };
};
