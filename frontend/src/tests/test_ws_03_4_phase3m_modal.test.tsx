import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { DASDetailModal } from '../modules/operational_dashboard/components/DASDetailModal';

describe('WS-03.4 Phase 3M — DASDetailModal Accessibility & Trigger Flow', () => {
  const mockSummary = {
    total_dispatches: 3532,
    accurate_dispatches: 2232,
    das_score: 63.2,
    target_sla: 90.0,
    variance: -26.8,
    operational_status: 'CRITICAL',
  };

  const mockBuckets = {
    within_20m_count: 2232,
    within_20m_pct: 63.2,
    moderate_20_40m_count: 674,
    moderate_20_40m_pct: 19.1,
    critical_above_40m_count: 626,
    critical_above_40m_pct: 17.7,
  };

  it('1. Does not render when isOpen is false', () => {
    render(
      <DASDetailModal
        isOpen={false}
        onClose={vi.fn()}
        summary={mockSummary}
        buckets={mockBuckets}
      />
    );
    expect(screen.queryByText('DISPATCH ACCURACY DETAILS')).toBeNull();
  });

  it('2. Renders summary metrics directly from DTO without frontend calculation when isOpen is true', () => {
    render(
      <DASDetailModal
        isOpen={true}
        onClose={vi.fn()}
        summary={mockSummary}
        buckets={mockBuckets}
        hasDetailApi={false}
      />
    );

    expect(screen.getByText('DISPATCH ACCURACY DETAILS')).toBeDefined();
    expect(screen.getByText('CRITICAL')).toBeDefined();
    expect(screen.getAllByText('63.2%').length).toBeGreaterThan(0);
    expect(screen.getByText('3,532')).toBeDefined();
    expect(screen.getByText('Backend Detail API Contract Required')).toBeDefined();
  });

  it('3. Triggers onClose callback when Close button is clicked', () => {
    const handleClose = vi.fn();
    render(
      <DASDetailModal
        isOpen={true}
        onClose={handleClose}
        summary={mockSummary}
        buckets={mockBuckets}
      />
    );

    const closeButtons = screen.getAllByRole('button', { name: /close/i });
    fireEvent.click(closeButtons[0]);

    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('4. Renders honest empty state when summary has NO_OBSERVATIONS (0 dispatches)', () => {
    const emptySummary = {
      total_dispatches: 0,
      accurate_dispatches: 0,
      das_score: null,
      target_sla: 90.0,
      variance: null,
      operational_status: 'NEUTRAL',
    };

    render(
      <DASDetailModal
        isOpen={true}
        onClose={vi.fn()}
        summary={emptySummary}
        buckets={null}
      />
    );

    expect(screen.getByText('No dispatch accuracy observations available for this filter scope.')).toBeDefined();
  });
});
