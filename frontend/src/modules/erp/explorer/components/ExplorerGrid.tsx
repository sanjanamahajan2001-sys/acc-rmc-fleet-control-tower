import { formatDisplayDate, formatDisplayDateTime } from '../../../../utils/date';
import React from 'react';
import { Eye, Download, Search, Filter } from 'lucide-react';
import { useERPExplorerStore, ExplorerEntityType, SyntheticFilterOption } from '../stores';

export const ExplorerGrid: React.FC = () => {
  const {
    activeEntity,
    setActiveEntity,
    items,
    totalRecords,
    currentPage,
    pageSize,
    loading,
    searchQuery,
    setSearchQuery,
    syntheticFilter,
    setSyntheticFilter,
    fetchEntityData,
    selectItemForInspection,
  } = useERPExplorerStore();

  const entities: { id: ExplorerEntityType; label: string }[] = [
    { id: 'dispatches', label: 'Dispatches' },
    { id: 'tickets', label: 'Tickets' },
    { id: 'plants', label: 'Plants' },
    { id: 'vehicles', label: 'Vehicles' },
    { id: 'customers', label: 'Customers' },
    { id: 'drivers', label: 'Drivers' },
    { id: 'orders', label: 'Orders' },
    { id: 'sites', label: 'Sites' },
    { id: 'trips', label: 'Trips' },
    { id: 'invoices', label: 'Invoices' },
    { id: 'telemetry' as any, label: 'Telemetry Stream' },
  ];

  const [showTechnicalCols, setShowTechnicalCols] = React.useState(false);

  // Technical UUID columns to hide when showTechnicalCols is false
  const techUuidCols = new Set([
    'id',
    'ticket_id',
    'vehicle_id',
    'driver_id',
    'plant_id',
    'customer_id',
    'order_id',
    'dispatch_id',
    'created_at',
    'updated_at',
    'deleted_at',
    'is_deleted',
    'version_id',
    'created_by',
    'updated_by',
    'import_batch_id',
    'checksum',
    'parser_version',
    'source_system',
    'excel_row',
    'telemetry_matched',
    'telemetry_match_score',
    'source_lineage',
  ]);

  // Filtering logic for search and synthetic records
  const filteredItems = items.filter((item) => {
    // Synthetic filter
    const isSynthetic =
      item.ticket_number?.startsWith('SYNTH-') ||
      item.dispatch_number?.startsWith('SYNTH-') ||
      item.is_synthetic;

    if (syntheticFilter === 'REAL_ONLY' && isSynthetic) return false;
    if (syntheticFilter === 'SYNTHETIC_ONLY' && !isSynthetic) return false;

    // Search query filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const stringified = JSON.stringify(item).toLowerCase();
      return stringified.includes(q);
    }
    return true;
  });

  const getVisibleColumns = (sampleItem: Record<string, any>) => {
    const keys = Object.keys(sampleItem);
    if (showTechnicalCols) return keys;
    return keys.filter((k) => !techUuidCols.has(k));
  };

  const exportToCSV = () => {
    if (filteredItems.length === 0) return;
    const cols = getVisibleColumns(filteredItems[0]);
    const headers = cols.join(',');
    const rows = filteredItems.map((row) =>
      cols
        .map((v) => `"${String(row[v] ?? '').replace(/"/g, '""')}"`)
        .join(',')
    );
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers, ...rows].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `erp_explorer_${activeEntity}_export.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="p-5 rounded-lg border border-slate-200/90 bg-white space-y-4 shadow-xs">
      {/* Entity Selector Tabs */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-thin">
        {entities.map((entity) => (
          <button
            key={entity.id}
            type="button"
            onClick={() => setActiveEntity(entity.id)}
            className={`px-3 py-1.5 rounded-md text-xs font-bold whitespace-nowrap transition-colors border ${
              activeEntity === entity.id
                ? 'bg-blue-700 border-blue-700 text-white shadow-xs'
                : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
            }`}
          >
            {entity.label}
          </button>
        ))}
      </div>

      {/* Control Toolbar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pt-1">
        <div className="flex items-center gap-3 flex-1">
          {/* Search Box */}
          <div className="relative flex-1 max-w-sm">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder={`Search ${activeEntity} (Ticket, Dispatch, Plant)...`}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 rounded-md border border-slate-200 text-xs font-medium focus:outline-none focus:border-blue-600 bg-white text-slate-900 placeholder:text-slate-400"
            />
          </div>

          {/* Synthetic Filter Pill */}
          <div className="flex items-center gap-1 p-0.5 rounded-md border border-slate-200 bg-slate-50 text-xs font-mono font-semibold">
            <Filter className="w-3 h-3 ml-1.5 text-slate-400" />
            <button
              type="button"
              onClick={() => setSyntheticFilter('ALL')}
              className={`px-2 py-0.5 rounded transition-colors text-xs font-sans ${
                syntheticFilter === 'ALL'
                  ? 'bg-white text-slate-900 font-bold border border-slate-200 shadow-2xs'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              All Records
            </button>
            <button
              type="button"
              onClick={() => setSyntheticFilter('REAL_ONLY')}
              className={`px-2 py-0.5 rounded transition-colors text-xs font-sans ${
                syntheticFilter === 'REAL_ONLY'
                  ? 'bg-white text-slate-900 font-bold border border-slate-200 shadow-2xs'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              Real Only
            </button>
            <button
              type="button"
              onClick={() => setSyntheticFilter('SYNTHETIC_ONLY')}
              className={`px-2 py-0.5 rounded transition-colors text-xs font-sans ${
                syntheticFilter === 'SYNTHETIC_ONLY'
                  ? 'bg-white text-slate-900 font-bold border border-slate-200 shadow-2xs'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              Synthetic Only
            </button>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs font-semibold text-slate-600 cursor-pointer">
            <input
              type="checkbox"
              checked={showTechnicalCols}
              onChange={(e) => setShowTechnicalCols(e.target.checked)}
              className="rounded text-blue-700 focus:ring-blue-700 border-slate-300"
            />
            <span>Show Technical UUIDs</span>
          </label>

          <button
            type="button"
            onClick={exportToCSV}
            className="px-3 py-1.5 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-bold flex items-center gap-1.5 transition-colors shadow-xs"
          >
            <Download className="w-3.5 h-3.5" />
            Export CSV
          </button>
        </div>
      </div>

      {/* Main Explorer Data Table */}
      <div className="border border-slate-200 rounded-md overflow-hidden">
        <div className="overflow-x-auto max-h-[500px]">
          <table className="w-full text-left border-collapse font-mono text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-[10px] font-bold uppercase text-slate-500 tracking-wider">
                {filteredItems.length > 0 ? (
                  getVisibleColumns(filteredItems[0]).map((col) => (
                    <th key={col} className="py-2.5 px-3.5 whitespace-nowrap">
                      {col.replace(/_/g, ' ')}
                    </th>
                  ))
                ) : (
                  <th className="py-2.5 px-3.5">Entity Attribute</th>
                )}
                <th className="py-2.5 px-3.5 text-right font-sans">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-800">
              {loading ? (
                <tr>
                  <td colSpan={15} className="py-8 text-center font-bold text-slate-500 font-sans">
                    Loading canonical explorer records...
                  </td>
                </tr>
              ) : filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={15} className="py-8 text-center font-medium text-slate-500 font-sans">
                    No records found matching current query or filters.
                  </td>
                </tr>
              ) : (
                filteredItems.map((row, idx) => (
                  <tr key={row.id || idx} className={`hover:bg-slate-50/80 transition-colors ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}`}>
                    {getVisibleColumns(row).map((key) => {
                      const val = row[key];
                      return (
                        <td key={key} className="py-2.5 px-3.5 whitespace-nowrap font-medium text-slate-800">
                          {key === 'is_generated' ? (
                            val ? (
                              <span className="px-2 py-0.5 rounded border text-[10px] font-bold inline-flex items-center gap-1 bg-amber-50 border-amber-200 text-amber-700" title={row.generation_reason || 'System Generated'}>
                                GENERATED
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded border text-[10px] font-bold inline-flex items-center gap-1 bg-emerald-50 border-emerald-200 text-emerald-700">
                                IMPORTED ERP
                              </span>
                            )
                          ) : key === 'correlation_status' ? (
                            val === 'CORRELATED' ? (
                              <span className="px-2 py-0.5 rounded border text-[10px] font-bold bg-emerald-50 border-emerald-200 text-emerald-700">
                                CORRELATED
                              </span>
                            ) : val === 'MANUAL_REVIEW' ? (
                              <span className="px-2 py-0.5 rounded border text-[10px] font-bold bg-amber-50 border-amber-200 text-amber-700">
                                MANUAL REVIEW
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded border text-[10px] font-bold bg-slate-50 border-slate-200 text-slate-600">
                                {String(val ?? 'PENDING')}
                              </span>
                            )
                          ) : key === 'correlation_score' ? (
                            val && val !== 'Pending' ? (
                              <span className="font-bold text-emerald-700">{val}</span>
                            ) : (
                              <span className="italic text-slate-400">Pending</span>
                            )
                          ) : key === 'generation_reason' ? (
                            <span className="italic text-[11px] text-slate-500">{String(val ?? 'N/A')}</span>
                          ) : key.includes('number') || key.includes('code') || key.includes('name') ? (
                            <span className="font-bold text-blue-700">{String(val ?? '')}</span>
                          ) : key.startsWith('is_synthetic') && val ? (
                            <span className="px-2 py-0.5 rounded border text-[10px] font-bold bg-amber-50 border-amber-200 text-amber-700">SYNTHETIC</span>
                          ) : key.includes('date') || (typeof val === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(val)) ? (
                            formatDisplayDate(val)
                          ) : (key.includes('time') || key.endsWith('_at')) && typeof val === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(val) ? (
                            formatDisplayDateTime(val)
                          ) : (
                            String(val ?? '')
                          )}
                        </td>
                      );
                    })}
                    <td className="py-2.5 px-3.5 text-right font-sans">
                      <button
                        type="button"
                        onClick={() => selectItemForInspection(row)}
                        className="p-1 rounded border border-slate-200 bg-white text-blue-700 hover:bg-blue-50 transition-colors shadow-2xs"
                        title="Inspect Entity Lineage & Payload"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Table Footer Stats */}
        <div className="p-3 border-t border-slate-200 bg-slate-50/50 flex items-center justify-between text-xs font-mono font-medium text-slate-500">
          <span>
            Showing Page <strong className="font-bold text-slate-900">{currentPage}</strong> of{' '}
            <strong className="font-bold text-slate-900">{Math.ceil(totalRecords / pageSize) || 1}</strong> ({totalRecords} total records)
          </span>
          <div className="flex items-center gap-1.5 font-sans">
            <button
              type="button"
              disabled={currentPage <= 1}
              onClick={() => fetchEntityData(activeEntity, currentPage - 1)}
              className="px-2.5 py-1 rounded border border-slate-200 bg-white disabled:opacity-40 hover:bg-slate-50 font-semibold text-slate-700 shadow-2xs transition-colors"
            >
              Previous
            </button>
            <button
              type="button"
              disabled={currentPage >= Math.ceil(totalRecords / pageSize)}
              onClick={() => fetchEntityData(activeEntity, currentPage + 1)}
              className="px-2.5 py-1 rounded border border-slate-200 bg-white disabled:opacity-40 hover:bg-slate-50 font-semibold text-slate-700 shadow-2xs transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
