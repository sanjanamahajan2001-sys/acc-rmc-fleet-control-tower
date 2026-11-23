import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  icon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  icon,
  className = '',
  disabled,
  ...props
}) => {
  const getVariantClasses = () => {
    if (disabled) return 'bg-slate-200 text-slate-400 border-slate-200 cursor-not-allowed';
    switch (variant) {
      case 'primary':
        return 'bg-blue-700 hover:bg-blue-800 text-white border-transparent shadow-xs';
      case 'secondary':
        return 'bg-white hover:bg-slate-50 text-slate-700 border-slate-200 shadow-xs';
      case 'danger':
        return 'bg-rose-600 hover:bg-rose-700 text-white border-transparent shadow-xs';
      case 'outline':
        return 'bg-transparent hover:bg-slate-50 text-slate-700 border-slate-300';
    }
  };

  const getSizeClasses = () => {
    switch (size) {
      case 'sm':
        return 'px-2.5 py-1 text-xs';
      case 'lg':
        return 'px-4 py-2 text-sm';
      default:
        return 'px-3 py-1.5 text-xs';
    }
  };

  return (
    <button
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-1.5 font-bold rounded-md border transition-colors ${getVariantClasses()} ${getSizeClasses()} ${className}`}
      {...props}
    >
      {icon && <span>{icon}</span>}
      {children}
    </button>
  );
};
