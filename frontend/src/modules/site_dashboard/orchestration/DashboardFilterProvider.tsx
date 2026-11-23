import { env } from '../../../config/env';
import React, { createContext, useContext, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

export interface DashboardFilterState {
  plant_id: string;
  customer_id: string;
  dataset_type: 'ALL' | 'REAL_ONLY' | 'SYNTHETIC_ONLY';
  operation_date?: string;
  dataset_id?: string;
}

export interface FilterOption {
  id: string;
  name: string;
  code?: string;
}

export interface DatasetMetadata {
  operational_date: string;
  dataset_id: string;
  import_timestamp: string;
  calculation_timestamp: string;
  total_dispatches: number;
  total_trips: number;
  dataset_status: string;
}

interface DashboardFilterContextType {
  filters: DashboardFilterState;
  metadata: DatasetMetadata | null;
  plantOptions: FilterOption[];
  customerOptions: FilterOption[];
  setPlantFilter: (plantId: string) => void;
  setCustomerFilter: (customerId: string) => void;
  setDatasetTypeFilter: (type: 'ALL' | 'REAL_ONLY' | 'SYNTHETIC_ONLY') => void;
  setOperationDateFilter: (date: string) => void;
  updateMetadata: (meta: DatasetMetadata) => void;
  resetFilters: () => void;
}

const DEFAULT_FILTERS: DashboardFilterState = {
  plant_id: 'ALL',
  customer_id: 'ALL',
  dataset_type: 'ALL',
  operation_date: undefined,
  dataset_id: undefined,
};

const DashboardFilterContext = createContext<DashboardFilterContextType | undefined>(undefined);

export const DashboardFilterProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [searchParams, setSearchParams] = useSearchParams();

  const [plantOptions, setPlantOptions] = useState<FilterOption[]>([
    { id: 'ALL', name: 'All Plants' }
  ]);
  const [customerOptions, setCustomerOptions] = useState<FilterOption[]>([
    { id: 'ALL', name: 'All Customers' }
  ]);

  // Initialize filters from URL search params or defaults
  const [filters, setFilters] = useState<DashboardFilterState>(() => ({
    plant_id: searchParams.get('plant_id') || DEFAULT_FILTERS.plant_id,
    customer_id: searchParams.get('customer_id') || DEFAULT_FILTERS.customer_id,
    dataset_type: (searchParams.get('dataset_type') as any) || DEFAULT_FILTERS.dataset_type,
    operation_date: searchParams.get('operation_date') || undefined,
    dataset_id: searchParams.get('dataset_id') || undefined,
  }));

  const [metadata, setMetadata] = useState<DatasetMetadata | null>(() => ({
    operational_date: searchParams.get('operation_date') || '',
    dataset_id: searchParams.get('dataset_id') || '',
    import_timestamp: new Date().toISOString(),
    calculation_timestamp: new Date().toISOString(),
    total_dispatches: 0,
    total_trips: 0,
    dataset_status: 'ACTIVE_PRODUCTION',
  }));

  // Dynamically load plant and customer options from canonical API
  useEffect(() => {
    fetchFilterMetadata();

    const handleSettingsUpdated = () => {
      fetchFilterMetadata();
    };

    window.addEventListener('fleet-settings-updated', handleSettingsUpdated);
    window.addEventListener('customer-overrides-updated', handleSettingsUpdated);
    window.addEventListener('fleet-dataset-updated', handleSettingsUpdated);

    return () => {
      window.removeEventListener('fleet-settings-updated', handleSettingsUpdated);
      window.removeEventListener('customer-overrides-updated', handleSettingsUpdated);
      window.removeEventListener('fleet-dataset-updated', handleSettingsUpdated);
    };
  }, []);

  const fetchFilterMetadata = async () => {
    try {
      const res = await fetch(env.VITE_API_BASE_URL + '/site-dashboard/filters');
      const data = await res.json();
      if (data.success && data.data) {
        setPlantOptions(data.data.plants || [{ id: 'ALL', name: 'All Plants' }]);
        setCustomerOptions(data.data.customers || [{ id: 'ALL', name: 'All Customers' }]);
        if (data.data.dataset_info) {
          setMetadata(data.data.dataset_info);
          setFilters((prev) => ({
            ...prev,
            operation_date: searchParams.get('operation_date') || data.data.dataset_info.operational_date,
            dataset_id: searchParams.get('dataset_id') || data.data.dataset_info.dataset_id,
          }));
        }
      }
    } catch (e) {
      // Keep initial defaults on failure
    }
  };

  // Sync state changes to URL search parameters
  const updateFiltersAndUrl = (newFilters: DashboardFilterState) => {
    setFilters(newFilters);
    const params: Record<string, string> = {};
    if (newFilters.plant_id !== 'ALL') params.plant_id = newFilters.plant_id;
    if (newFilters.customer_id !== 'ALL') params.customer_id = newFilters.customer_id;
    if (newFilters.dataset_type !== 'ALL') params.dataset_type = newFilters.dataset_type;
    if (newFilters.operation_date) params.operation_date = newFilters.operation_date;
    if (newFilters.dataset_id) params.dataset_id = newFilters.dataset_id;
    setSearchParams(params, { replace: true });
  };

  const setPlantFilter = (plantId: string) => {
    updateFiltersAndUrl({ ...filters, plant_id: plantId });
  };

  const setCustomerFilter = (customerId: string) => {
    updateFiltersAndUrl({ ...filters, customer_id: customerId });
  };

  const setDatasetTypeFilter = (type: 'ALL' | 'REAL_ONLY' | 'SYNTHETIC_ONLY') => {
    updateFiltersAndUrl({ ...filters, dataset_type: type });
  };

  const setOperationDateFilter = (date: string) => {
    updateFiltersAndUrl({ ...filters, operation_date: date });
  };

  const updateMetadata = (meta: DatasetMetadata) => {
    setMetadata(meta);
  };

  const resetFilters = () => {
    updateFiltersAndUrl(DEFAULT_FILTERS);
  };

  return (
    <DashboardFilterContext.Provider
      value={{
        filters,
        metadata,
        plantOptions,
        customerOptions,
        setPlantFilter,
        setCustomerFilter,
        setDatasetTypeFilter,
        setOperationDateFilter,
        updateMetadata,
        resetFilters,
      }}
    >
      {children}
    </DashboardFilterContext.Provider>
  );
};

export const useDashboardFilters = (): DashboardFilterContextType => {
  const context = useContext(DashboardFilterContext);
  if (!context) {
    throw new Error('useDashboardFilters must be used within a DashboardFilterProvider');
  }
  return context;
};
