export interface ExplorerEntityItem {
  id: string;
  [key: string]: any;
}

export interface LineageStep {
  stage: string;
  label: string;
  detail: string;
  status: 'COMPLETED' | 'PASSED' | 'VALID' | 'COMMITTED';
  timestamp: string;
}

export interface DatabaseIntegrityMetrics {
  dispatchesCount: number;
  ticketsCount: number;
  plantsCount: number;
  vehiclesCount: number;
  customersCount: number;
  driversCount: number;
  ordersCount: number;
  importJobsCount: number;
  auditLogsCount: number;
  orphanRecordsCount: number;
  duplicateKeysCount: number;
  successRatePercentage: number;
  integrityScorePercentage: number;
}
