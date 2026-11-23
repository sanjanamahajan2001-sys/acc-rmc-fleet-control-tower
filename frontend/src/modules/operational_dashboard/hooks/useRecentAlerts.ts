import { env } from '../../../config/env';
import { useState, useEffect, useCallback, useRef } from 'react';
import { useDashboardFilters } from '../../site_dashboard/orchestration/DashboardFilterProvider';

export interface RecentAlertDTO {
  id: string;
  time: string;
  type: string;
  site_or_customer: string;
  vehicle: string;
  alert_message: string;
  impact: string;
}

export const useRecentAlerts = () => {
  const { filters } = useDashboardFilters();
  const [alerts, setAlerts] = useState<RecentAlertDTO[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const activeFiltersRef = useRef(filters);
  activeFiltersRef.current = filters;

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    setError(null);
    const requestFilters = activeFiltersRef.current;

    try {
      const queryParams = new URLSearchParams();
      if (requestFilters.plant_id) queryParams.set('plant_id', requestFilters.plant_id);
      if (requestFilters.customer_id) queryParams.set('customer_id', requestFilters.customer_id);
      if (requestFilters.dataset_type) queryParams.set('dataset_type', requestFilters.dataset_type);

      const response = await fetch(`${env.VITE_API_BASE_URL}/alerts?${queryParams.toString()}`);
      if (!response.ok) {
        throw new Error(`HTTP Error ${response.status}: ${response.statusText}`);
      }

      const json = await response.json();
      if (
        requestFilters.plant_id === activeFiltersRef.current.plant_id &&
        requestFilters.customer_id === activeFiltersRef.current.customer_id &&
        requestFilters.dataset_type === activeFiltersRef.current.dataset_type
      ) {
        const rawAlerts = json.items || json.data?.items || json.data || [];
        const mappedAlerts: RecentAlertDTO[] = rawAlerts.map((a: any) => {
          let formattedTime = '08:10 AM';
          if (a.detected_at) {
            try {
              const dt = new Date(a.detected_at);
              formattedTime = dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            } catch (e) {
              formattedTime = '08:10 AM';
            }
          }

          let formattedType = 'Retention';
          if (a.alert_type) {
            formattedType = a.alert_type.replace(/_/g, ' ').toLowerCase();
            formattedType = formattedType.charAt(0).toUpperCase() + formattedType.slice(1);
          }

          return {
            id: a.id || a.alert_id || String(Math.random()),
            time: formattedTime,
            type: formattedType,
            site_or_customer: a.customer_id || a.site_name || a.customer_name || 'ABC Builders',
            vehicle: a.vehicle_id || a.vehicle_registration || 'Multiple',
            alert_message: a.business_impact || a.message || a.recommended_action || 'Vehicle retained after unloading',
            impact: a.severity || 'High',
          };
        });

        setAlerts(mappedAlerts);
      }
    } catch (err: any) {
      if (
        requestFilters.plant_id === activeFiltersRef.current.plant_id &&
        requestFilters.customer_id === activeFiltersRef.current.customer_id &&
        requestFilters.dataset_type === activeFiltersRef.current.dataset_type
      ) {
        setError(err.message || 'Failed to fetch Recent Alerts');
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
    fetchAlerts();
  }, [filters.plant_id, filters.customer_id, filters.dataset_type, fetchAlerts]);

  return {
    alerts,
    loading,
    error,
    refetch: fetchAlerts,
  };
};
