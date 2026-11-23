import { env } from '../../../config/env';
import { useState, useEffect, useCallback, useRef } from 'react';
import { useDashboardFilters } from '../../site_dashboard/orchestration/DashboardFilterProvider';
import { OperationalIntelligenceStatusEnum } from './useTopProblemCustomers';

export interface DASBucketBreakdownDTO {
  within_20m_count: number;
  within_20m_pct: number;
  range_21_40m_count?: number;
  range_21_40m_pct?: number;
  range_41_60m_count?: number;
  range_41_60m_pct?: number;
  above_60m_count?: number;
  above_60m_pct?: number;
  moderate_20_40m_count: number;
  moderate_20_40m_pct: number;
  critical_above_40m_count: number;
  critical_above_40m_pct: number;
}

export interface DASSummaryDTO {
  total_dispatches: number;
  accurate_dispatches: number;
  das_score: number | null;
  target_sla: number;
  variance: number | null;
  operational_status: 'OPTIMAL' | 'WARNING' | 'CRITICAL' | 'NEUTRAL' | string;
}

export interface DASOverviewResponseDTO {
  success: boolean;
  status: OperationalIntelligenceStatusEnum;
  summary: DASSummaryDTO;
  buckets: DASBucketBreakdownDTO;
  filters: Record<string, any>;
}

export const useDASOverview = () => {
  const { filters } = useDashboardFilters();
  const [data, setData] = useState<DASOverviewResponseDTO | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const activeFiltersRef = useRef(filters);
  activeFiltersRef.current = filters;

  const fetchDASOverview = useCallback(async () => {
    setLoading(true);
    setError(null);
    const requestFilters = activeFiltersRef.current;

    try {
      const queryParams = new URLSearchParams();
      if (requestFilters.plant_id) queryParams.set('plant_id', requestFilters.plant_id);
      if (requestFilters.customer_id) queryParams.set('customer_id', requestFilters.customer_id);
      if (requestFilters.dataset_type) queryParams.set('dataset_type', requestFilters.dataset_type);

      const response = await fetch(`${env.VITE_API_BASE_URL}/operational-dashboard/das-overview?${queryParams.toString()}`);
      if (!response.ok) {
        throw new Error(`HTTP Error ${response.status}: ${response.statusText}`);
      }

      const json = await response.json();
      if (
        requestFilters.plant_id === activeFiltersRef.current.plant_id &&
        requestFilters.customer_id === activeFiltersRef.current.customer_id &&
        requestFilters.dataset_type === activeFiltersRef.current.dataset_type
      ) {
        if (json.success && json.data) {
          setData(json.data);
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
        setError(err.message || 'Failed to fetch Dispatch Accuracy Score data');
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
    fetchDASOverview();
  }, [filters.plant_id, filters.customer_id, filters.dataset_type, fetchDASOverview]);

  return {
    data,
    loading,
    error,
    refetch: fetchDASOverview,
  };
};
