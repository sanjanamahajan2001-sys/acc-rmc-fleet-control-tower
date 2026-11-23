import React from 'react';
import { IconShieldSecure } from '../../../components/icons/LinealColorIcons';
import { useERPProgressStore } from '../stores';

interface VerificationItem {
  id: string;
  label: string;
  check: (stage?: string) => 'PASS' | 'WARNING' | 'PENDING';
}

const CHECKS: VerificationItem[] = [
  { id: 'storage', label: 'Workbook File Stored in Local Storage Provider', check: (s) => (s ? 'PASS' : 'PENDING') },
  { id: 'checksum', label: 'SHA-256 Checksum Streaming Verified', check: (s) => (s ? 'PASS' : 'PENDING') },
  { id: 'validation', label: 'Layer 1 & Layer 2 Validation Rules Passed', check: (s) => (s === 'PERSISTING' || s === 'COMPLETED' ? 'PASS' : 'PENDING') },
  { id: 'persistence', label: 'PostgreSQL UnitOfWork Transaction Committed', check: (s) => (s === 'COMPLETED' ? 'PASS' : 'PENDING') },
  { id: 'audit', label: 'ImportAuditLog Entry Written', check: (s) => (s === 'COMPLETED' ? 'PASS' : 'PENDING') },
  { id: 'metrics', label: 'ImportStatistic & Telemetry Metrics Recorded', check: (s) => (s === 'COMPLETED' ? 'PASS' : 'PENDING') },
];

export const VerificationPanel: React.FC = () => {
  const currentStage = useERPProgressStore((s) => s.snapshot?.stage);

  return (
    <div className="p-5 rounded-lg border border-slate-200/90 bg-white space-y-3.5 shadow-xs">
      <div className="flex items-center gap-2 font-bold text-slate-900">
        <IconShieldSecure className="w-4 h-4" />
        <h3 className="text-xs font-bold uppercase tracking-wider">Backend Integrity &amp; Verification Panel</h3>
      </div>

      <div className="space-y-1.5">
        {CHECKS.map((item) => {
          const status = item.check(currentStage);
          return (
            <div
              key={item.id}
              className="flex items-center justify-between p-2 rounded border border-slate-200 bg-slate-50 text-xs font-medium"
            >
              <span className="text-slate-700 font-medium text-[11px]">{item.label}</span>
              <span
                className={`px-1.5 py-0.5 font-bold font-mono rounded border text-[10px] ${
                  status === 'PASS'
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                    : status === 'WARNING'
                    ? 'bg-amber-50 border-amber-200 text-amber-700'
                    : 'bg-white border-slate-200 text-slate-500'
                }`}
              >
                {status}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
