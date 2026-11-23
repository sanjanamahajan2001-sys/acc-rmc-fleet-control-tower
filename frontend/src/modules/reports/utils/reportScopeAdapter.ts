import { ReportScopeDTO } from '../types/report.types';
import { DashboardFilterState } from '../../site_dashboard/orchestration/DashboardFilterProvider';

/**
 * Converts frontend DashboardFilterState into certified backend ReportScopeDTO.
 */
export const adaptFilterStateToReportScope = (
  filters?: Partial<DashboardFilterState> | null,
  overrideScope?: Partial<ReportScopeDTO>
): ReportScopeDTO => {
  const defaultDate = '2026-08-05';
  
  const plant_id = (filters?.plant_id || overrideScope?.plant_id || 'ALL').toUpperCase();
  const customer_id = (filters?.customer_id || overrideScope?.customer_id || 'ALL').toUpperCase();
  const dataset_type = (filters?.dataset_type || overrideScope?.dataset_type || 'ALL').toUpperCase();
  const operation_date = filters?.operation_date || overrideScope?.operation_date || defaultDate;
  const shift = overrideScope?.shift || 'ALL';

  const scope: ReportScopeDTO = {
    plant_id,
    customer_id,
    dataset_type,
    operation_date,
    shift,
  };

  if (overrideScope?.start_date) {
    scope.start_date = overrideScope.start_date;
  }
  if (overrideScope?.end_date) {
    scope.end_date = overrideScope.end_date;
  }

  return scope;
};

/**
 * Creates an immutable snapshot of current scope for background execution safety.
 */
export const createScopeSnapshot = (scope: ReportScopeDTO): ReportScopeDTO => {
  return JSON.parse(JSON.stringify(scope));
};
