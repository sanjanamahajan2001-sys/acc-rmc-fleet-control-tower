import { env } from '../../../config/env';
import React, { useState, useEffect, useMemo } from 'react';
import { useAuthStore } from '../../../store/auth';
import {
  Database,
  Search,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Download,
  Copy,
  Check,
  Table2,
  Key,
  Link2,
  Layers,
  Code2,
  RefreshCw,
  AlertCircle,
  Clock,
  Server,
  FileCode,
  ShieldCheck,
} from 'lucide-react';

interface DatabaseColumn {
  name: string;
  data_type: string;
  udt_name?: string | null;
  is_nullable: boolean;
  column_default?: string | null;
  is_primary_key: boolean;
  is_foreign_key: boolean;
  foreign_key_target_table?: string | null;
  foreign_key_target_column?: string | null;
}

interface DatabaseTable {
  table_name: string;
  table_schema: string;
  columns: DatabaseColumn[];
  primary_keys: string[];
  foreign_keys: Array<{
    column_name: string;
    target_table: string;
    target_column: string;
    constraint_name?: string | null;
  }>;
}

interface DatabaseSchemaResponse {
  database_name: string;
  schema_name: string;
  table_count: number;
  column_count: number;
  primary_key_count: number;
  foreign_key_count: number;
  generated_at: string;
  tables: DatabaseTable[];
}

interface DatabaseSqlExportResponse {
  database_name: string;
  schema_name: string;
  table_count: number;
  generated_at: string;
  sql_script: string;
}

export const DatabasePreviewSection: React.FC = () => {
  const token = useAuthStore((state) => state.token);
  const user = useAuthStore((state) => state.user);

  const [activeTab, setActiveTab] = useState<'visual' | 'sql'>('visual');
  const [schemaData, setSchemaData] = useState<DatabaseSchemaResponse | null>(null);
  const [sqlExportData, setSqlExportData] = useState<DatabaseSqlExportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingSql, setLoadingSql] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [zoomLevel, setZoomLevel] = useState(100);
  const [copied, setCopied] = useState(false);

  const fetchSchema = async () => {
    setLoading(true);
    setError(null);
    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      const res = await fetch(`${env.VITE_API_BASE_URL}/settings/database-schema`, {
        headers,
      });

      if (!res.ok) {
        if (res.status === 401 || res.status === 403) {
          throw new Error('Access denied: Administrator privileges required to inspect database schema.');
        }
        throw new Error(`Failed to load database schema (HTTP ${res.status})`);
      }

      const json = await res.json();
      if (json.success && json.data) {
        setSchemaData(json.data);
      } else {
        throw new Error(json.message || 'Failed to parse database schema');
      }
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred while fetching database schema.');
    } finally {
      setLoading(false);
    }
  };

  const fetchSqlExport = async () => {
    if (sqlExportData) return;
    setLoadingSql(true);
    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      const res = await fetch(`${env.VITE_API_BASE_URL}/settings/database-schema/sql-export`, {
        headers,
      });

      if (!res.ok) {
        throw new Error('Failed to generate SQL export.');
      }

      const json = await res.json();
      if (json.success && json.data) {
        setSqlExportData(json.data);
      }
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoadingSql(false);
    }
  };

  useEffect(() => {
    fetchSchema();
  }, [token]);

  useEffect(() => {
    if (activeTab === 'sql') {
      fetchSqlExport();
    }
  }, [activeTab]);

  const handleZoomIn = () => {
    setZoomLevel((prev) => Math.min(prev + 10, 150));
  };

  const handleZoomOut = () => {
    setZoomLevel((prev) => Math.max(prev - 10, 70));
  };

  const handleResetZoom = () => {
    setZoomLevel(100);
  };

  const handleCopySql = () => {
    if (sqlExportData?.sql_script) {
      navigator.clipboard.writeText(sqlExportData.sql_script);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownloadSql = () => {
    if (sqlExportData?.sql_script) {
      const element = document.createElement('a');
      const file = new Blob([sqlExportData.sql_script], { type: 'text/plain' });
      element.href = URL.createObjectURL(file);
      element.download = `${schemaData?.database_name || 'fleet_control_tower'}_schema_export.sql`;
      document.body.appendChild(element);
      element.click();
      document.body.removeChild(element);
    }
  };

  const filteredTables = useMemo(() => {
    if (!schemaData?.tables) return [];
    if (!searchQuery.trim()) return schemaData.tables;

    const query = searchQuery.toLowerCase().trim();
    return schemaData.tables.filter((table) => {
      const nameMatch = table.table_name.toLowerCase().includes(query);
      const columnMatch = table.columns.some((col) => col.name.toLowerCase().includes(query));
      return nameMatch || columnMatch;
    });
  }, [schemaData, searchQuery]);

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div
        className="p-5 rounded-xl border shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4"
        style={{ backgroundColor: '#FBFCFE', borderColor: '#DCE2EA' }}
      >
        <div className="flex items-start md:items-center gap-3">
          <div
            className="p-2.5 rounded-xl border shrink-0"
            style={{ backgroundColor: '#EFF6FF', borderColor: '#BFDBFE', color: '#1D4ED8' }}
          >
            <Database className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold tracking-tight" style={{ color: '#172033' }}>
                PostgreSQL Schema Viewer &amp; Live Introspection
              </h2>
              <span
                className="px-2 py-0.5 rounded-md text-[11px] font-bold border flex items-center gap-1"
                style={{ backgroundColor: '#ECFDF5', borderColor: '#A7F3D0', color: '#16805C' }}
              >
                <ShieldCheck className="w-3 h-3" /> Live Metadata
              </span>
            </div>
            <p className="text-xs font-medium" style={{ color: '#64748B' }}>
              Real-time dynamic inspection of PostgreSQL tables, columns, primary keys, and foreign key relations.
            </p>
          </div>
        </div>

        {/* View Switcher Tabs */}
        <div className="flex items-center gap-1 p-1 rounded-xl border bg-slate-100" style={{ borderColor: '#DCE2EA' }}>
          <button
            type="button"
            onClick={() => setActiveTab('visual')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition ${
              activeTab === 'visual'
                ? 'bg-white text-indigo-600 shadow-xs border border-slate-200'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            Schema Viewer
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('sql')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition ${
              activeTab === 'sql'
                ? 'bg-white text-indigo-600 shadow-xs border border-slate-200'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Code2 className="w-3.5 h-3.5" />
            SQL DDL Export
          </button>
        </div>
      </div>

      {/* Summary KPI Badges */}
      {schemaData && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div
            className="p-3.5 rounded-xl border shadow-xs"
            style={{ backgroundColor: '#FBFCFE', borderColor: '#DCE2EA' }}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Public Tables</span>
              <Table2 className="w-4 h-4 text-indigo-600" />
            </div>
            <div className="text-xl font-bold mt-1" style={{ color: '#172033' }}>
              {schemaData.table_count}
            </div>
            <span className="text-[10px] text-slate-400 font-medium">PostgreSQL Base Tables</span>
          </div>

          <div
            className="p-3.5 rounded-xl border shadow-xs"
            style={{ backgroundColor: '#FBFCFE', borderColor: '#DCE2EA' }}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Total Columns</span>
              <Layers className="w-4 h-4 text-sky-600" />
            </div>
            <div className="text-xl font-bold mt-1" style={{ color: '#172033' }}>
              {schemaData.column_count}
            </div>
            <span className="text-[10px] text-slate-400 font-medium">Across all schemas</span>
          </div>

          <div
            className="p-3.5 rounded-xl border shadow-xs"
            style={{ backgroundColor: '#FBFCFE', borderColor: '#DCE2EA' }}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">FK Relations</span>
              <Link2 className="w-4 h-4 text-indigo-600" />
            </div>
            <div className="text-xl font-bold mt-1" style={{ color: '#172033' }}>
              {schemaData.foreign_key_count}
            </div>
            <span className="text-[10px] text-slate-400 font-medium">Referential Constraints</span>
          </div>

          <div
            className="p-3.5 rounded-xl border shadow-xs"
            style={{ backgroundColor: '#FBFCFE', borderColor: '#DCE2EA' }}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Database</span>
              <Server className="w-4 h-4 text-emerald-600" />
            </div>
            <div className="text-sm font-bold mt-1 truncate" style={{ color: '#172033' }}>
              {schemaData.database_name}
            </div>
            <span className="text-[10px] text-slate-400 font-medium flex items-center gap-1">
              <Clock className="w-2.5 h-2.5" />
              {schemaData.generated_at ? new Date(schemaData.generated_at).toLocaleTimeString() : 'Live'}
            </span>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      {loading ? (
        <div
          className="p-12 rounded-xl border flex flex-col items-center justify-center gap-3 text-center"
          style={{ backgroundColor: '#FBFCFE', borderColor: '#DCE2EA' }}
        >
          <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin" />
          <p className="text-sm font-bold" style={{ color: '#172033' }}>
            Querying PostgreSQL information_schema...
          </p>
          <p className="text-xs text-slate-500">Introspecting live base tables, keys, and constraint targets.</p>
        </div>
      ) : error ? (
        <div
          className="p-6 rounded-xl border flex items-center gap-3 text-rose-800 bg-rose-50 border-rose-200"
        >
          <AlertCircle className="w-5 h-5 shrink-0 text-rose-600" />
          <div className="text-xs">
            <p className="font-bold">Database Introspection Error</p>
            <p className="mt-0.5">{error}</p>
            <button
              onClick={fetchSchema}
              className="mt-2 px-3 py-1 bg-rose-100 hover:bg-rose-200 text-rose-900 rounded-lg font-bold inline-flex items-center gap-1"
            >
              <RefreshCw className="w-3 h-3" /> Retry
            </button>
          </div>
        </div>
      ) : activeTab === 'visual' ? (
        <div className="space-y-4">
          {/* Controls Bar */}
          <div
            className="p-4 rounded-xl border shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-3"
            style={{ backgroundColor: '#FBFCFE', borderColor: '#DCE2EA' }}
          >
            {/* Search Filter */}
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search tables or columns (e.g. 'dispatches', 'customer_id')..."
                className="w-full pl-9 pr-4 py-2 rounded-xl border text-xs font-medium focus:outline-none min-h-[38px]"
                style={{ backgroundColor: '#FFFFFF', borderColor: '#DCE2EA', color: '#172033' }}
              />
            </div>

            {/* Canvas Zoom Controls */}
            <div className="flex items-center gap-2">
              <div
                className="flex items-center border rounded-xl bg-white p-0.5 shadow-xs"
                style={{ borderColor: '#DCE2EA' }}
              >
                <button
                  type="button"
                  onClick={handleZoomOut}
                  title="Zoom Out"
                  className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-600 disabled:opacity-40"
                  disabled={zoomLevel <= 70}
                >
                  <ZoomOut className="w-4 h-4" />
                </button>
                <span className="px-2.5 text-xs font-bold text-slate-700 min-w-[50px] text-center">
                  {zoomLevel}%
                </span>
                <button
                  type="button"
                  onClick={handleZoomIn}
                  title="Zoom In"
                  className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-600 disabled:opacity-40"
                  disabled={zoomLevel >= 150}
                >
                  <ZoomIn className="w-4 h-4" />
                </button>
              </div>

              <button
                type="button"
                onClick={handleResetZoom}
                title="Reset Zoom"
                className="p-2 rounded-xl border bg-white hover:bg-slate-50 text-slate-600 shadow-xs"
                style={{ borderColor: '#DCE2EA' }}
              >
                <RotateCcw className="w-4 h-4" />
              </button>

              <button
                type="button"
                onClick={fetchSchema}
                title="Refresh Schema"
                className="p-2 rounded-xl border bg-white hover:bg-slate-50 text-slate-600 shadow-xs"
                style={{ borderColor: '#DCE2EA' }}
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Tables Grid / Canvas */}
          <div
            className="p-6 rounded-xl border shadow-xs overflow-x-auto min-h-[500px]"
            style={{
              backgroundColor: '#F8FAFC',
              borderColor: '#DCE2EA',
              transform: `scale(${zoomLevel / 100})`,
              transformOrigin: 'top left',
              transition: 'transform 0.15s ease-out',
            }}
          >
            {filteredTables.length === 0 ? (
              <div className="text-center py-16 text-slate-500">
                <Table2 className="w-8 h-8 mx-auto mb-2 opacity-40" />
                <p className="text-xs font-bold">No matching tables or columns found</p>
                <p className="text-[11px] text-slate-400 mt-1">Try adjusting your search query</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
                {filteredTables.map((table) => {
                  return (
                    <div
                      key={table.table_name}
                      className="rounded-xl border bg-white shadow-xs overflow-hidden flex flex-col hover:border-indigo-400 transition"
                      style={{ borderColor: '#DCE2EA' }}
                    >
                      {/* Table Card Header */}
                      <div
                        className="px-4 py-3 border-b flex items-center justify-between"
                        style={{ backgroundColor: '#FBFCFE', borderColor: '#E2E8F0' }}
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <Table2 className="w-4 h-4 text-indigo-600 shrink-0" />
                          <span className="text-xs font-bold truncate text-slate-900" title={table.table_name}>
                            {table.table_name}
                          </span>
                        </div>
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-600 shrink-0">
                          {table.columns.length} cols
                        </span>
                      </div>

                      {/* Columns List */}
                      <div className="divide-y divide-slate-100 max-h-80 overflow-y-auto font-mono text-[11px]">
                        {table.columns.map((col) => (
                          <div
                            key={col.name}
                            className="px-3.5 py-2 flex items-center justify-between gap-2 hover:bg-slate-50 transition"
                          >
                            <div className="flex items-center gap-1.5 min-w-0 truncate">
                              {col.is_primary_key ? (
                                <span title="Primary Key">
                                  <Key className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                                </span>
                              ) : col.is_foreign_key ? (
                                <span title={`Foreign Key → ${col.foreign_key_target_table}.${col.foreign_key_target_column}`}>
                                  <Link2 className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
                                </span>
                              ) : (
                                <span className="w-3.5 h-3.5 shrink-0 inline-block text-slate-300">•</span>
                              )}
                              <span
                                className={`truncate ${
                                  col.is_primary_key
                                    ? 'font-bold text-amber-950'
                                    : col.is_foreign_key
                                    ? 'font-bold text-indigo-950'
                                    : 'text-slate-800'
                                }`}
                              >
                                {col.name}
                              </span>
                              {!col.is_nullable && (
                                <span className="text-rose-500 text-[9px] font-bold" title="NOT NULL">
                                  *
                                </span>
                              )}
                            </div>

                            <div className="flex items-center gap-1.5 shrink-0 text-[10px] font-sans">
                              {col.is_foreign_key && col.foreign_key_target_table && (
                                <span
                                  className="px-1.5 py-0.2 rounded bg-indigo-50 text-indigo-700 text-[9px] font-medium border border-indigo-100 truncate max-w-[110px]"
                                  title={`References ${col.foreign_key_target_table}(${col.foreign_key_target_column})`}
                                >
                                  → {col.foreign_key_target_table}
                                </span>
                              )}
                              <span className="text-slate-400 font-mono text-[10px]">{col.data_type}</span>
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* Footer Info */}
                      {table.foreign_keys && table.foreign_keys.length > 0 && (
                        <div
                          className="px-3.5 py-1.5 bg-slate-50 border-t text-[10px] text-slate-500 flex items-center justify-between"
                          style={{ borderColor: '#F1F5F9' }}
                        >
                          <span>{table.foreign_keys.length} Foreign Relationships</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      ) : (
        /* SQL DDL Export Tab */
        <div className="space-y-4">
          <div
            className="p-4 rounded-xl border shadow-xs flex items-center justify-between gap-4"
            style={{ backgroundColor: '#FBFCFE', borderColor: '#DCE2EA' }}
          >
            <div className="flex items-center gap-2">
              <FileCode className="w-5 h-5 text-indigo-600" />
              <div>
                <h3 className="text-xs font-bold text-slate-900">Read-Only PostgreSQL Schema DDL</h3>
                <p className="text-[11px] text-slate-500">
                  Clean generated SQL with table structures, keys, and foreign constraints. Zero credentials.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleCopySql}
                disabled={loadingSql || !sqlExportData}
                className="px-3 py-1.5 rounded-xl border bg-white hover:bg-slate-50 text-slate-700 text-xs font-bold flex items-center gap-1.5 shadow-xs disabled:opacity-50"
                style={{ borderColor: '#DCE2EA' }}
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? 'Copied!' : 'Copy SQL'}
              </button>

              <button
                type="button"
                onClick={handleDownloadSql}
                disabled={loadingSql || !sqlExportData}
                className="px-3 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold flex items-center gap-1.5 shadow-xs disabled:opacity-50"
              >
                <Download className="w-3.5 h-3.5" />
                Download .sql
              </button>
            </div>
          </div>

          <div
            className="rounded-xl border overflow-hidden bg-slate-950 p-4 font-mono text-xs text-slate-200 shadow-inner"
            style={{ borderColor: '#334155' }}
          >
            {loadingSql ? (
              <div className="py-12 flex flex-col items-center justify-center gap-2 text-slate-400">
                <RefreshCw className="w-6 h-6 animate-spin text-indigo-400" />
                <p>Generating DDL export from PostgreSQL metadata...</p>
              </div>
            ) : sqlExportData ? (
              <pre className="overflow-x-auto max-h-[600px] leading-relaxed select-all">
                {sqlExportData.sql_script}
              </pre>
            ) : (
              <p className="text-slate-500 text-center py-8">Failed to generate SQL export.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
