import React from 'react';
import { TMDetailsRow, TMDetailItem } from './TMDetailsRow';

interface TMDetailsTableProps {
  items: TMDetailItem[];
  isDark?: boolean;
}

export const TMDetailsTable: React.FC<TMDetailsTableProps> = ({ items, isDark }) => {
  if (isDark) {
    return (
      <div className="overflow-x-auto border border-slate-800 rounded-md bg-slate-950">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-900 text-slate-400 font-sans text-[10px] uppercase font-bold border-b border-slate-800">
            <tr>
              <th className="px-3 py-2.5 text-left font-bold text-slate-300">TM No.</th>
              <th className="px-3 py-2.5 text-center font-bold text-slate-300">Site In<br/><span className="text-[9px] text-slate-500 font-normal">(Arrived)</span></th>
              <th className="px-3 py-2.5 text-center font-bold text-slate-300">Unloading Start</th>
              <th className="px-3 py-2.5 text-center font-bold text-slate-300">Unloading End</th>
              <th className="px-3 py-2.5 text-center font-bold text-slate-300">Site Out</th>
              <th className="px-3 py-2.5 text-center font-bold text-slate-300">Holding<br/><span className="text-[9px] text-slate-500 font-normal">(Site In → Start)</span></th>
              <th className="px-3 py-2.5 text-center font-bold text-slate-300">Retention<br/><span className="text-[9px] text-slate-500 font-normal">(End → Out)</span></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-medium">
            {items.map((item, idx) => (
              <TMDetailsRow key={`${item.tm_no}-${item.dispatch_id}-${idx}`} item={item} isDark={true} />
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto border border-slate-200/90 rounded-md bg-white">
      <table className="w-full text-left text-xs">
        <thead className="bg-slate-50 text-slate-600 font-sans text-[10px] uppercase font-bold border-b border-slate-200">
          <tr>
            <th className="px-3 py-2 text-left font-bold text-slate-700">TM No.</th>
            <th className="px-3 py-2 text-center font-bold text-slate-700">Site In<br/><span className="text-[9px] text-slate-400 font-normal">(Arrived)</span></th>
            <th className="px-3 py-2 text-center font-bold text-slate-700">Unloading Start</th>
            <th className="px-3 py-2 text-center font-bold text-slate-700">Unloading End</th>
            <th className="px-3 py-2 text-center font-bold text-slate-700">Site Out</th>
            <th className="px-3 py-2 text-center font-bold text-slate-700">Holding<br/><span className="text-[9px] text-slate-400 font-normal">(Site In → Start)</span></th>
            <th className="px-3 py-2 text-center font-bold text-slate-700">Retention<br/><span className="text-[9px] text-slate-400 font-normal">(End → Out)</span></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 font-medium">
          {items.map((item, idx) => (
            <TMDetailsRow key={`${item.tm_no}-${item.dispatch_id}-${idx}`} item={item} />
          ))}
        </tbody>
      </table>
    </div>
  );
};

