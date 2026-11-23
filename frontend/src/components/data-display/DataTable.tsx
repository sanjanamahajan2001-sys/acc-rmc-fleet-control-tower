import React from 'react';

export interface Column<T> {
  header: string;
  accessorKey?: keyof T;
  cell?: (row: T) => React.ReactNode;
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  emptyMessage?: string;
}

export function DataTable<T extends { id?: string | number }>({
  columns,
  data,
  emptyMessage = 'No records found',
}: DataTableProps<T>) {
  return (
    <div style={{ overflowX: 'auto', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 6 }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, textAlign: 'left' }}>
        <thead>
          <tr style={{ backgroundColor: '#1E293B', borderBottom: '1px solid rgba(255,255,255,0.08)', color: '#94A3B8' }}>
            {columns.map((col, idx) => (
              <th key={idx} style={{ padding: '10px 14px', fontWeight: 600 }}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} style={{ padding: 24, textAlign: 'center', color: '#64748B' }}>
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, rowIdx) => (
              <tr
                key={row.id ?? rowIdx}
                style={{
                  borderBottom: '1px solid rgba(255,255,255,0.04)',
                  backgroundColor: rowIdx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)',
                }}
              >
                {columns.map((col, colIdx) => (
                  <td key={colIdx} style={{ padding: '10px 14px', color: '#F8FAFC' }}>
                    {col.cell ? col.cell(row) : col.accessorKey ? String(row[col.accessorKey] ?? '') : null}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
