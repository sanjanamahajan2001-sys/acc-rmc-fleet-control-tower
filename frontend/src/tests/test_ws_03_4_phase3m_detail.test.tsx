import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { DASDetailModal } from '../modules/operational_dashboard/components/DASDetailModal';

const mockOverviewData = {
  success: true,
  status: 'AVAILABLE',
  summary: {
    total_dispatches: 978,
    accurate_dispatches: 561,
    das_score: 57.4,
    target_sla: 90.0,
    variance: -32.6,
    operational_status: 'CRITICAL',
  },
  buckets: {
    within_20m_count: 561,
    within_20m_pct: 57.4,
    moderate_20_40m_count: 212,
    moderate_20_40m_pct: 21.7,
    critical_above_40m_count: 205,
    critical_above_40m_pct: 21.0,
  },
  filters: { plant_id: 'ACC_DHARGA' },
};

const mockDetailsData = {
  success: true,
  status: 'AVAILABLE',
  total_customers: 2,
  summary: mockOverviewData.summary,
  buckets: mockOverviewData.buckets,
  data: [
    {
      customer_id: 'CUST_01',
      customer_name: 'ALPHA CONST',
      rank: 1,
      total_dispatches: 100,
      accurate_count: 40,
      moderate_count: 30,
      critical_count: 30,
      das_score: 40.0,
      within_20m_pct: 40.0,
      moderate_pct: 30.0,
      critical_pct: 30.0,
      operational_status: 'CRITICAL',
    },
    {
      customer_id: 'CUST_02',
      customer_name: 'BETA CONST',
      rank: 2,
      total_dispatches: 878,
      accurate_count: 521,
      moderate_count: 182,
      critical_count: 175,
      das_score: 59.3,
      within_20m_pct: 59.3,
      moderate_pct: 20.7,
      critical_pct: 19.9,
      operational_status: 'CRITICAL',
    },
  ],
  filters: { plant_id: 'ACC_DHARGA' },
};

describe('WS-03.4 Phase 3M Gap Closure — DAS Detail Modal & API Integration', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders DASDetailModal shell with real DTO breakdown rows when open', () => {
    render(
      <DASDetailModal
        isOpen={true}
        onClose={vi.fn()}
        summary={mockDetailsData.summary}
        buckets={mockDetailsData.buckets}
        detailRows={mockDetailsData.data}
        hasDetailApi={true}
      />
    );

    expect(screen.getByText(/DISPATCH ACCURACY DETAILS/i)).toBeInTheDocument();
    expect(screen.getAllByText('57.4%').length).toBeGreaterThan(0);
    expect(screen.getByText('ALPHA CONST')).toBeInTheDocument();
    expect(screen.getByText('BETA CONST')).toBeInTheDocument();
    expect(screen.getByText('40.0%')).toBeInTheDocument();
  });

  it('closes modal on Escape key press', () => {
    const handleClose = vi.fn();
    render(
      <DASDetailModal
        isOpen={true}
        onClose={handleClose}
        summary={mockDetailsData.summary}
        buckets={mockDetailsData.buckets}
        detailRows={mockDetailsData.data}
        hasDetailApi={true}
      />
    );

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('renders honest NO_OBSERVATIONS when total dispatches is 0', () => {
    render(
      <DASDetailModal
        isOpen={true}
        onClose={vi.fn()}
        summary={{
          total_dispatches: 0,
          accurate_dispatches: 0,
          das_score: null,
          target_sla: 90.0,
          variance: null,
          operational_status: 'NEUTRAL',
        }}
        buckets={{
          within_20m_count: 0,
          within_20m_pct: 0,
          moderate_20_40m_count: 0,
          moderate_20_40m_pct: 0,
          critical_above_40m_count: 0,
          critical_above_40m_pct: 0,
        }}
        detailRows={[]}
        hasDetailApi={true}
      />
    );

    expect(screen.getByText(/No dispatch accuracy observations available/i)).toBeInTheDocument();
  });
});
