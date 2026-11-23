import { env } from '../../../config/env';
import { useState, useEffect, useCallback, useRef } from 'react';
import { useDashboardFilters } from '../../site_dashboard/orchestration/DashboardFilterProvider';
import { OperationalIntelligenceStatusEnum } from './useTopProblemCustomers';

export interface DelayCategoryDTO {
  category_name: string;
  delay_hours: number;
  percentage_contribution: number;
  affected_trips_count: number;
  severity: string;
  recommendation: string;
}

export interface DispatchDelayAnalyticsDTO {
  total_delay_hours: number;
  buildup_delay_hours: number;
  unload_delay_hours: number;
  sequence_variance_delay_hours: number;
  categories: DelayCategoryDTO[];
}

export interface DispatchDelayAnalyticsResponseDTO {
  success: boolean;
  status: OperationalIntelligenceStatusEnum;
  data: DispatchDelayAnalyticsDTO | null;
  filters: Record<string, any>;
}

export const useDispatchDelayAnalytics = () => {
  const { filters } = useDashboardFilters();
  const [data, setData] = useState<DispatchDelayAnalyticsResponseDTO | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const activeFiltersRef = useRef(filters);
  activeFiltersRef.current = filters;

  const fetchDelayAnalytics = useCallback(async () => {
    setLoading(true);
    setError(null);
    const requestFilters = activeFiltersRef.current;

    try {
      const queryParams = new URLSearchParams();
      if (requestFilters.plant_id) queryParams.set('plant_id', requestFilters.plant_id);
      if (requestFilters.customer_id) queryParams.set('customer_id', requestFilters.customer_id);
      if (requestFilters.dataset_type) queryParams.set('dataset_type', requestFilters.dataset_type);

      const response = await fetch(`${env.VITE_API_BASE_URL}/dispatch-analysis/delay-analytics?${queryParams.toString()}`);
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
        setError(err.message || 'Failed to fetch dispatch delay analytics');
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
    fetchDelayAnalytics();
  }, [filters.plant_id, filters.customer_id, filters.dataset_type, fetchDelayAnalytics]);

  return {
    data: data?.data || null,
    status: data?.status || OperationalIntelligenceStatusEnum.UNAVAILABLE,
    loading,
    error,
    refetch: fetchDelayAnalytics,
  };
};
