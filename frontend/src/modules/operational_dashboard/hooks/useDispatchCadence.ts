import { env } from '../../../config/env';
import { useState, useEffect, useCallback, useRef } from 'react';
import { useDashboardFilters } from '../../site_dashboard/orchestration/DashboardFilterProvider';
import { OperationalIntelligenceStatusEnum } from './useTopProblemCustomers';

export interface DispatchCadenceItemDTO {
  dispatch_id: string;
  dispatch_number: string;
  dispatch_date: string;
  time_out: string | null;
  time_in: string | null;
  plant_code: string;
  customer_code: string;
  customer_name: string;
  vehicle_id: string;
  driver_name: string;
  interval_mins: number;
  variance_mins: number;
  holding_mins: number;
  retention_mins: number;
  sla_status: string;
  trip_status: string;
  cadence_recommendation: string;
}

export interface DispatchCadenceTableResponseDTO {
  success: boolean;
  status: OperationalIntelligenceStatusEnum;
  data: DispatchCadenceItemDTO[];
  filters: Record<string, any>;
}

export const useDispatchCadence = () => {
  const { filters } = useDashboardFilters();
  const [data, setData] = useState<DispatchCadenceTableResponseDTO | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const activeFiltersRef = useRef(filters);
  activeFiltersRef.current = filters;

  const fetchCadence = useCallback(async () => {
    setLoading(true);
    setError(null);
    const requestFilters = activeFiltersRef.current;

    try {
      const queryParams = new URLSearchParams();
      if (requestFilters.plant_id) queryParams.set('plant_id', requestFilters.plant_id);
      if (requestFilters.customer_id) queryParams.set('customer_id', requestFilters.customer_id);
      if (requestFilters.dataset_type) queryParams.set('dataset_type', requestFilters.dataset_type);

      const response = await fetch(`${env.VITE_API_BASE_URL}/dispatch-analysis/cadence?${queryParams.toString()}`);
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
        setError(err.message || 'Failed to fetch dispatch cadence table data');
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
    fetchCadence();
  }, [filters.plant_id, filters.customer_id, filters.dataset_type, fetchCadence]);

  return {
    data: data?.data || [],
    status: data?.status || OperationalIntelligenceStatusEnum.UNAVAILABLE,
    loading,
    error,
    refetch: fetchCadence,
  };
};
