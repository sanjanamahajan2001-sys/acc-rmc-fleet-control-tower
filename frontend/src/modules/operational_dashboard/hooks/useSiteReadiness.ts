import { env } from '../../../config/env';
import { useState, useEffect, useCallback, useRef } from 'react';
import { useDashboardFilters } from '../../site_dashboard/orchestration/DashboardFilterProvider';
import { OperationalIntelligenceStatusEnum } from './useTopProblemCustomers';

export enum OperationalGradeEnum {
  GRADE_A = 'GRADE_A',
  GRADE_B = 'GRADE_B',
  GRADE_C = 'GRADE_C',
  GRADE_D = 'GRADE_D',
}

export interface SiteReadinessDTO {
  site_id: string;
  site_name: string;
  rank: number;
  total_trips: number;
  swi_site: number;
  dpi_site: number;
  fui_site: number;
  sri_score: number;
  grade: OperationalGradeEnum;
}

export interface SiteReadinessResponseDTO {
  success: boolean;
  status: OperationalIntelligenceStatusEnum;
  total_sites: number;
  data: SiteReadinessDTO[];
  filters: Record<string, any>;
}

export const useSiteReadiness = () => {
  const { filters } = useDashboardFilters();
  const [data, setData] = useState<SiteReadinessResponseDTO | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const activeFiltersRef = useRef(filters);
  activeFiltersRef.current = filters;

  const fetchSiteReadiness = useCallback(async () => {
    setLoading(true);
    setError(null);
    const requestFilters = activeFiltersRef.current;

    try {
      const queryParams = new URLSearchParams();
      if (requestFilters.plant_id) queryParams.set('plant_id', requestFilters.plant_id);
      if (requestFilters.customer_id) queryParams.set('customer_id', requestFilters.customer_id);
      if (requestFilters.dataset_type) queryParams.set('dataset_type', requestFilters.dataset_type);

      const response = await fetch(`${env.VITE_API_BASE_URL}/operational-dashboard/site-readiness?${queryParams.toString()}`);
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
        setError(err.message || 'Failed to fetch Site Readiness Index data');
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
    fetchSiteReadiness();
  }, [filters.plant_id, filters.customer_id, filters.dataset_type, fetchSiteReadiness]);

  return {
    data,
    loading,
    error,
    refetch: fetchSiteReadiness,
  };
};
