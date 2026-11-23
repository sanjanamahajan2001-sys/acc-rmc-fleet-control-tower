import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ExplorerGrid } from '../components/ExplorerGrid';
import { IntegrityDashboard } from '../components/IntegrityDashboard';
import { EntityDetailDrawer } from '../components/EntityDetailDrawer';
import { useERPExplorerStore } from '../stores';

vi.mock('../../api', () => ({
  erpApiClient: {
    getExplorerData: vi.fn().mockResolvedValue({
      items: [
        {
          id: 'test-1',
          dispatch_number: 'SYNTH-TCK-TRIP-1',
          dispatch_date: '2025-06-15',
          status: 'COMPLETED',
        },
      ],
      total_records: 1,
      page: 1,
      page_size: 20,
      total_pages: 1,
      has_next: false,
      has_previous: false,
    }),
    listJobs: vi.fn().mockResolvedValue({ items: [] }),
    getAuditLogs: vi.fn().mockResolvedValue({ items: [] }),
  },
}));

describe('WS1.8 Imported Data Explorer & Audit Center Test Suite', () => {
  it('renders IntegrityDashboard with 100% integrity score', () => {
    render(<IntegrityDashboard />);
    expect(screen.getByText(/Database Integrity & Health Center/i)).toBeInTheDocument();
    expect(screen.getByText(/Integrity Score: 100%/i)).toBeInTheDocument();
  });

  it('renders ExplorerGrid entity tabs and data grid table', async () => {
    render(<ExplorerGrid />);
    expect(screen.getByText(/Dispatches/i)).toBeInTheDocument();
    expect(screen.getByText(/Tickets/i)).toBeInTheDocument();
    expect(screen.getByText(/Plants/i)).toBeInTheDocument();
  });

  it('opens EntityDetailDrawer when a record is selected', async () => {
    useERPExplorerStore.setState({
      selectedItem: { id: 'test-uuid-123', dispatch_number: 'SYNTH-TCK-TRIP-1', is_synthetic: true },
      drawerOpen: true,
      activeEntity: 'dispatches',
    });

    render(<EntityDetailDrawer />);
    expect(screen.getByText(/dispatches Record Inspection/i)).toBeInTheDocument();
    expect(screen.getByText(/Synthetic Operational Identifier Tagged/i)).toBeInTheDocument();
  });
});
