import { create } from 'zustand';
import { erpApiClient } from '../../api';
import { PaginatedResponse, ImportJobResponse, AuditLogItem } from '../../types';

export type ExplorerEntityType =
  | 'dispatches'
  | 'tickets'
  | 'plants'
  | 'vehicles'
  | 'customers'
  | 'drivers'
  | 'orders'
  | 'sites'
  | 'trips'
  | 'invoices';

export type SyntheticFilterOption = 'ALL' | 'REAL_ONLY' | 'SYNTHETIC_ONLY';

interface ExplorerState {
  activeEntity: ExplorerEntityType;
  items: any[];
  totalRecords: number;
  currentPage: number;
  pageSize: number;
  loading: boolean;
  error: string | null;

  // Global search & filters
  searchQuery: string;
  syntheticFilter: SyntheticFilterOption;
  selectedPlant: string;

  // Selected Item for Drawer & Lineage
  selectedItem: any | null;
  drawerOpen: boolean;

  // Import History & Audit Logs
  jobs: ImportJobResponse[];
  auditLogs: AuditLogItem[];

  // Actions
  setActiveEntity: (entity: ExplorerEntityType) => void;
  setSearchQuery: (query: string) => void;
  setSyntheticFilter: (filter: SyntheticFilterOption) => void;
  setSelectedPlant: (plant: string) => void;
  fetchEntityData: (entity?: ExplorerEntityType, page?: number) => Promise<void>;
  selectItemForInspection: (item: any) => void;
  closeDrawer: () => void;
  fetchImportHistory: () => Promise<void>;
  fetchAuditLogs: () => Promise<void>;
}

export const useERPExplorerStore = create<ExplorerState>((set, get) => ({
  activeEntity: 'dispatches',
  items: [],
  totalRecords: 0,
  currentPage: 1,
  pageSize: 20,
  loading: false,
  error: null,

  searchQuery: '',
  syntheticFilter: 'ALL',
  selectedPlant: 'ALL',

  selectedItem: null,
  drawerOpen: false,

  jobs: [],
  auditLogs: [],

  setActiveEntity: (entity) => {
    set({ activeEntity: entity, currentPage: 1, selectedItem: null, drawerOpen: false });
    get().fetchEntityData(entity, 1);
  },

  setSearchQuery: (query) => {
    set({ searchQuery: query });
  },

  setSyntheticFilter: (filter) => {
    set({ syntheticFilter: filter });
  },

  setSelectedPlant: (plant) => {
    set({ selectedPlant: plant });
  },

  fetchEntityData: async (entity = get().activeEntity, page = get().currentPage) => {
    set({ loading: true, error: null });
    try {
      const res: PaginatedResponse<any> = await erpApiClient.getExplorerData(entity, page, get().pageSize);
      set({
        items: res?.items || [],
        totalRecords: res?.total_records || 0,
        currentPage: res?.page || 1,
        loading: false,
      });
    } catch (err: any) {
      set({ loading: false, error: err.message || 'Failed to fetch entity data' });
    }
  },

  selectItemForInspection: (item: any) => {
    set({ selectedItem: item, drawerOpen: true });
  },

  closeDrawer: () => {
    set({ drawerOpen: false });
  },

  fetchImportHistory: async () => {
    try {
      const jobsRes = await erpApiClient.listJobs(1, 50);
      set({ jobs: jobsRes?.items || [] });
    } catch (err) {
      console.error('Failed to fetch import history:', err);
    }
  },

  fetchAuditLogs: async () => {
    try {
      const logsRes = await erpApiClient.getAuditLogs(1, 100);
      set({ auditLogs: logsRes?.items || [] });
    } catch (err) {
      console.error('Failed to fetch audit logs:', err);
    }
  },
}));
