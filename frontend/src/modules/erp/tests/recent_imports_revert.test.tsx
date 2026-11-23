import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { RecentImports } from '../components/RecentImports';
import { useERPJobsStore } from '../stores';

vi.mock('../../../hooks/usePermissions', () => ({
  usePermissions: () => ({ canEdit: true, role: 'admin' }),
}));

describe('RecentImports Revert & Archive Dataset Suite', () => {
  const mockJobs = [
    {
      id: 'job-1',
      job_number: 'JOB-20261014-001',
      file_name: 'ERP_2026_MAR_APR.xlsx',
      file_type: 'ERP Dispatches',
      status: 'COMPLETED',
      uploaded_by: 'admin',
      is_active_dataset: true,
      is_reset: false,
      dataset_period: '2026-MAR-APR',
      processed_rows: 6834,
      total_rows: 6834,
      error_count: 0,
      completed_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: 'job-2',
      job_number: 'JOB-20250815-001',
      file_name: 'ERP_2025_JUL_AUG.xlsx',
      file_type: 'ERP Dispatches',
      status: 'COMPLETED',
      uploaded_by: 'admin',
      is_active_dataset: false,
      is_reset: true,
      dataset_period: '2025-JUL-AUG',
      processed_rows: 3532,
      total_rows: 3532,
      error_count: 0,
      completed_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ];

  beforeEach(() => {
    useERPJobsStore.setState({
      jobs: mockJobs as any,
      loading: false,
    });
  });

  it('renders Active Dataset by default and shows active jobs count', () => {
    render(<RecentImports onSelectJob={vi.fn()} />);
    expect(screen.getByRole('button', { name: /Active Dataset/i })).toBeInTheDocument();
    expect(screen.getByText('ERP_2026_MAR_APR.xlsx')).toBeInTheDocument();
    expect(screen.queryByText('ERP_2025_JUL_AUG.xlsx')).not.toBeInTheDocument();
  });

  it('switches to Archived tab and displays revert informational banner', () => {
    render(<RecentImports onSelectJob={vi.fn()} />);
    const archivedTab = screen.getByRole('button', { name: /Archived/i });
    fireEvent.click(archivedTab);

    expect(screen.getByText(/Dataset Revert & Resume Mode/i)).toBeInTheDocument();
    expect(screen.getByText('ERP_2025_JUL_AUG.xlsx')).toBeInTheDocument();
  });

  it('renders Revert button for archived job and opens confirmation modal', async () => {
    render(<RecentImports onSelectJob={vi.fn()} />);
    const archivedTab = screen.getByRole('button', { name: /Archived/i });
    fireEvent.click(archivedTab);

    const revertButton = screen.getByRole('button', { name: /Revert/i });
    expect(revertButton).toBeInTheDocument();
    fireEvent.click(revertButton);

    expect(screen.getByText(/Confirm Dataset Revert & Resume/i)).toBeInTheDocument();
    expect(screen.getByText(/Operational Rollback Notice/i)).toBeInTheDocument();
    expect(screen.getAllByText('2025-JUL-AUG').length).toBeGreaterThan(0);
  });

  it('triggers onRevertJob callback when confirmed if callback provided', async () => {
    const onRevertMock = vi.fn();
    render(<RecentImports onSelectJob={vi.fn()} onRevertJob={onRevertMock} />);
    const archivedTab = screen.getByRole('button', { name: /Archived/i });
    fireEvent.click(archivedTab);

    fireEvent.click(screen.getByRole('button', { name: /Revert/i }));
    const confirmButton = screen.getByRole('button', { name: /Confirm Revert & Resume/i });
    fireEvent.click(confirmButton);

    expect(onRevertMock).toHaveBeenCalledWith(expect.objectContaining({
      job_number: 'JOB-20250815-001',
      dataset_period: '2025-JUL-AUG',
    }));
  });
});
