import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { DatabasePreviewSection } from '../modules/settings/components/DatabasePreviewSection';

// Mock auth store
vi.mock('../store/auth', () => ({
  useAuthStore: (selector: any) =>
    selector({
      token: 'fake_admin_token',
      user: { id: 'admin-1', username: 'admin', is_superuser: true, roles: ['Administrator'] },
    }),
}));

// Mock env
vi.mock('../config/env', () => ({
  env: {
    VITE_API_BASE_URL: 'http://localhost:8010/fleet-api/v1',
  },
}));

describe('DatabasePreviewSection Component Tests', () => {
  const mockSchemaData = {
    database_name: 'fleet_control_tower_db',
    schema_name: 'public',
    table_count: 2,
    column_count: 5,
    primary_key_count: 2,
    foreign_key_count: 1,
    generated_at: new Date().toISOString(),
    tables: [
      {
        table_name: 'customers',
        table_schema: 'public',
        columns: [
          {
            name: 'id',
            data_type: 'uuid',
            is_nullable: false,
            is_primary_key: true,
            is_foreign_key: false,
          },
          {
            name: 'name',
            data_type: 'character varying',
            is_nullable: false,
            is_primary_key: false,
            is_foreign_key: false,
          },
        ],
        primary_keys: ['id'],
        foreign_keys: [],
      },
      {
        table_name: 'dispatches',
        table_schema: 'public',
        columns: [
          {
            name: 'id',
            data_type: 'uuid',
            is_nullable: false,
            is_primary_key: true,
            is_foreign_key: false,
          },
          {
            name: 'customer_id',
            data_type: 'uuid',
            is_nullable: false,
            is_primary_key: false,
            is_foreign_key: true,
            foreign_key_target_table: 'customers',
            foreign_key_target_column: 'id',
          },
          {
            name: 'status',
            data_type: 'character varying',
            is_nullable: true,
            is_primary_key: false,
            is_foreign_key: false,
          },
        ],
        primary_keys: ['id'],
        foreign_keys: [
          {
            column_name: 'customer_id',
            target_table: 'customers',
            target_column: 'id',
          },
        ],
      },
    ],
  };

  const mockSqlData = {
    database_name: 'fleet_control_tower_db',
    schema_name: 'public',
    table_count: 2,
    generated_at: new Date().toISOString(),
    sql_script: '-- Fleet Control Tower DDL Export\nCREATE TABLE IF NOT EXISTS public.customers (\n  id uuid NOT NULL,\n  name varchar NOT NULL\n);',
  };

  beforeEach(() => {
    vi.restoreAllMocks();
    global.fetch = vi.fn((url: any) => {
      if (typeof url === 'string' && url.includes('/settings/database-schema/sql-export')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true, data: mockSqlData }),
        } as any);
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ success: true, data: mockSchemaData }),
      } as any);
    });
  });

  it('renders summary badges and table cards with live metadata', async () => {
    render(<DatabasePreviewSection />);

    await waitFor(() => {
      expect(screen.getByText('PostgreSQL Schema Viewer & Live Introspection')).toBeInTheDocument();
      expect(screen.getByText('fleet_control_tower_db')).toBeInTheDocument();
      expect(screen.getByText('customers')).toBeInTheDocument();
      expect(screen.getByText('dispatches')).toBeInTheDocument();
      expect(screen.getByText('customer_id')).toBeInTheDocument();
    });
  });

  it('filters tables dynamically when typing in search input', async () => {
    render(<DatabasePreviewSection />);

    await waitFor(() => {
      expect(screen.getByText('customers')).toBeInTheDocument();
      expect(screen.getByText('dispatches')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Search tables or columns/i);
    fireEvent.change(searchInput, { target: { value: 'dispatches' } });

    expect(screen.getByText('dispatches')).toBeInTheDocument();
    expect(screen.queryByText('customers')).not.toBeInTheDocument();
  });

  it('switches to SQL DDL Export tab and displays read-only SQL script', async () => {
    render(<DatabasePreviewSection />);

    await waitFor(() => {
      expect(screen.getByText('Schema Viewer')).toBeInTheDocument();
    });

    const sqlTabBtn = screen.getByText('SQL DDL Export');
    fireEvent.click(sqlTabBtn);

    await waitFor(() => {
      expect(screen.getByText('Read-Only PostgreSQL Schema DDL')).toBeInTheDocument();
      expect(screen.getByText(/CREATE TABLE IF NOT EXISTS public.customers/i)).toBeInTheDocument();
      expect(screen.getByText('Copy SQL')).toBeInTheDocument();
      expect(screen.getByText('Download .sql')).toBeInTheDocument();
    });
  });
});
