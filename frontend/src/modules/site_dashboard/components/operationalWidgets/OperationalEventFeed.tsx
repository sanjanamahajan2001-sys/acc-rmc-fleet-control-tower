import React from 'react';
import { AlertTriangle, Clock } from 'lucide-react';

export interface EventItem {
  event_id: string;
  timestamp: string;
  event_type: 'SLA_BREACH' | 'QUEUE_OVERFLOW' | 'ERP_IMPORT_COMPLETE' | 'ERP_IMPORT_FAILED' | 'LONG_DELAY';
  category_icon: string;
  title: string;
  description: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'INFO';
}

interface OperationalEventFeedProps {
  events: EventItem[];
}

export const OperationalEventFeed: React.FC<OperationalEventFeedProps> = ({ events }) => {
  const severityColors: Record<string, string> = {
    CRITICAL: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
    HIGH: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
    MEDIUM: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    INFO: 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30',
  };

  return (
    <div className="space-y-3">
      <h3 className="text-xs font-extrabold text-slate-300 uppercase tracking-wider">
        RECENT OPERATIONAL EVENTS & SLA BREACH FEED (MAX 20)
      </h3>

      {events.length === 0 ? (
        <div className="p-6 text-center text-xs text-slate-500 italic border border-slate-800/80 rounded-xl bg-slate-950/60">
          No recent operational events detected for active filters.
        </div>
      ) : (
        <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
          {events.map((e) => (
            <div key={e.event_id} className="p-3 rounded-xl bg-slate-950/80 border border-slate-800/90 flex items-center justify-between gap-3 hover:bg-slate-900/60 transition">
              <div className="flex items-center gap-3">
                <div className="w-7 h-7 rounded-lg bg-slate-800 flex items-center justify-center text-slate-300">
                  {e.severity === 'CRITICAL' || e.severity === 'HIGH' ? <AlertTriangle className="w-4 h-4 text-rose-400" /> : <Clock className="w-4 h-4 text-amber-400" />}
                </div>
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-extrabold text-slate-100">{e.title}</span>
                    <span className="text-[10px] font-mono text-slate-500">{e.timestamp}</span>
                  </div>
                  <p className="text-[11px] text-slate-400">{e.description}</p>
                </div>
              </div>
              <span className={`px-2 py-0.5 rounded text-[9.5px] font-extrabold uppercase border ${severityColors[e.severity]}`}>
                {e.severity}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
