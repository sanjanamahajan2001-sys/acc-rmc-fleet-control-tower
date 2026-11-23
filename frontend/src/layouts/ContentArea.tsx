import React from 'react';

export const ContentArea: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="flex-1 p-2 sm:p-4 md:p-5 overflow-y-auto flex flex-col gap-3 sm:gap-4 bg-[#F4F6F9] text-[#172033] min-w-0 w-full">
      {children}
    </div>
  );
};
