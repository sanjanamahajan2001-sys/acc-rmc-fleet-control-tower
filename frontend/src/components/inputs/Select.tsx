import React from 'react';

export interface SelectOption {
  label: string;
  value: string | number;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: SelectOption[];
  error?: string;
}

export const Select: React.FC<SelectProps> = ({ label, options, error, className = '', ...props }) => (
  <div className="flex flex-col gap-1">
    {label && <label className="text-xs text-slate-600 font-semibold">{label}</label>}
    <select
      className={`bg-white border rounded-md px-3 py-1.5 text-xs text-slate-800 outline-none transition-colors focus:border-blue-600 ${
        error ? 'border-rose-500' : 'border-slate-200'
      } ${className}`}
      {...props}
    >
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
    {error && <span className="text-[11px] text-rose-600 font-medium">{error}</span>}
  </div>
);
