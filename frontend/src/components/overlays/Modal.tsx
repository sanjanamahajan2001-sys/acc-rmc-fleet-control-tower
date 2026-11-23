import React from 'react';
import { X } from 'lucide-react';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children, footer }) => {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg bg-white rounded-lg border border-slate-200/90 shadow-2xl p-6 text-slate-800 transition-all"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center pb-3 mb-4 border-b border-slate-100">
          <h3 className="text-base font-bold text-slate-900">{title}</h3>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-slate-600 rounded-md transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="text-xs text-slate-700 mb-5">{children}</div>
        {footer && <div className="flex justify-end gap-2.5 pt-3 border-t border-slate-100">{footer}</div>}
      </div>
    </div>
  );
};
