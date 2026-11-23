import React from 'react';

export const PageContainer: React.FC<{ children: React.ReactNode; title?: string }> = ({ children, title }) => {
  return (
    <div className="rounded-xl border shadow-xs p-3 sm:p-4 md:p-5 bg-[#F4F6F9] border-[#DCE2EA] min-w-0 w-full">
      {title && <h1 className="text-base sm:text-lg font-bold text-[#172033] mb-3 sm:mb-4">{title}</h1>}
      {children}
    </div>
  );
};
