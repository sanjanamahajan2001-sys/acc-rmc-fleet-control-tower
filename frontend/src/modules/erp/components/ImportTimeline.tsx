import React from 'react';
import { IconCycleStopwatch, IconCalendarCheckmark } from '../../../components/icons/LinealColorIcons';
import { useERPProgressStore } from '../stores';

export const ImportTimeline: React.FC = () => {
  const snapshot = useERPProgressStore((s) => s.snapshot);

  const timelineSteps = [
    { stage: 'QUEUED', label: 'Import Job Enqueued', time: 'T+0.00s' },
    { stage: 'PARSING', label: 'Streaming Batch Excel Parsing', time: 'T+0.25s' },
    { stage: 'VALIDATING', label: 'Layer 1 & 2 Canonical Validation', time: 'T+0.80s' },
    { stage: 'PERSISTING', label: 'PostgreSQL Atomic Persistence', time: 'T+1.40s' },
    { stage: 'COMPLETED', label: 'Pipeline Completed & Audit Logged', time: 'T+1.85s' },
  ];

  const currentStageIndex = timelineSteps.findIndex((s) => s.stage === snapshot?.stage);

  return (
    <div className="p-5 rounded-lg border border-slate-200/90 bg-white space-y-3.5 shadow-xs">
      <h3 className="text-[11px] font-bold uppercase tracking-wider flex items-center gap-2 text-slate-900">
        <IconCycleStopwatch className="w-4 h-4" />
        Import Execution Timeline
      </h3>

      <div className="relative pl-6 space-y-5 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
        {timelineSteps.map((step, index) => {
          const isPassed = currentStageIndex >= 0 && index <= currentStageIndex;
          const isActive = snapshot?.stage === step.stage;

          return (
            <div key={step.stage} className="relative flex items-center justify-between text-xs">
              <div
                className={`absolute -left-6 w-4 h-4 rounded-full flex items-center justify-center border text-[10px] font-bold ${
                  isPassed
                    ? 'bg-emerald-50 border-emerald-300 text-emerald-700'
                    : 'bg-white border-slate-300 text-slate-400'
                }`}
              >
                {isPassed ? <IconCalendarCheckmark className="w-3.5 h-3.5" /> : null}
              </div>

              <div>
                <p
                  className={`font-bold ${
                    isActive
                      ? 'text-blue-700'
                      : isPassed
                      ? 'text-emerald-700'
                      : 'text-slate-600'
                  }`}
                >
                  {step.label}
                </p>
                <p className="font-mono text-[10px] text-slate-400">{step.stage}</p>
              </div>

              <span className={`font-mono font-bold text-[11px] ${isPassed ? 'text-emerald-700' : 'text-slate-400'}`}>
                {step.time}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
