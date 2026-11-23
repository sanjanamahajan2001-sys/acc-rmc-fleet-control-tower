import { env } from '../../../config/env';
import { useState, useEffect } from 'react';
import { useDashboardFilters } from '../../site_dashboard/orchestration/DashboardFilterProvider';

export interface DASDetailRowDTO {
  customer_id: string;
  customer_name: string;
  rank: number;
  total_dispatches: number;
  accurate_count: number;
  moderate_count: number;
  critical_count: number;
  das_score: number;
  within_20m_pct: number;
  moderate_pct: number;
  critical_pct: number;
  operational_status: string;
}

export interface DASDetailsData {
  success: boolean;
  status: string;
  total_customers: number;
  summary: {
    total_dispatches: number;
    accurate_dispatches: number;
    das_score: number | null;
    target_sla: number;
    variance: number | null;
    operational_status: string;
  };
  buckets: {
    within_20m_count: number;
    within_20m_pct: number;
    moderate_20_40m_count: number;
    moderate_20_40m_pct: number;
    critical_above_40m_count: number;
    critical_above_40m_pct: number;
  };
  data: DASDetailRowDTO[];
  filters: Record<string, any>;
}

export function useDASDetails() {
  const { filters } = useDashboardFilters();
  const [data, setData] = useState<DASDetailsData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);

    const queryParams = new URLSearchParams();
    if (filters.plant_id) queryParams.set('plant_id', filters.plant_id);
    if (filters.customer_id) queryParams.set('customer_id', filters.customer_id);
    if (filters.dataset_type) queryParams.set('dataset_type', filters.dataset_type);

    fetch(`${env.VITE_API_BASE_URL}/operational-dashboard/das-details?${queryParams.toString()}`)
      .then((res) => {
        if (!res.ok) {
          throw new Error('API Error ' + res.status);
        }
        return res.json();
      })
      .then((json) => {
        if (isMounted) {
          if (json.success && json.data) {
            setData(json.data);
          } else {
            setError('Invalid data payload received');
          }
          setIsLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || 'Failed to fetch DAS details');
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [filters.plant_id, filters.customer_id, filters.dataset_type]);

  return { data, isLoading, error };
}
