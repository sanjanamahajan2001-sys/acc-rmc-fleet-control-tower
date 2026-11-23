import React from 'react';

export interface TextInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const TextInput: React.FC<TextInputProps> = ({ label, error, className = '', ...props }) => (
  <div className="flex flex-col gap-1">
    {label && <label className="text-xs text-slate-600 font-semibold">{label}</label>}
    <input
      className={`bg-white border rounded-md px-3 py-1.5 text-xs text-slate-800 placeholder:text-slate-400 outline-none transition-colors focus:border-blue-600 ${
        error ? 'border-rose-500' : 'border-slate-200'
      } ${className}`}
      {...props}
    />
    {error && <span className="text-[11px] text-rose-600 font-medium">{error}</span>}
  </div>
);
