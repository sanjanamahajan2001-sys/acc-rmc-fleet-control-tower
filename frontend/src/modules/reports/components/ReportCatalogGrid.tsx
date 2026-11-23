import React, { useState } from 'react';
import { ReportDefinitionDTO } from '../types/report.types';
import { ReportCatalogCard } from './ReportCatalogCard';
import { TextInput } from '../../../components/inputs/TextInput';
import { Search } from 'lucide-react';

export interface ReportCatalogGridProps {
  catalog: ReportDefinitionDTO[];
  onExportSelect: (report: ReportDefinitionDTO) => void;
}

export const ReportCatalogGrid: React.FC<ReportCatalogGridProps> = ({ catalog = [], onExportSelect }) => {
  const [searchQuery, setSearchQuery] = useState<string>('');

  const safeCatalog = Array.isArray(catalog) ? catalog : [];
  const filteredCatalog = safeCatalog.filter((item) => {
    if (item.report_id === 'erp_data_explorer') return false;
    const q = searchQuery.toLowerCase().trim();
    if (!q) return true;
    return (
      item.title.toLowerCase().includes(q) ||
      item.description.toLowerCase().includes(q) ||
      item.report_id.toLowerCase().includes(q) ||
      (item.category && item.category.toLowerCase().includes(q))
    );
  });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
        <div className="relative w-full max-w-sm">
          <TextInput
            placeholder="Search report catalog..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-white border-slate-200 text-slate-900 pr-9"
            data-testid="catalog-search-input"
          />
          <Search
            size={16}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
          />
        </div>
        <div className="text-xs font-medium text-slate-500">
          Showing <strong className="text-slate-900 font-bold">{filteredCatalog.length}</strong> of <strong className="text-slate-900 font-bold">{catalog.length}</strong> reports
        </div>
      </div>

      {filteredCatalog.length === 0 ? (
        <div
          className="p-10 text-center bg-white rounded-lg border border-dashed border-slate-200 text-slate-500 text-sm font-medium"
          data-testid="catalog-empty-state"
        >
          No reports match your search criteria.
        </div>
      ) : (
        <div
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
          data-testid="catalog-grid-container"
        >
          {filteredCatalog.map((report) => (
            <ReportCatalogCard key={report.report_id} report={report} onExportSelect={onExportSelect} />
          ))}
        </div>
      )}
    </div>
  );
};
