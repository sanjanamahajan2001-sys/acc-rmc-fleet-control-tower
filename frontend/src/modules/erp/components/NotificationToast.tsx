import React from 'react';
import { CheckCircle, AlertCircle, Info, X } from 'lucide-react';
import { useERPNotificationStore } from '../stores';

export const NotificationToast: React.FC = () => {
  const { notifications, removeNotification } = useERPNotificationStore();

  if (notifications.length === 0) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 space-y-2 max-w-sm w-full">
      {notifications.map((n) => (
        <div
          key={n.id}
          className={`p-3 rounded-lg border shadow-lg flex items-center justify-between transition-all ${
            n.type === 'success'
              ? 'bg-emerald-950/90 border-emerald-500/40 text-emerald-300'
              : n.type === 'error'
              ? 'bg-rose-950/90 border-rose-500/40 text-rose-300'
              : 'bg-indigo-950/90 border-indigo-500/40 text-indigo-300'
          }`}
        >
          <div className="flex items-center gap-2 text-xs">
            {n.type === 'success' && <CheckCircle className="w-4 h-4 text-emerald-400" />}
            {n.type === 'error' && <AlertCircle className="w-4 h-4 text-rose-400" />}
            {n.type === 'info' && <Info className="w-4 h-4 text-indigo-400" />}
            <span>{n.message}</span>
          </div>

          <button
            type="button"
            onClick={() => removeNotification(n.id)}
            className="p-0.5 hover:bg-slate-800 rounded"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
};
