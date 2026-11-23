import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { adaptFilterStateToReportScope, createScopeSnapshot } from '../utils/reportScopeAdapter';
import { mapReportErrorToUserMessage } from '../utils/reportErrorMapper';
import { ReportStatus } from '../types/report.types';
import { DashboardFilterProvider, useDashboardFilters } from '../../site_dashboard/orchestration/DashboardFilterProvider';




describe('WS5.4 - Global Filters Integration & Error State UX Suite', () => {
  it('1. adaptFilterStateToReportScope maps DashboardFilterState cleanly to ReportScopeDTO', () => {
    const rawFilter = {
      plant_id: 'VASCO',
      customer_id: 'CUST-001',
      dataset_type: 'REAL_ONLY' as const,
      operation_date: '2026-08-05',
    };

    const scope = adaptFilterStateToReportScope(rawFilter);
    expect(scope.plant_id).toBe('VASCO');
    expect(scope.customer_id).toBe('CUST-001');
    expect(scope.dataset_type).toBe('REAL_ONLY');
    expect(scope.operation_date).toBe('2026-08-05');
    expect(scope.shift).toBe('ALL');
  });

  it('2. createScopeSnapshot creates immutable scope clone', () => {
    const originalScope = { plant_id: 'VASCO', customer_id: 'CUST-A', operation_date: '2026-08-05' };
    const snapshot = createScopeSnapshot(originalScope);

    expect(snapshot).toEqual(originalScope);

    // Mutate original
    originalScope.plant_id = 'MUTATED_PLANT';
    expect(snapshot.plant_id).toBe('VASCO'); // Snapshot remains unaffected
  });

  it('3. mapReportErrorToUserMessage correctly maps NO_DATA terminal status', () => {
    const errorDetails = mapReportErrorToUserMessage(ReportStatus.NO_DATA);
    expect(errorDetails.category).toBe('NO_DATA');
    expect(errorDetails.title).toBe('No Data Found');
    expect(errorDetails.isRetryable).toBe(false);
  });

  it('4. mapReportErrorToUserMessage correctly maps EXPORT_LIMIT_EXCEEDED error', () => {
    const errObj = { code: 'EXPORT_LIMIT_EXCEEDED', message: 'Query returned 15000 records' };
    const errorDetails = mapReportErrorToUserMessage(errObj);
    expect(errorDetails.category).toBe('VALIDATION');
    expect(errorDetails.title).toBe('Export Record Limit Exceeded');
    expect(errorDetails.message).toContain('10,000');
  });

  it('5. mapReportErrorToUserMessage correctly maps HTTP 429 rate limit error', () => {
    const errObj = { status: 429, message: 'Too many requests' };
    const errorDetails = mapReportErrorToUserMessage(errObj);
    expect(errorDetails.category).toBe('RATE_LIMIT');
    expect(errorDetails.title).toBe('Rate Limit Exceeded');
    expect(errorDetails.isRetryable).toBe(true);
  });

  it('6. integrates with DashboardFilterProvider context cleanly', () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <MemoryRouter>
        <DashboardFilterProvider>{children}</DashboardFilterProvider>
      </MemoryRouter>
    );

    const { result } = renderHook(() => useDashboardFilters(), { wrapper });

    act(() => {
      result.current.setPlantFilter('VASCO');
    });

    const scope = adaptFilterStateToReportScope(result.current.filters);
    expect(scope.plant_id).toBe('VASCO');
  });


});
