import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { OperationalCostExposureSection, OperationalCostExposureData } from '../components/OperationalCostExposureSection';

vi.mock('../../../store/auth', () => ({
  useAuthStore: () => ({ user: { username: 'Admin Operator' }, token: 'mock-token' }),
}));

vi.mock('../../../store/app', () => ({
  useAppStore: () => ({ isSidebarCollapsed: false, toggleSidebar: vi.fn() }),
}));

describe('WS-10 Section 6 Operational ↔ Predictive Intelligence UI Synchronization Suite', () => {

  const mockAvailableData: OperationalCostExposureData = {
    summary: {
      realized_cost_exposure_inr: 2192830,
      predicted_cost_exposure_inr: 323230,
      holding_penalty_cost_inr: 1053550,
      retention_sla_penalty_inr: 507150,
      idle_fuel_waste_inr: 632130,
      high_cost_operations_count: 1730,
    },
    high_cost_operations: {
      items: [
        {
          dispatch_id: 'd1',
          dispatch_code: 'SYNTH-TCK-TRIP-2302',
          plant_code: 'ACC_DHARGA',
          customer_code: 'CUST_KESHVA_KIYAAN',
          vehicle_code: 'GA11T0840',
          holding_penalty_mins: 482,
          retention_penalty_mins: 0,
          total_exposure_inr: 19490,
          risk_level: 'Critical',
        },
      ],
      page: 1,
      page_size: 10,
      total_items: 1730,
      total_pages: 173,
    },
    plant_cost_risk: [
      {
        plant_code: 'ACC_DHARGA',
        plant_name: 'ACC DHARGA',
        dispatches_count: 978,
        total_exposure_inr: 751500,
        exposure_percentage: 34.3,
      },
    ],
    customer_cost_risk: [
      {
        customer_code: 'DEFAULT_CUSTOMER',
        customer_name: 'DEFAULT CUSTOMER',
        delivered_trips: 2066,
        total_exposure_inr: 1047970,
        exposure_percentage: 47.8,
      },
    ],
    provenance: {
      is_model_configured: true,
      prediction_status: 'AVAILABLE',
      model_name: 'delay_regressor',
      model_version: 'v1.1.0-promoted-fixture',
      prediction_snapshot_id: 'SNAP-TELEMETRY-12345',
      prediction_timestamp: '2026-08-19T12:00:00Z',
      confidence_score: 0.94,
      notes: 'Authoritative Production Inference Engine active (4/4 Promoted Families, 12345 active snapshots).',
    },
    calculation_status: 'SUCCESS',
    prediction_status: 'AVAILABLE',
    calculation_notes: 'Authoritative Phase 4 financial calculation reused successfully across ₹2,192,830.00 total realized exposure.',
  };

  const mockNotConfiguredData: OperationalCostExposureData = {
    ...mockAvailableData,
    summary: {
      ...mockAvailableData.summary,
      predicted_cost_exposure_inr: null,
    },
    provenance: {
      is_model_configured: false,
      prediction_status: 'NOT_CONFIGURED',
      model_name: null,
      model_version: null,
      prediction_snapshot_id: null,
      prediction_timestamp: null,
      confidence_score: null,
      notes: 'Phase 6 Production Inference Engine is not authoritative in current repository environment.',
    },
    prediction_status: 'NOT_CONFIGURED',
  };

  it('UI-01: Renders AUTHORITATIVE state correctly when prediction_status is AVAILABLE', () => {
    render(
      <MemoryRouter>
        <OperationalCostExposureSection data={mockAvailableData} />
      </MemoryRouter>
    );

    expect(screen.getByText('Authoritative Production Inference Provenance')).toBeInTheDocument();
    expect(screen.getByText('PREDICTIVE INTELLIGENCE | AUTHORITATIVE')).toBeInTheDocument();
    expect(screen.getByText(/12345 active snapshots/i)).toBeInTheDocument();
  });

  it('UI-02: Renders safe NOT_CONFIGURED state when zero promoted models exist', () => {
    render(
      <MemoryRouter>
        <OperationalCostExposureSection data={mockNotConfiguredData} />
      </MemoryRouter>
    );

    expect(screen.getByText('NOT CONFIGURED')).toBeInTheDocument();
    expect(screen.getByText('Status: NOT_CONFIGURED')).toBeInTheDocument();
    expect(screen.getByText(/not authoritative in current repository environment/i)).toBeInTheDocument();
  });

  it('UI-03: Renders predicted cost exposure formatted in INR', () => {
    render(
      <MemoryRouter>
        <OperationalCostExposureSection data={mockAvailableData} />
      </MemoryRouter>
    );

    expect(screen.getByText('₹3,23,230')).toBeInTheDocument();
  });

  it('UI-04: Keeps Realized and Predicted Cost Exposure cards separate and distinct', () => {
    render(
      <MemoryRouter>
        <OperationalCostExposureSection data={mockAvailableData} />
      </MemoryRouter>
    );

    expect(screen.getByText('Realized Cost Exposure')).toBeInTheDocument();
    expect(screen.getByText('Predicted Cost Exposure')).toBeInTheDocument();
    expect(screen.getByText('₹21,92,830')).toBeInTheDocument();
    expect(screen.getByText('₹3,23,230')).toBeInTheDocument();
  });

  it('UI-05: Renders dynamic active snapshot notes from telemetry fixture without hardcoding', () => {
    render(
      <MemoryRouter>
        <OperationalCostExposureSection data={mockAvailableData} />
      </MemoryRouter>
    );

    expect(screen.getByText(/12345 active snapshots/i)).toBeInTheDocument();
  });

  it('UI-07: Telemetry API failure produces safe degraded NOT_CONFIGURED state without falsely displaying AUTHORITATIVE', () => {
    render(
      <MemoryRouter>
        <OperationalCostExposureSection data={mockNotConfiguredData} />
      </MemoryRouter>
    );

    expect(screen.queryByText('PREDICTIVE INTELLIGENCE | AUTHORITATIVE')).not.toBeInTheDocument();
    expect(screen.getByText('Status: NOT_CONFIGURED')).toBeInTheDocument();
  });

  it('UI-08: Renders dynamic model version tag matching telemetry fixture', () => {
    render(
      <MemoryRouter>
        <OperationalCostExposureSection data={mockAvailableData} />
      </MemoryRouter>
    );

    expect(screen.getByText('v1.1.0-promoted-fixture')).toBeInTheDocument();
  });
});
