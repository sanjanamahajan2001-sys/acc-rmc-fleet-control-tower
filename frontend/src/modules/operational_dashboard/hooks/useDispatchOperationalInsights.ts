import { env } from '../../../config/env';
import { useState, useEffect, useCallback, useRef } from 'react';
import { useDashboardFilters } from '../../site_dashboard/orchestration/DashboardFilterProvider';
import { OperationalIntelligenceStatusEnum } from './useTopProblemCustomers';

export interface OperationalInsightItemDTO {
  id: string;
  category: string;
  title: string;
  description: string;
  impact_level: string;
  primary_metric: string;
  action_type: string;
  target_interval_mins: number;
  estimated_delay_reduction_hrs: number;
}

export interface OperationalInsightsDTO {
  total_insights: number;
  primary_pacing_strategy: string;
  target_departure_interval_mins: number;
  potential_recoverable_delay_hrs: number;
  insights: OperationalInsightItemDTO[];
}

export interface OperationalInsightsResponseDTO {
  success: boolean;
  status: OperationalIntelligenceStatusEnum;
  data: OperationalInsightsDTO | null;
  filters: Record<string, any>;
}

export const useDispatchOperationalInsights = () => {
  const { filters } = useDashboardFilters();
  const [data, setData] = useState<OperationalInsightsResponseDTO | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const activeFiltersRef = useRef(filters);
  activeFiltersRef.current = filters;

  const fetchInsights = useCallback(async () => {
    setLoading(true);
    setError(null);
    const requestFilters = activeFiltersRef.current;

    try {
      const queryParams = new URLSearchParams();
      if (requestFilters.plant_id) queryParams.set('plant_id', requestFilters.plant_id);
      if (requestFilters.customer_id) queryParams.set('customer_id', requestFilters.customer_id);
      if (requestFilters.dataset_type) queryParams.set('dataset_type', requestFilters.dataset_type);

      const response = await fetch(`${env.VITE_API_BASE_URL}/dispatch-analysis/operational-insights?${queryParams.toString()}`);
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
        setError(err.message || 'Failed to fetch operational insights');
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
    fetchInsights();
  }, [filters.plant_id, filters.customer_id, filters.dataset_type, fetchInsights]);

  return {
    data: data?.data || null,
    status: data?.status || OperationalIntelligenceStatusEnum.UNAVAILABLE,
    loading,
    error,
    refetch: fetchInsights,
  };
};
