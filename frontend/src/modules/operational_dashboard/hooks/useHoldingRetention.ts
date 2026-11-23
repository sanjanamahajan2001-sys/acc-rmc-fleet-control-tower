import { env } from '../../../config/env';
import { useState, useEffect, useCallback, useRef } from 'react';
import { useDashboardFilters } from '../../site_dashboard/orchestration/DashboardFilterProvider';
import { OperationalIntelligenceStatusEnum } from './useTopProblemCustomers';

export interface HoldingRetentionTrendPointDTO {
  hour_label: string;
  total_dispatches: number;
  holding_penalty_mins: number;
  retention_penalty_mins: number;
  total_lost_hours: number;
}

export interface HoldingRetentionSummaryDTO {
  total_dispatches: number;
  total_holding_penalty_mins: number;
  total_retention_penalty_mins: number;
  total_lost_hours: number;
}

export interface HoldingRetentionResponseDTO {
  success: boolean;
  status: OperationalIntelligenceStatusEnum;
  summary: HoldingRetentionSummaryDTO;
  data: HoldingRetentionTrendPointDTO[];
  filters: Record<string, any>;
}

export const useHoldingRetention = () => {
  const { filters } = useDashboardFilters();
  const [data, setData] = useState<HoldingRetentionResponseDTO | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const activeFiltersRef = useRef(filters);
  activeFiltersRef.current = filters;

  const fetchHoldingRetention = useCallback(async () => {
    setLoading(true);
    setError(null);
    const requestFilters = activeFiltersRef.current;

    try {
      const queryParams = new URLSearchParams();
      if (requestFilters.plant_id) queryParams.set('plant_id', requestFilters.plant_id);
      if (requestFilters.customer_id) queryParams.set('customer_id', requestFilters.customer_id);
      if (requestFilters.dataset_type) queryParams.set('dataset_type', requestFilters.dataset_type);

      const response = await fetch(`${env.VITE_API_BASE_URL}/operational-dashboard/holding-retention?${queryParams.toString()}`);
      if (!response.ok) {
        throw new Error('HTTP Error ' + response.status + ': ' + response.statusText);
      }

      const json = await response.json();
      if (
        requestFilters.plant_id === activeFiltersRef.current.plant_id &&
        requestFilters.customer_id === activeFiltersRef.current.customer_id &&
        requestFilters.dataset_type === activeFiltersRef.current.dataset_type
      ) {
        if (json.success && json.data) {
          // If response wrapper wraps DTO inside data
          setData(json.data.status ? json.data : json.data);
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
        setError(err.message || 'Failed to fetch Holding & Retention Overview data');
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
    fetchHoldingRetention();
  }, [filters.plant_id, filters.customer_id, filters.dataset_type, fetchHoldingRetention]);

  return {
    data,
    loading,
    error,
    refetch: fetchHoldingRetention,
  };
};
