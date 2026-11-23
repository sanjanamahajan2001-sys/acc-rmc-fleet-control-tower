import React from 'react';
import { ReportDefinitionDTO, ReportFormat } from '../types/report.types';
import { Download } from 'lucide-react';
import { IconExcelSpreadsheet } from '../../../components/icons/LinealColorIcons';

export interface ReportCatalogCardProps {
  report: ReportDefinitionDTO;
  onExportSelect: (report: ReportDefinitionDTO) => void;
}

const SHOW_JSON_FORMAT = false; // Manager requirement: Safely hide JSON format without removing code

export const ReportCatalogCard: React.FC<ReportCatalogCardProps> = ({ report, onExportSelect }) => {
  const visibleFormats = report.supported_formats.filter(
    (fmt) => SHOW_JSON_FORMAT || fmt !== ReportFormat.JSON
  );

  return (
    <div
      className="p-5 flex flex-col justify-between gap-3 rounded-lg border border-slate-200/90 bg-white shadow-xs hover:border-slate-300 transition-all"
      data-testid={`report-card-${report.report_id}`}
    >
      <div>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <IconExcelSpreadsheet className="w-4 h-4" />
            <span className="text-[11px] font-bold text-blue-700 tracking-wider uppercase">
              {(report.category || 'GENERAL').toUpperCase()}
            </span>
          </div>
          {report.is_active ? (
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
              ACTIVE
            </span>
          ) : (
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-50 text-rose-700 border border-rose-200">
              DISABLED
            </span>
          )}
        </div>
        
        <h3 className="text-sm font-bold text-slate-900 mb-1.5">{report.title}</h3>
        <p className="text-xs text-slate-600 leading-relaxed min-h-[36px] font-normal">{report.description}</p>
      </div>

      <div className="flex flex-col gap-3 pt-3 border-t border-slate-100">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold text-slate-500">Formats:</span>
          <div className="flex gap-1">
            {visibleFormats.map((fmt) => (
              <span
                key={fmt}
                className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200"
              >
                {fmt}
              </span>
            ))}
          </div>
        </div>

        <button
          disabled={!report.is_active}
          onClick={() => onExportSelect(report)}
          className="inline-flex items-center justify-center gap-1.5 w-full py-2 px-3.5 rounded-md text-xs font-bold transition-colors shadow-xs disabled:opacity-50 disabled:cursor-not-allowed bg-blue-700 hover:bg-blue-800 disabled:bg-slate-200 text-white disabled:text-slate-400"
          data-testid={'export-btn-' + report.report_id}
        >
          <Download className="w-3.5 h-3.5" /> Export Report
        </button>
      </div>
    </div>
  );
};
