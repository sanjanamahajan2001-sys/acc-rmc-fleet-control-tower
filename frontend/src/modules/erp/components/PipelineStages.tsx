import React from 'react';
import { Loader2, Circle } from 'lucide-react';
import { IconCalendarCheckmark, IconCriticalAlert } from '../../../components/icons/LinealColorIcons';
import { useERPProgressStore } from '../stores';
import { ImportPipelineStage } from '../types';

interface StageConfig {
  id: string;
  label: string;
  matchingStages: ImportPipelineStage[];
}

const STAGES: StageConfig[] = [
  { id: 'upload', label: 'Workbook Upload & Storage', matchingStages: ['ACQUIRING'] },
  { id: 'parsing', label: 'Streaming Batch Parsing', matchingStages: ['PARSING'] },
  { id: 'validation', label: 'Layer 1 & 2 Canonical Validation', matchingStages: ['VALIDATING'] },
  { id: 'persistence', label: 'PostgreSQL UnitOfWork Persistence', matchingStages: ['PERSISTING'] },
  { id: 'digital_twin', label: 'Digital Twin State Synchronization', matchingStages: ['COMPLETED'] },
  { id: 'kpi_engine', label: 'Real-time Fleet KPI Engine', matchingStages: ['COMPLETED'] },
];

export const PipelineStages: React.FC = () => {
  const currentStage = useERPProgressStore((s) => s.snapshot?.stage);

  const getStageStatus = (stageConfig: StageConfig) => {
    if (!currentStage) return 'pending';
    if (currentStage === 'FAILED') return 'failed';
    if (currentStage === 'COMPLETED') return 'completed';

    if (stageConfig.matchingStages.includes(currentStage)) {
      return 'running';
    }

    const currentIndex = STAGES.findIndex((s) => s.matchingStages.includes(currentStage));
    const stageIndex = STAGES.findIndex((s) => s.id === stageConfig.id);

    if (stageIndex < currentIndex) return 'completed';
    return 'pending';
  };

  return (
    <div className="p-5 rounded-lg border border-slate-200/90 bg-white space-y-3.5 shadow-xs">
      <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-900">
        Full Pipeline Progression
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">
        {STAGES.map((stage) => {
          const status = getStageStatus(stage);
          return (
            <div
              key={stage.id}
              className={`p-2.5 rounded-md border flex items-center gap-2.5 transition-all font-medium ${
                status === 'running'
                  ? 'bg-blue-50 border-blue-200 text-blue-800'
                  : status === 'completed'
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                  : status === 'failed'
                  ? 'bg-rose-50 border-rose-200 text-rose-800'
                  : 'bg-slate-50 border-slate-200 text-slate-600'
              }`}
            >
              {status === 'running' && <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-700 shrink-0" />}
              {status === 'completed' && <IconCalendarCheckmark className="w-3.5 h-3.5 shrink-0" />}
              {status === 'failed' && <IconCriticalAlert className="w-3.5 h-3.5 shrink-0" />}
              {status === 'pending' && <Circle className="w-3.5 h-3.5 text-slate-400 shrink-0" />}

              <span className="text-xs font-bold">{stage.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
