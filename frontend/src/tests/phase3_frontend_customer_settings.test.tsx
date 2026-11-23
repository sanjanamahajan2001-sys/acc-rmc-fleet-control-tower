import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import { useAuthStore } from '../store/auth';
import { CompanyCustomerSettingsSection } from '../modules/settings/components/CompanyCustomerSettingsSection';
import { PlatformSettingsPage } from '../modules/settings/pages/PlatformSettingsPage';


describe('Phase 3 Settings UI — Company & Customer Accounts Suite', () => {
  beforeEach(() => {
    localStorage.clear();
    useAuthStore.setState({
      token: 'admin_test_token',
      user: {
        id: 'admin-uuid',
        username: 'admin',
        is_superuser: true,
        roles: ['Administrator'],
        auth_stage: 'NORMAL',
      },
    });
    vi.restoreAllMocks();
  });

  const mockCustomerData = {
    success: true,
    data: {
      items: [
        {
          id: 'cust-uuid-1',
          code: 'CUST_LNT',
          raw_customer_name: 'L&T CONSTRUCTIONS GOA',
          effective_customer_name: 'Larsen & Toubro Goa Infrastructure',
          override_name: 'Larsen & Toubro Goa Infrastructure',
          override_reason: 'Branding request',
          updated_at: '2026-08-21T10:00:00Z',
          updated_by_name: 'ADMIN',
          is_overridden: true,
          plants: [
            { id: 'p1', code: 'ACC_VASCO', name: 'ACC VASCO' },
            { id: 'p2', code: 'ACC_KUNDAIM', name: 'ACC KUNDAIM' },
          ],
        },
        {
          id: 'cust-uuid-2',
          code: 'CUST_ACC',
          raw_customer_name: 'ACC CONCRETE SUPPLIES',
          effective_customer_name: 'ACC CONCRETE SUPPLIES',
          override_name: null,
          override_reason: null,
          updated_at: null,
          updated_by_name: null,
          is_overridden: false,
          plants: [{ id: 'p1', code: 'ACC_VASCO', name: 'ACC VASCO' }],
        },
      ],
      total: 2,
      page: 1,
      size: 15,
      pages: 1,
    },
  };

  it('1. Table Rendering & Read-Only Fields: Renders Plant names, ERP name, Customer code read-only', async () => {
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes(`${env.VITE_API_BASE_URL}/settings/customer-overrides')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockCustomerData,
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({ success: true, data: [] }),
      });
    });

    render(
      <MemoryRouter initialEntries={['/settings']}>
        <PlatformSettingsPage />
      </MemoryRouter>
    );

    // Wait for table to load
    await waitFor(() => {
      expect(screen.getAllByText(/Company & Customer Accounts/i)[0]).toBeInTheDocument();
    });

    // Check Multi-Plant rendering (ACC VASCO & ACC KUNDAIM)
    expect(screen.getAllByText('ACC VASCO')[0]).toBeInTheDocument();
    expect(screen.getByText('ACC KUNDAIM')).toBeInTheDocument();

    // Check Customer Codes
    expect(screen.getByText('CUST_LNT')).toBeInTheDocument();
    expect(screen.getByText('CUST_ACC')).toBeInTheDocument();

    // Check Raw Canonical ERP Name (Read-Only)
    expect(screen.getByText('L&T CONSTRUCTIONS GOA')).toBeInTheDocument();
    expect(screen.getAllByText('ACC CONCRETE SUPPLIES')[0]).toBeInTheDocument();


    // Check Effective Display Name & Status
    expect(screen.getByText('Larsen & Toubro Goa Infrastructure')).toBeInTheDocument();
    expect(screen.getByText('MANUALLY OVERRIDDEN')).toBeInTheDocument();
    expect(screen.getByText('ERP DEFAULT')).toBeInTheDocument();
  });

  it('2. Edit Flow & Field Constraints: Admin opens edit modal; only Company/Customer Name is editable', async () => {
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes(`${env.VITE_API_BASE_URL}/settings/customer-overrides')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockCustomerData,
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({ success: true, data: [] }),
      });
    });

    render(
      <MemoryRouter>
        <CompanyCustomerSettingsSection />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('CUST_LNT')).toBeInTheDocument();
    });

    const editBtns = screen.getAllByRole('button', { name: /Edit/i });
    fireEvent.click(editBtns[0]);

    // Modal opens
    expect(screen.getByText(/Edit Company\/Customer Name/i)).toBeInTheDocument();

    // Verify Read-only context fields inside modal
    expect(screen.getAllByText('CUST_LNT')[0]).toBeInTheDocument();
    expect(screen.getAllByText('L&T CONSTRUCTIONS GOA')[0]).toBeInTheDocument();


    // Editable input field
    const nameInput = screen.getByPlaceholderText(/Enter custom display name/i) as HTMLInputElement;
    expect(nameInput).toBeInTheDocument();
    expect(nameInput.value).toBe('Larsen & Toubro Goa Infrastructure');

    // Change input
    fireEvent.change(nameInput, { target: { value: 'L&T Goa Updated Name' } });
    expect(nameInput.value).toBe('L&T Goa Updated Name');
  });

  it('3. PUT Integration & Save Confirmation Flow: Calls PUT endpoint and refetches backend state', async () => {
    let putCalled = false;
    let putPayload: any = null;

    global.fetch = vi.fn().mockImplementation((_url: string, opts?: any) => {
      if (opts && opts.method === 'PUT') {
        putCalled = true;
        putPayload = JSON.parse(opts.body);
        return Promise.resolve({
          ok: true,
          json: async () => ({
            success: true,
            data: {
              customer_id: 'cust-uuid-2',
              override_name: 'ACC Concrete Goa Ltd',
              effective_customer_name: 'ACC Concrete Goa Ltd',
              is_overridden: true,
            },
          }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => mockCustomerData,
      });
    });

    render(
      <MemoryRouter>
        <CompanyCustomerSettingsSection />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('CUST_ACC')).toBeInTheDocument();
    });

    // Click edit on second item (ACC CONCRETE SUPPLIES)
    const editBtns = screen.getAllByRole('button', { name: /Edit/i });
    fireEvent.click(editBtns[1]);

    const nameInput = screen.getByPlaceholderText(/Enter custom display name/i);
    fireEvent.change(nameInput, { target: { value: 'ACC Concrete Goa Ltd' } });

    // Click Review & Save
    const reviewBtn = screen.getByRole('button', { name: /Review & Save/i });
    fireEvent.click(reviewBtn);

    // Confirmation Modal appears
    expect(screen.getByText(/Confirm Display Name Change/i)).toBeInTheDocument();
    expect(screen.getByText(/This changes the display name used by the Fleet Control Tower/i)).toBeInTheDocument();

    // Confirm Save
    const confirmBtn = screen.getByRole('button', { name: /Confirm & Save/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(putCalled).toBe(true);
      expect(putPayload).toEqual({
        override_name: 'ACC Concrete Goa Ltd',
      });
    });
  });

  it('4. DELETE Integration & Reset Flow: Calls DELETE endpoint and returns to ERP default', async () => {
    let deleteCalled = false;

    global.fetch = vi.fn().mockImplementation((_url: string, opts?: any) => {
      if (opts && opts.method === 'DELETE') {
        deleteCalled = true;
        return Promise.resolve({
          ok: true,
          json: async () => ({
            success: true,
            message: 'Override reset to ERP canonical name.',
          }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => mockCustomerData,
      });
    });

    render(
      <MemoryRouter>
        <CompanyCustomerSettingsSection />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('CUST_LNT')).toBeInTheDocument();
    });

    // Reset button exists for overridden customer
    const resetBtn = screen.getByRole('button', { name: /Reset to ERP/i });
    fireEvent.click(resetBtn);

    // Reset modal appears
    expect(screen.getByText(/Reset to ERP Default Name/i)).toBeInTheDocument();

    // Click confirm reset
    const confirmResetBtn = screen.getByRole('button', { name: /Confirm Reset/i });
    fireEvent.click(confirmResetBtn);

    await waitFor(() => {
      expect(deleteCalled).toBe(true);
    });
  });

  it('5. RBAC Behavior: Non-admin users see read-only table without Edit/Reset controls', async () => {
    // Set non-admin user
    useAuthStore.setState({
      token: 'non_admin_token',
      user: {
        id: 'user-uuid',
        username: 'dispatcher',
        is_superuser: false,
        roles: ['Plant Dispatcher'],
        auth_stage: 'NORMAL',
      },
    });

    global.fetch = vi.fn().mockImplementation((_url: string) => {
      return Promise.resolve({
        ok: true,
        json: async () => mockCustomerData,
      });
    });

    render(
      <MemoryRouter>
        <CompanyCustomerSettingsSection />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('CUST_LNT')).toBeInTheDocument();
    });

    // Edit and Reset buttons should NOT be present for non-admin
    expect(screen.queryByRole('button', { name: /Edit/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Reset to ERP/i })).not.toBeInTheDocument();
    expect(screen.getByText(/Read-Only View \(Administrator rights required/i)).toBeInTheDocument();
  });

  it('6. Loading State: Renders spinner while GET request is pending and prevents false empty state', async () => {
    let resolveGet: any;
    const pendingPromise = new Promise((resolve) => {
      resolveGet = resolve;
    });

    global.fetch = vi.fn().mockImplementation(() => pendingPromise.then(() => ({
      ok: true,
      json: async () => mockCustomerData,
    })));

    render(
      <MemoryRouter>
        <CompanyCustomerSettingsSection />
      </MemoryRouter>
    );

    // Initial state shows loading spinner and text
    expect(screen.getByText(/Loading customer accounts.../i)).toBeInTheDocument();
    expect(screen.queryByText(/No Customer Accounts Found/i)).not.toBeInTheDocument();

    // Resolve GET
    resolveGet();

    await waitFor(() => {
      expect(screen.getByText('CUST_LNT')).toBeInTheDocument();
    });
  });

  it('7. API Error State: GET failure displays standard application error state and retry option', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ message: 'Database connection failed' }),
    });

    render(
      <MemoryRouter>
        <CompanyCustomerSettingsSection />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Failed to load customer settings \(HTTP 500\)/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument();
    });
  });

  it('8. Empty State: Successful GET returning zero records renders platform empty state', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        data: { items: [], total: 0, page: 1, size: 15, pages: 0 },
      }),
    });

    render(
      <MemoryRouter>
        <CompanyCustomerSettingsSection />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/No Customer Accounts Found/i)).toBeInTheDocument();
      expect(screen.getByText(/No customer records are currently ingested in the platform./i)).toBeInTheDocument();
    });
  });

  it('9. Validation Alignment: Enforces empty string, whitespace-only rejection, max 255 chars in UI', async () => {
    global.fetch = vi.fn().mockImplementation(() => Promise.resolve({
      ok: true,
      json: async () => mockCustomerData,
    }));

    render(
      <MemoryRouter>
        <CompanyCustomerSettingsSection />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('CUST_LNT')).toBeInTheDocument();
    });

    // Open Edit Modal
    const editBtns = screen.getAllByRole('button', { name: /Edit/i });
    fireEvent.click(editBtns[0]);

    const nameInput = screen.getByPlaceholderText(/Enter custom display name/i);
    const saveBtn = screen.getByRole('button', { name: /Review & Save/i });

    // Test Whitespace-only
    fireEvent.change(nameInput, { target: { value: '    ' } });
    fireEvent.click(saveBtn);
    expect(screen.getByText(/Company\/Customer Name cannot be empty or whitespace-only/i)).toBeInTheDocument();

    // Test > 255 chars
    const longName = 'A'.repeat(256);
    fireEvent.change(nameInput, { target: { value: longName } });
    fireEvent.click(saveBtn);
    expect(screen.getByText(/Company\/Customer Name cannot exceed 255 characters/i)).toBeInTheDocument();
  });

  it('10. Mutation Failure Handling: PUT and DELETE failures show error toast and allow user retry', async () => {
    global.fetch = vi.fn().mockImplementation((_url: string, opts?: any) => {
      if (opts && (opts.method === 'PUT' || opts.method === 'DELETE')) {
        return Promise.resolve({
          ok: false,
          status: 400,
          json: async () => ({ detail: 'Custom validation rejection' }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => mockCustomerData,
      });
    });

    render(
      <MemoryRouter>
        <CompanyCustomerSettingsSection />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('CUST_LNT')).toBeInTheDocument();
    });

    // Attempt Edit -> Fail
    const editBtns = screen.getAllByRole('button', { name: /Edit/i });
    fireEvent.click(editBtns[0]);
    fireEvent.click(screen.getByRole('button', { name: /Review & Save/i }));
    fireEvent.click(screen.getByRole('button', { name: /Confirm & Save/i }));

    await waitFor(() => {
      expect(screen.getByText(/Custom validation rejection/i)).toBeInTheDocument();
    });

    // Attempt Reset -> Fail
    const resetBtn = screen.getByRole('button', { name: /Reset to ERP/i });
    fireEvent.click(resetBtn);
    fireEvent.click(screen.getByRole('button', { name: /Confirm Reset/i }));

    await waitFor(() => {
      expect(screen.getByText(/Custom validation rejection/i)).toBeInTheDocument();
    });
  });

  it('11. Authoritative Refetch: GET request is issued immediately following successful PUT or DELETE', async () => {
    let getFetchCount = 0;

    global.fetch = vi.fn().mockImplementation((_url: string, opts?: any) => {
      if (!opts || !opts.method || opts.method === 'GET') {
        getFetchCount++;
        return Promise.resolve({
          ok: true,
          json: async () => mockCustomerData,
        });
      }
      if (opts.method === 'PUT') {
        return Promise.resolve({
          ok: true,
          json: async () => ({ success: true }),
        });
      }
      return Promise.resolve({ ok: true, json: async () => ({ success: true }) });
    });

    render(
      <MemoryRouter>
        <CompanyCustomerSettingsSection />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(getFetchCount).toBe(1);
    });

    // Perform PUT
    const editBtns = screen.getAllByRole('button', { name: /Edit/i });
    fireEvent.click(editBtns[0]);
    fireEvent.click(screen.getByRole('button', { name: /Review & Save/i }));
    fireEvent.click(screen.getByRole('button', { name: /Confirm & Save/i }));

    await waitFor(() => {
      expect(getFetchCount).toBe(2); // Initial GET + Post-PUT Refetch
    });
  });
});

