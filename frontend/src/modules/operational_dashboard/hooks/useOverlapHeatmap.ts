import { env } from '../../../config/env';
import { useState, useEffect, useCallback, useRef } from 'react';
import { useDashboardFilters } from '../../site_dashboard/orchestration/DashboardFilterProvider';
import { OperationalIntelligenceStatusEnum } from './useTopProblemCustomers';

export interface OverlapSiteDTO {
  site_id: string;
  site_name: string;
  rank: number;
  total_trips: number;
  peak_tms_together: number;
  avg_tms_standing_together: number;
  overlap_hours: number;
  weighted_tm_minutes: number;
}

export interface OverlapHeatmapResponseDTO {
  success: boolean;
  status: OperationalIntelligenceStatusEnum;
  total_sites: number;
  data: OverlapSiteDTO[];
  filters: Record<string, any>;
}

export const useOverlapHeatmap = () => {
  const { filters } = useDashboardFilters();
  const [data, setData] = useState<OverlapHeatmapResponseDTO | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const activeFiltersRef = useRef(filters);
  activeFiltersRef.current = filters;

  const fetchOverlapHeatmap = useCallback(async () => {
    setLoading(true);
    setError(null);
    const requestFilters = activeFiltersRef.current;

    try {
      const queryParams = new URLSearchParams();
      if (requestFilters.plant_id) queryParams.set('plant_id', requestFilters.plant_id);
      if (requestFilters.customer_id) queryParams.set('customer_id', requestFilters.customer_id);
      if (requestFilters.dataset_type) queryParams.set('dataset_type', requestFilters.dataset_type);

      // Fetch all sites for drawer directory completeness
      const response = await fetch(`${env.VITE_API_BASE_URL}/operational-dashboard/overlap-heatmap?${queryParams.toString()}`);
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
        setError(err.message || 'Failed to fetch Overlap Heat Map data');
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
    fetchOverlapHeatmap();
  }, [filters.plant_id, filters.customer_id, filters.dataset_type, fetchOverlapHeatmap]);

  return {
    data,
    loading,
    error,
    refetch: fetchOverlapHeatmap,
  };
};
