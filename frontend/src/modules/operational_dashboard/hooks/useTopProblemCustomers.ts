import { env } from '../../../config/env';
import { useState, useEffect, useCallback, useRef } from 'react';
import { useDashboardFilters } from '../../site_dashboard/orchestration/DashboardFilterProvider';

export enum OperationalIntelligenceStatusEnum {
  AVAILABLE = 'AVAILABLE',
  NO_OBSERVATIONS = 'NO_OBSERVATIONS',
  UNAVAILABLE = 'UNAVAILABLE',
  SOURCE_UNAVAILABLE = 'SOURCE_UNAVAILABLE',
}

export interface ProblemCustomerDTO {
  customer_id: string;
  customer_name: string;
  rank: number;
  total_trips: number;
  holding_hours: number;
  retention_hours: number;
  total_lost_hours: number;
  cei: number;
}

export interface ProblemCustomerListResponseDTO {
  success: boolean;
  status: OperationalIntelligenceStatusEnum;
  total_count: number;
  data: ProblemCustomerDTO[];
  filters: Record<string, any>;
}

export const useTopProblemCustomers = () => {
  const { filters } = useDashboardFilters();
  const [data, setData] = useState<ProblemCustomerListResponseDTO | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const activeFiltersRef = useRef(filters);
  activeFiltersRef.current = filters;

  const fetchProblemCustomers = useCallback(async () => {
    setLoading(true);
    setError(null);
    const requestFilters = activeFiltersRef.current;

    try {
      const queryParams = new URLSearchParams();
      if (requestFilters.plant_id) queryParams.set('plant_id', requestFilters.plant_id);
      if (requestFilters.customer_id) queryParams.set('customer_id', requestFilters.customer_id);
      if (requestFilters.dataset_type) queryParams.set('dataset_type', requestFilters.dataset_type);

      const response = await fetch(`${env.VITE_API_BASE_URL}/operational-dashboard/problem-customers?${queryParams.toString()}`);
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
        setError(err.message || 'Failed to fetch Top Problem Customers');
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
    fetchProblemCustomers();
  }, [filters.plant_id, filters.customer_id, filters.dataset_type, fetchProblemCustomers]);

  return {
    data,
    loading,
    error,
    refetch: fetchProblemCustomers,
  };
};
