import { env } from '../../../config/env';
import { useState, useEffect, useCallback, useRef } from 'react';
import { useDashboardFilters } from '../../site_dashboard/orchestration/DashboardFilterProvider';
import { OperationalIntelligenceStatusEnum } from './useTopProblemCustomers';

export interface DispatchCadenceKPIsDTO {
  total_dispatches: number;
  on_schedule_dispatches: number;
  sla_compliance_pct: number;
  avg_interval_mins: number;
  interval_variance_mins: number;
  das_score_pct: number;
  completed_dispatches: number;
  avg_loading_mins: number;
  avg_transit_mins: number;
  recommended_interval_mins: number;
  cadence_status: 'Optimal' | 'Good' | 'Warning' | 'Critical' | string;
  potential_delay_reduction_hrs: number;
}

export interface DispatchCadenceKPIResponseDTO {
  success: boolean;
  status: OperationalIntelligenceStatusEnum;
  data: DispatchCadenceKPIsDTO | null;
  filters: Record<string, any>;
}

export const useDispatchAnalysisKPIs = () => {
  const { filters } = useDashboardFilters();
  const [data, setData] = useState<DispatchCadenceKPIResponseDTO | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const activeFiltersRef = useRef(filters);
  activeFiltersRef.current = filters;

  const fetchKPIs = useCallback(async () => {
    setLoading(true);
    setError(null);
    const requestFilters = activeFiltersRef.current;

    try {
      const queryParams = new URLSearchParams();
      if (requestFilters.plant_id) queryParams.set('plant_id', requestFilters.plant_id);
      if (requestFilters.customer_id) queryParams.set('customer_id', requestFilters.customer_id);
      if (requestFilters.dataset_type) queryParams.set('dataset_type', requestFilters.dataset_type);

      const response = await fetch(`${env.VITE_API_BASE_URL}/dispatch-analysis/kpis?${queryParams.toString()}`);
      if (!response.ok) {
        throw new Error(`HTTP Error ${response.status}: ${response.statusText}`);
      }

      const json = await response.json();
      if (
        requestFilters.plant_id === activeFiltersRef.current.plant_id &&
        requestFilters.customer_id === activeFiltersRef.current.customer_id &&
        requestFilters.dataset_type === activeFiltersRef.current.dataset_type
      ) {
        if (json.success) {
          setData(json);
        } else {
          setError('Invalid API response format');
        }
      }
    } catch (err: any) {
      if (
        requestFilters.plant_id === activeFiltersRef.current.plant_id &&
        requestFilters.customer_id === activeFiltersRef.current.customer_id &&
        requestFilters.dataset_type === activeFiltersRef.current.dataset_type
      ) {
        setError(err.message || 'Failed to fetch dispatch analysis KPIs');
      }
    } finally {
      if (
        requestFilters.plant_id === activeFiltersRef.current.plant_id &&
        requestFilters.customer_id === activeFiltersRef.current.customer_id &&
        requestFilters.dataset_type === activeFiltersRef.current.dataset_type
      ) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    fetchKPIs();
  }, [filters.plant_id, filters.customer_id, filters.dataset_type, fetchKPIs]);

  return {
    data: data?.data || null,
    status: data?.status || OperationalIntelligenceStatusEnum.UNAVAILABLE,
    loading,
    error,
    refetch: fetchKPIs,
  };
};
