import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { DispatchOptimizationDashboardPage } from '../modules/operational_dashboard/pages/DispatchOptimizationDashboardPage';

describe('WS-06.10 UX Presentation Cleanup Tests', () => {
  it('1. Renders clean operator-facing UI with ZERO internal phase or DTO badges', async () => {
    const { container } = render(
      <MemoryRouter>
        <DispatchOptimizationDashboardPage />
      </MemoryRouter>
    );
    const pageText = container.textContent || '';

    // Verify zero internal phase / engine / DTO / enum badges exist
    expect(pageText).not.toContain('Phase 5.7 Audit Boundary');
    expect(pageText).not.toContain('WS-06.');
    expect(pageText).not.toContain('CandidateScenarioDTO');
    expect(pageText).not.toContain('RecommendationReasonDTO');
    expect(pageText).not.toContain('Solver Engine');
    expect(pageText).not.toContain('OPTIMAL_HISTORICAL_SPACING');
    expect(pageText).not.toContain('PLANT_HOLDING_BOTTLENECK_REDUCTION');
    expect(pageText).not.toContain('v1.0.0-PROPOSED');

    // Verify clean operator-facing headings exist
    expect(screen.getByText('Dispatch Optimization Control Center')).toBeDefined();
    expect(screen.getByText('Optimization Decision')).toBeDefined();
  });
});
