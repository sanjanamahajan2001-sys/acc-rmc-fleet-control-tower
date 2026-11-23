import React, { useState } from 'react';
import { ChevronRight } from 'lucide-react';
import { IconSettingsCog, IconBatchingPlantFactory, IconDatasetDatabase } from '../../../components/icons/LinealColorIcons';
import { CompanyCustomerSettingsSection } from '../components/CompanyCustomerSettingsSection';
import { DatabasePreviewSection } from '../components/DatabasePreviewSection';
import { SyncStatusHeaderBadge } from '../../site_dashboard/components/SyncStatusHeaderBadge';
import { DashboardSyncProvider } from '../../site_dashboard/orchestration/DashboardSyncProvider';

interface ConfigurationCategory {
  id: string;
  category_name: string;
  display_name: string;
  icon: string;
  display_order: number;
  description?: string;
}

const categoryIcons: Record<string, React.ReactNode> = {
  customers: <IconBatchingPlantFactory className="w-4 h-4" />,
  database_preview: <IconDatasetDatabase className="w-4 h-4" />,
};

// Manager requirement: Safely hide DB preview pane without removing code
const SHOW_DB_PREVIEW = false;

export const PlatformSettingsPage: React.FC = () => {
  const [categories] = useState<ConfigurationCategory[]>([
    {
      id: 'cat-cust',
      category_name: 'customers',
      display_name: 'Company & Customer Accounts',
      icon: 'Building',
      display_order: 5,
      description: 'Customer display overrides, plant mappings & entity management',
    },
    ...(SHOW_DB_PREVIEW
      ? [
          {
            id: 'cat-db-preview',
            category_name: 'database_preview',
            display_name: 'Database Preview',
            icon: 'Database',
            display_order: 10,
            description: 'Live PostgreSQL schema introspection, foreign key mapping & DDL export',
          },
        ]
      : []),
  ]);
  const [activeCategory, setActiveCategory] = useState<string>('customers');

  return (
    <DashboardSyncProvider onRefreshNeeded={() => {}}>
      <div className="min-h-screen bg-slate-50 p-4 md:p-5 space-y-6 text-slate-800">
        {/* Platform Settings Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-lg bg-white shadow-xs border border-slate-200/90">
          <div className="flex items-center gap-3">
            <IconSettingsCog className="w-7 h-7 shrink-0" />
            <div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900">
                Platform Configuration Registry
              </h1>
              <p className="text-xs font-medium text-slate-500">
                Centralized Operational Settings, Company &amp; Customer Accounts
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <SyncStatusHeaderBadge />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Left Sidebar: Configuration Domains */}
          <div className="lg:col-span-1 space-y-1.5 p-3 rounded-lg border border-slate-200/90 bg-white shadow-xs h-fit">
            <div className="px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Configuration Domains
            </div>

            {categories.map((cat) => {
              const isActive = activeCategory === cat.category_name;
              return (
                <button
                  key={cat.category_name}
                  type="button"
                  onClick={() => setActiveCategory(cat.category_name)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-xs font-bold transition-colors border ${
                    isActive
                      ? 'bg-blue-700 border-blue-700 text-white shadow-xs'
                      : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    {categoryIcons[cat.category_name] || <IconSettingsCog className="w-4 h-4" />}
                    <span className="truncate">{cat.display_name}</span>
                  </div>
                  <ChevronRight className={`w-3.5 h-3.5 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                </button>
              );
            })}
          </div>

          {/* Right Main Content Pane */}
          <div className="lg:col-span-3 space-y-6">
            {activeCategory === 'customers' ? (
              <CompanyCustomerSettingsSection />
            ) : SHOW_DB_PREVIEW && activeCategory === 'database_preview' ? (
              <DatabasePreviewSection />
            ) : (
              <CompanyCustomerSettingsSection />
            )}
          </div>
        </div>
      </div>
    </DashboardSyncProvider>
  );
};

export default PlatformSettingsPage;
