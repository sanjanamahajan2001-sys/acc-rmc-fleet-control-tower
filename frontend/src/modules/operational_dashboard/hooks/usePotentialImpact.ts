import { env } from '../../../config/env';
import { useState, useEffect, useCallback, useRef } from 'react';
import { useDashboardFilters } from '../../site_dashboard/orchestration/DashboardFilterProvider';
import { OperationalIntelligenceStatusEnum } from './useTopProblemCustomers';

export interface PotentialImpactCategoryDTO {
  reduction_pct: number;
  saved_hours_total: number;
  trips_unlocked: number;
}

export interface TotalPotentialImpactDTO {
  saved_hours_total: number;
  total_trips_unlocked: number;
}

export interface PotentialImpactDataDTO {
  holding_impact: PotentialImpactCategoryDTO;
  retention_impact: PotentialImpactCategoryDTO;
  total_impact: TotalPotentialImpactDTO;
}

export interface PotentialImpactResponseDTO {
  success: boolean;
  status: OperationalIntelligenceStatusEnum;
  data: PotentialImpactDataDTO;
  filters: Record<string, any>;
}

export const usePotentialImpact = () => {
  const { filters } = useDashboardFilters();
  const [data, setData] = useState<PotentialImpactResponseDTO | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const activeFiltersRef = useRef(filters);
  activeFiltersRef.current = filters;

  const fetchPotentialImpact = useCallback(async () => {
    setLoading(true);
    setError(null);
    const requestFilters = activeFiltersRef.current;

    try {
      const queryParams = new URLSearchParams();
      if (requestFilters.plant_id) queryParams.set('plant_id', requestFilters.plant_id);
      if (requestFilters.customer_id) queryParams.set('customer_id', requestFilters.customer_id);
      if (requestFilters.dataset_type) queryParams.set('dataset_type', requestFilters.dataset_type);

      const response = await fetch(`${env.VITE_API_BASE_URL}/operational-dashboard/potential-impact?${queryParams.toString()}`);
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
        setError(err.message || 'Failed to fetch potential impact metrics');
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
    fetchPotentialImpact();
  }, [filters.plant_id, filters.customer_id, filters.dataset_type, fetchPotentialImpact]);

  return {
    data,
    loading,
    error,
    status: data?.status || OperationalIntelligenceStatusEnum.UNAVAILABLE,
    refetch: fetchPotentialImpact,
  };
};
