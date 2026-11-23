import React, { useEffect, useState } from 'react';
import { Button } from '../../../components/inputs/Button';
import { useReportsStore } from '../store/reports.store';
import { ReportCatalogGrid } from '../components/ReportCatalogGrid';
import { ReportExecutionHistoryTable } from '../components/ReportExecutionHistoryTable';
import { ReportExportModal } from '../components/ReportExportModal';

import { ReportDefinitionDTO } from '../types/report.types';
import { adaptFilterStateToReportScope } from '../utils/reportScopeAdapter';
import { useDashboardFilters } from '../../site_dashboard/orchestration/DashboardFilterProvider';
import { DashboardSyncProvider } from '../../site_dashboard/orchestration/DashboardSyncProvider';
import { GlobalDashboardFilterBar } from '../../site_dashboard/components/GlobalDashboardFilterBar';
import { SyncStatusHeaderBadge } from '../../site_dashboard/components/SyncStatusHeaderBadge';
import { RefreshCw, ShieldCheck } from 'lucide-react';
import { IconExcelSpreadsheet } from '../../../components/icons/LinealColorIcons';

export const ReportsManagementPage: React.FC = () => {
  const { catalog, isCatalogLoading, catalogError, loadCatalog } = useReportsStore();
  const { filters } = useDashboardFilters();

  const [selectedReport, setSelectedReport] = useState<ReportDefinitionDTO | null>(null);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

  useEffect(() => {
    loadCatalog();
  }, [loadCatalog]);

  const handleExportSelect = (report: ReportDefinitionDTO) => {
    setSelectedReport(report);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedReport(null);
  };

  const currentScope = adaptFilterStateToReportScope(filters);

  return (
    <DashboardSyncProvider onRefreshNeeded={loadCatalog}>
      <div className="min-h-screen bg-slate-50 p-4 md:p-5 space-y-6 text-slate-800">
        {/* Workspace Header Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-lg bg-white shadow-xs border border-slate-200/90">
          <div className="flex items-center gap-3">
            <IconExcelSpreadsheet className="w-7 h-7 shrink-0" />
            <div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900">
                Reports &amp; Export Management
              </h1>
              <p className="text-xs font-medium text-slate-500">
                <span>Authoritative Report Catalog</span> — Browse, generate, and export certified operational reports for Fleet Control Tower
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={() => loadCatalog()}
              disabled={isCatalogLoading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white border border-slate-200 text-slate-700 text-xs font-semibold hover:bg-slate-50 transition-colors disabled:opacity-50"
              data-testid="refresh-catalog-btn"
            >
              <RefreshCw size={13} className={isCatalogLoading ? 'animate-spin' : ''} />
              Refresh Catalog
            </button>
            <SyncStatusHeaderBadge />
          </div>
        </div>

        {/* Security & Download Advisory Banner */}
        <div className="bg-blue-50/80 border border-blue-200/80 rounded-lg p-3 text-xs text-blue-900 flex items-start gap-3">
          <ShieldCheck className="w-4 h-4 text-blue-600 mt-0.5 shrink-0" />
          <div className="flex-1">
            <span className="font-bold text-blue-950">Report Download &amp; Browser Advisory:</span>{' '}
            <span className="text-blue-800">
              When accessing via server IP, Chrome may prompt <em>&quot;Insecure download blocked&quot;</em> for downloaded files. If prompted, click <strong>&quot;Keep&quot;</strong> in your browser&apos;s download bar to finish saving your certified report, or use <strong>&quot;Preview&quot;</strong> to inspect the PDF directly in a new tab.
            </span>
          </div>
        </div>

        {/* Global Operational Dashboard Filter Bar */}
        <GlobalDashboardFilterBar />

        {/* Loading State */}
        {isCatalogLoading && catalog.length === 0 && (
          <div
            className="p-10 text-center text-blue-700 text-sm font-semibold bg-white rounded-lg border border-slate-200 shadow-xs"
            data-testid="catalog-loading-state"
          >
            <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-blue-600" />
            Loading backend report catalog...
          </div>
        )}

        {/* Error State */}
        {catalogError && (
          <div
            className="bg-rose-50 border border-rose-200 text-rose-700 p-4 rounded-lg text-sm font-semibold flex justify-between items-center"
            data-testid="catalog-error-banner"
          >
            <span>{catalogError}</span>
            <Button variant="danger" size="sm" onClick={() => loadCatalog()}>
              Retry
            </Button>
          </div>
        )}

        {/* Catalog Grid */}
        {!isCatalogLoading && !catalogError && (
          <ReportCatalogGrid catalog={catalog} onExportSelect={handleExportSelect} />
        )}

        {/* Real-Time Execution History Section */}
        <div className="mt-4">
          <ReportExecutionHistoryTable
            executions={Object.values(useReportsStore.getState().executions)}
            onRefresh={() => loadCatalog()}
          />
        </div>

        {/* Reusable Export Modal Integration */}
        {selectedReport && (
          <ReportExportModal
            isOpen={isModalOpen}
            onClose={handleCloseModal}
            reportId={selectedReport.report_id}
            reportDefinition={selectedReport}
            scope={currentScope}
          />
        )}
      </div>
    </DashboardSyncProvider>
  );
};
