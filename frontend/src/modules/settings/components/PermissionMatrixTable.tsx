import React from 'react';
import {
  PlatformSectionKey,
  SectionAccessLevel,
  PLATFORM_SECTIONS,
  PLATFORM_SECTION_LABELS,
  TESTED_PILOT_SECTIONS,
} from '../../../types/auth';
import {
  Home,
  LayoutDashboard,
  BarChart3,
  Clock,
  Zap,
  Activity,
  Brain,
  Bell,
  FileSpreadsheet,
  Layers,
  FileSearch,
  Settings,
  Users,
  Shield,
  Eye,
  Check,
  RotateCcw,
} from 'lucide-react';

export interface PermissionMatrixTableProps {
  permissions: Record<string, SectionAccessLevel>;
  onChange: (updated: Record<string, SectionAccessLevel>) => void;
  disabled?: boolean;
  isSuperuser?: boolean;
}

interface SectionMeta {
  key: PlatformSectionKey;
  label: string;
  route: string;
  desc: string;
  icon: React.ReactNode;
}

const SECTION_CATALOG: SectionMeta[] = [
  { key: 'platform_home', label: 'Platform Home', route: '/', desc: 'Live operational KPIs & incident summary', icon: <Home className="w-3.5 h-3.5 text-blue-600" /> },
  { key: 'site_dashboard', label: 'Site Dashboard', route: '/site-dashboard', desc: 'Plant stats, TM queue & cycle stages', icon: <LayoutDashboard className="w-3.5 h-3.5 text-indigo-600" /> },
  { key: 'overall_dashboard', label: 'Overall Dashboard', route: '/overall-dashboard', desc: 'Fleet holding & capacity loss metrics', icon: <BarChart3 className="w-3.5 h-3.5 text-blue-600" /> },
  { key: 'dispatch_analysis', label: 'Dispatch Analysis', route: '/dispatch-analysis', desc: 'Transit route telemetry & maps replay', icon: <Clock className="w-3.5 h-3.5 text-amber-600" /> },
  { key: 'dispatch_optimization', label: 'Dispatch Optimization', route: '/dispatch-optimization', desc: 'Cadence solver & baseline comparison', icon: <Zap className="w-3.5 h-3.5 text-emerald-600" /> },
  { key: 'operational_intelligence', label: 'Operational Intelligence', route: '/operational-intelligence', desc: 'Pipeline bottlenecks & active directives', icon: <Activity className="w-3.5 h-3.5 text-cyan-600" /> },
  { key: 'predictive_intelligence', label: 'Predictive Intelligence', route: '/predictive-intelligence', desc: 'ML models, drift detection & scoring', icon: <Brain className="w-3.5 h-3.5 text-purple-600" /> },
  { key: 'control_tower_actions', label: 'Control Tower Actions', route: '/control-tower-actions', desc: 'Supervisor actions & dispatch triggers', icon: <Zap className="w-3.5 h-3.5 text-rose-600" /> },
  { key: 'alerts', label: 'Alert Center', route: '/alerts', desc: 'Incident triage & threshold breaches', icon: <Bell className="w-3.5 h-3.5 text-amber-600" /> },
  { key: 'reports', label: 'Reports & Exports', route: '/reports', desc: 'PDF preview, async jobs & Excel downloads', icon: <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" /> },
  { key: 'erp_import', label: /* 'ERP Import' */ 'Data Ingestion Hub', route: '/erp/import', desc: 'Batch workbook uploads & ingestion logs', icon: <Layers className="w-3.5 h-3.5 text-blue-600" /> },
  { key: 'erp_explorer', label: /* 'ERP Data Explorer' */ 'Data Explorer', route: '/erp/explorer', desc: 'Historical ERP record search & queries', icon: <FileSearch className="w-3.5 h-3.5 text-indigo-600" /> },
  { key: 'settings', label: 'Settings Center', route: '/settings', desc: 'Plant configs, customer rules & rates', icon: <Settings className="w-3.5 h-3.5 text-slate-600" /> },
  { key: 'user_management', label: 'User Management', route: '/settings/users', desc: 'User governance, passwords & roles', icon: <Users className="w-3.5 h-3.5 text-rose-600" /> },
];

export const PermissionMatrixTable: React.FC<PermissionMatrixTableProps> = ({
  permissions,
  onChange,
  disabled = false,
  isSuperuser = false,
}) => {
  // Preset templates
  const applyAdminPreset = () => {
    if (disabled || isSuperuser) return;
    const full: Record<string, SectionAccessLevel> = {};
    PLATFORM_SECTIONS.forEach((s) => {
      full[s] = 'edit';
    });
    onChange(full);
  };

  const applyTestedPilotPreset = () => {
    if (disabled || isSuperuser) return;
    const pilot: Record<string, SectionAccessLevel> = {};
    PLATFORM_SECTIONS.forEach((s) => {
      pilot[s] = TESTED_PILOT_SECTIONS.includes(s) ? 'view' : 'none';
    });
    onChange(pilot);
  };

  const applyDemoOperatorPreset = () => {
    if (disabled || isSuperuser) return;
    const demo: Record<string, SectionAccessLevel> = {};
    PLATFORM_SECTIONS.forEach((s) => {
      if (s === 'settings' || s === 'user_management' || s === 'erp_import') {
        demo[s] = 'none';
      } else {
        demo[s] = 'view';
      }
    });
    onChange(demo);
  };

  const applyExecutiveViewerPreset = () => {
    if (disabled || isSuperuser) return;
    const exec: Record<string, SectionAccessLevel> = {};
    PLATFORM_SECTIONS.forEach((s) => {
      exec[s] = 'view';
    });
    onChange(exec);
  };

  const handleSelectAllView = () => {
    if (disabled || isSuperuser) return;
    const updated: Record<string, SectionAccessLevel> = {};
    PLATFORM_SECTIONS.forEach((s) => {
      updated[s] = 'view';
    });
    onChange(updated);
  };

  const handleSelectAllEdit = () => {
    if (disabled || isSuperuser) return;
    const updated: Record<string, SectionAccessLevel> = {};
    PLATFORM_SECTIONS.forEach((s) => {
      updated[s] = 'edit';
    });
    onChange(updated);
  };

  const handleClearAll = () => {
    if (disabled || isSuperuser) return;
    const updated: Record<string, SectionAccessLevel> = {};
    PLATFORM_SECTIONS.forEach((s) => {
      updated[s] = 'none';
    });
    onChange(updated);
  };

  const toggleView = (key: PlatformSectionKey) => {
    if (disabled || isSuperuser) return;
    const current = permissions[key] || 'none';
    let next: SectionAccessLevel = 'none';
    if (current === 'none') {
      next = 'view';
    } else {
      next = 'none';
    }
    onChange({ ...permissions, [key]: next });
  };

  const toggleEdit = (key: PlatformSectionKey) => {
    if (disabled || isSuperuser) return;
    const current = permissions[key] || 'none';
    let next: SectionAccessLevel = 'none';
    if (current === 'edit') {
      next = 'view'; // Downgrade to view only
    } else {
      next = 'edit'; // Edit implies view automatically
    }
    onChange({ ...permissions, [key]: next });
  };

  // Determine active preset
  const isFullAdmin = PLATFORM_SECTIONS.every((s) => (permissions[s] || 'none') === 'edit');
  const isTestedPilot =
    PLATFORM_SECTIONS.every((s) =>
      TESTED_PILOT_SECTIONS.includes(s)
        ? (permissions[s] || 'none') === 'view'
        : (permissions[s] || 'none') === 'none'
    );

  const isDemoOperator =
    PLATFORM_SECTIONS.filter((s) => s !== 'settings' && s !== 'user_management' && s !== 'erp_import').every(
      (s) => (permissions[s] || 'none') === 'view'
    ) &&
    (permissions['settings'] || 'none') === 'none' &&
    (permissions['user_management'] || 'none') === 'none' &&
    (permissions['erp_import'] || 'none') === 'none';

  const isExecutive = PLATFORM_SECTIONS.every((s) => (permissions[s] || 'none') === 'view');

  const displayedSections = isTestedPilot
    ? SECTION_CATALOG.filter((sec) => TESTED_PILOT_SECTIONS.includes(sec.key))
    : SECTION_CATALOG;

  const hiddenPilotSections = isTestedPilot
    ? SECTION_CATALOG.filter((sec) => !TESTED_PILOT_SECTIONS.includes(sec.key))
    : [];

  return (
    <div className="space-y-2.5">
      {/* Header with Quick Presets */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-2 rounded-lg bg-slate-50 border border-slate-200">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider mr-1">
            Presets:
          </span>
          <button
            type="button"
            disabled={disabled || isSuperuser}
            onClick={applyAdminPreset}
            className={`px-2 py-1 rounded text-[11px] font-bold transition-all shadow-2xs ${
              isFullAdmin
                ? 'bg-blue-700 text-white'
                : 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-100'
            }`}
          >
            🛡️ Administrator (Full)
          </button>
                    <button
            type="button"
            disabled={disabled || isSuperuser}
            onClick={applyTestedPilotPreset}
            className={`px-2 py-1 rounded text-[11px] font-bold transition-all shadow-2xs ${
              isTestedPilot
                ? 'bg-blue-700 text-white'
                : 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-100'
            }`}
            title="Enables View on stable, fully-mapped sections (Site/Overall Dashboards, Dispatch Analysis, Alerts, Reports, ERP Explorer)"
          >
            🧪 Tested Pilot (Phase 1)
          </button>
          <button
            type="button"
            disabled={disabled || isSuperuser}
            onClick={applyDemoOperatorPreset}
            className={`px-2 py-1 rounded text-[11px] font-bold transition-all shadow-2xs ${
              isDemoOperator
                ? 'bg-blue-700 text-white'
                : 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-100'
            }`}
          >
            👁️ Demo Operator (View Only)
          </button>
          <button
            type="button"
            disabled={disabled || isSuperuser}
            onClick={applyExecutiveViewerPreset}
            className={`px-2 py-1 rounded text-[11px] font-bold transition-all shadow-2xs ${
              isExecutive
                ? 'bg-blue-700 text-white'
                : 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-100'
            }`}
          >
            📊 Executive (All Views)
          </button>
        </div>

        {/* Master Column Controls */}
        {!isSuperuser && (
          <div className="flex items-center gap-1.5 self-end sm:self-auto text-[10px]">
            <button
              type="button"
              disabled={disabled}
              onClick={handleSelectAllView}
              className="text-slate-600 hover:text-blue-700 font-semibold underline px-1 py-0.5"
            >
              All View
            </button>
            <span className="text-slate-300">|</span>
            <button
              type="button"
              disabled={disabled}
              onClick={handleSelectAllEdit}
              className="text-slate-600 hover:text-blue-700 font-semibold underline px-1 py-0.5"
            >
              All Edit
            </button>
            <span className="text-slate-300">|</span>
            <button
              type="button"
              disabled={disabled}
              onClick={handleClearAll}
              className="text-rose-600 hover:text-rose-800 font-semibold underline px-1 py-0.5"
            >
              Clear All
            </button>
          </div>
        )}
      </div>

      {isSuperuser && (
        <div className="p-2 rounded-md bg-blue-50 border border-blue-200 text-blue-800 text-[11px] flex items-center gap-2">
          <Shield className="w-4 h-4 text-blue-600 shrink-0" />
          <span>
            <strong>System Superuser:</strong> This account permanently holds unrestricted administrative access across all sections.
          </span>
        </div>
      )}

      {/* Matrix Table */}
      <div className="border border-slate-200 rounded-lg overflow-hidden bg-white shadow-2xs max-h-64 overflow-y-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead className="bg-slate-100/80 sticky top-0 border-b border-slate-200 text-slate-700 z-10 text-[11px]">
            <tr>
              <th className="py-2 px-3 font-bold uppercase tracking-wider">
                Platform Menu Section
              </th>
              <th className="py-2 px-3 font-bold uppercase tracking-wider text-center w-28">
                View Only
              </th>
              <th className="py-2 px-3 font-bold uppercase tracking-wider text-center w-28">
                Edit / Run
              </th>
              <th className="py-2 px-3 font-bold uppercase tracking-wider text-right w-24">
                Access
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {displayedSections.map((sec) => {
              const level = isSuperuser ? 'edit' : permissions[sec.key] || 'none';
              const hasView = level === 'view' || level === 'edit';
              const hasEdit = level === 'edit';

              return (
                <tr
                  key={sec.key}
                  className={`hover:bg-slate-50/80 transition-colors ${
                    level === 'none' ? 'opacity-65' : ''
                  }`}
                >
                  <td className="py-2 px-3">
                    <div className="flex items-center gap-2">
                      <div className="p-1 rounded bg-slate-100 border border-slate-200 shrink-0">
                        {sec.icon}
                      </div>
                      <div>
                        <div className="font-bold text-slate-800 text-[11px] flex items-center gap-1.5">
                          <span>{sec.label}</span>
                          <span className="text-[10px] font-mono text-slate-400 font-normal">
                            {sec.route}
                          </span>
                        </div>
                        <div className="text-[10px] text-slate-500 line-clamp-1">{sec.desc}</div>
                      </div>
                    </div>
                  </td>

                  {/* View Column */}
                  <td className="py-2 px-3 text-center">
                    <label className="inline-flex items-center justify-center cursor-pointer p-1">
                      <input
                        type="checkbox"
                        disabled={disabled || isSuperuser}
                        checked={hasView}
                        onChange={() => toggleView(sec.key)}
                        className="rounded border-slate-300 text-blue-700 focus:ring-blue-600 w-4 h-4 cursor-pointer disabled:cursor-not-allowed"
                      />
                    </label>
                  </td>

                  {/* Edit Column */}
                  <td className="py-2 px-3 text-center">
                    <label className="inline-flex items-center justify-center cursor-pointer p-1">
                      <input
                        type="checkbox"
                        disabled={disabled || isSuperuser}
                        checked={hasEdit}
                        onChange={() => toggleEdit(sec.key)}
                        className="rounded border-slate-300 text-blue-700 focus:ring-blue-600 w-4 h-4 cursor-pointer disabled:cursor-not-allowed"
                      />
                    </label>
                  </td>

                  {/* Access Status Badge */}
                  <td className="py-2 px-3 text-right">
                    {level === 'edit' ? (
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 border border-blue-200">
                        Edit
                      </span>
                    ) : level === 'view' ? (
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                        View
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-500 border border-slate-200">
                        None
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {isTestedPilot && hiddenPilotSections.length > 0 && (
        <div className="p-2.5 rounded-lg bg-amber-50/70 border border-amber-200/80 text-[11px] flex flex-col gap-1.5 shadow-2xs">
          <div className="flex items-center gap-1.5 font-bold text-amber-900">
            <span>🔒 Hidden Sections (No Access in Phase 1 Pilot):</span>
          </div>
          <div className="flex flex-wrap gap-1 text-[10px]">
            {hiddenPilotSections.map((sec) => (
              <span key={sec.key} className="px-2 py-0.5 rounded-md bg-white border border-amber-200 text-amber-800 font-medium shadow-2xs">
                {sec.label}
              </span>
            ))}
          </div>
          <span className="text-[10px] text-amber-700/80 italic">
            These sections are completely locked and hidden for this user. To view or configure permissions for all sections, click "Executive (All Views)" or "Administrator" preset above.
          </span>
        </div>
      )}

      <div className="flex items-center justify-between text-[10px] text-slate-500 px-1 font-medium">
        <span>* Selecting <strong>Edit</strong> automatically enables <strong>View</strong> access.</span>
        <span>
          {isTestedPilot
            ? `${displayedSections.length} Active Pilot Sections (${hiddenPilotSections.length} Locked & Hidden)`
            : '14 Canonical Sections'}
        </span>
      </div>
    </div>
  );
};
