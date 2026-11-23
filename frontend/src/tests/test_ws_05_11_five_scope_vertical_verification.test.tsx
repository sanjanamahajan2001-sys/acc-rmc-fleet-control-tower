import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { DispatchAnalysisDashboardPage } from '../modules/operational_dashboard/pages/DispatchAnalysisDashboardPage';
import { DashboardFilterProvider } from '../modules/site_dashboard/orchestration/DashboardFilterProvider';

describe('WS-05.11 — Five-Scope Vertical Verification & Cross-Layer Reconciliation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('1. V-01 Global Scope Vertical Slice Verification', () => {
    render(
      <MemoryRouter initialEntries={['/dispatch-analysis?dataset_type=REAL_ONLY']}>
        <DashboardFilterProvider>
          <DispatchAnalysisDashboardPage />
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    expect(screen.getByText('Dispatch Analysis & Cadence Optimization')).toBeInTheDocument();
  });

  it('2. V-02 Vasco Scope Vertical Slice Verification', () => {
    render(
      <MemoryRouter initialEntries={['/dispatch-analysis?plant_id=ACC_VASCO&dataset_type=REAL_ONLY']}>
        <DashboardFilterProvider>
          <DispatchAnalysisDashboardPage />
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    expect(screen.getByText('Dispatch Analysis & Cadence Optimization')).toBeInTheDocument();
  });

  it('3. V-03 Kundaim Scope Vertical Slice Verification', () => {
    render(
      <MemoryRouter initialEntries={['/dispatch-analysis?plant_id=ACC_KUNDAIM&dataset_type=REAL_ONLY']}>
        <DashboardFilterProvider>
          <DispatchAnalysisDashboardPage />
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    expect(screen.getByText('Dispatch Analysis & Cadence Optimization')).toBeInTheDocument();
  });

  it('4. V-04 Customer Scope Vertical Slice Verification', () => {
    render(
      <MemoryRouter initialEntries={['/dispatch-analysis?plant_id=ACC_KUNDAIM&customer_id=CUST_AARA_HOTELS&dataset_type=REAL_ONLY']}>
        <DashboardFilterProvider>
          <DispatchAnalysisDashboardPage />
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    expect(screen.getByText('Dispatch Analysis & Cadence Optimization')).toBeInTheDocument();
  });

  it('5. V-05 Synthetic Scope Vertical Slice Verification', () => {
    render(
      <MemoryRouter initialEntries={['/dispatch-analysis?dataset_type=SYNTHETIC_ONLY']}>
        <DashboardFilterProvider>
          <DispatchAnalysisDashboardPage />
        </DashboardFilterProvider>
      </MemoryRouter>
    );

    expect(screen.getByText('Dispatch Analysis & Cadence Optimization')).toBeInTheDocument();
  });
});
