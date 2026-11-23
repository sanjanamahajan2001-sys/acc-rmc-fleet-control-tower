import { env } from '../../../config/env';
import { useState, useEffect, useCallback, useRef } from 'react';
import { useDashboardFilters } from '../../site_dashboard/orchestration/DashboardFilterProvider';
import { OperationalIntelligenceStatusEnum } from './useTopProblemCustomers';
import { DispatchCadenceItemDTO } from './useDispatchCadence';

export interface VehiclePerformanceDTO {
  vehicle_id: string;
  driver_name: string;
  plant_code: string;
  trips_count: number;
  volume_m3: number;
  avg_holding_mins: number;
  avg_retention_mins: number;
  das_score_pct: number;
  status: string;
}

export interface CustomerVehicleReportDTO {
  customer_code: string;
  customer_name: string;
  total_dispatches: number;
  total_volume_m3: number;
  avg_holding_mins: number;
  avg_retention_mins: number;
  das_score_pct: number;
  vehicles: VehiclePerformanceDTO[];
  recent_dispatches: DispatchCadenceItemDTO[];
}

export interface CustomerVehicleReportResponseDTO {
  success: boolean;
  status: OperationalIntelligenceStatusEnum;
  data: CustomerVehicleReportDTO[];
  filters: Record<string, any>;
}

export const useDispatchCustomerReport = () => {
  const { filters } = useDashboardFilters();
  const [data, setData] = useState<CustomerVehicleReportResponseDTO | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const activeFiltersRef = useRef(filters);
  activeFiltersRef.current = filters;

  const fetchCustomerReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    const requestFilters = activeFiltersRef.current;

    try {
      const queryParams = new URLSearchParams();
      if (requestFilters.plant_id) queryParams.set('plant_id', requestFilters.plant_id);
      if (requestFilters.customer_id) queryParams.set('customer_id', requestFilters.customer_id);
      if (requestFilters.dataset_type) queryParams.set('dataset_type', requestFilters.dataset_type);

      const response = await fetch(`${env.VITE_API_BASE_URL}/dispatch-analysis/customer-report?${queryParams.toString()}`);
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
        setError(err.message || 'Failed to fetch customer vehicle report');
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
    fetchCustomerReport();
  }, [filters.plant_id, filters.customer_id, filters.dataset_type, fetchCustomerReport]);

  return {
    data: data?.data || [],
    status: data?.status || OperationalIntelligenceStatusEnum.UNAVAILABLE,
    loading,
    error,
    refetch: fetchCustomerReport,
  };
};
