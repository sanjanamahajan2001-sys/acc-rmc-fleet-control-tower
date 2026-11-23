import { useAuthStore } from '../store/auth';
import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Header } from './Header';
import { TopToolbar } from './TopToolbar';
import { Sidebar } from './Sidebar';
import { Breadcrumb } from './Breadcrumb';
import { ContentArea } from './ContentArea';
import { Footer } from './Footer';

import { DashboardFilterProvider } from '../modules/site_dashboard/orchestration/DashboardFilterProvider';

export const AppLayout: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const fetchCurrentUser = useAuthStore((s) => s.fetchCurrentUser);

  React.useEffect(() => {
    fetchCurrentUser();
  }, [fetchCurrentUser]);

  return (
    <DashboardFilterProvider>
      <div className="flex flex-col h-screen w-screen overflow-hidden text-[#172033]" style={{ backgroundColor: '#F4F6F9' }}>
        <Header onToggleMobileMenu={() => setMobileMenuOpen((prev) => !prev)} />
        <TopToolbar />
        
        <div className="flex flex-1 overflow-hidden relative" style={{ backgroundColor: '#F4F6F9' }}>
          {/* Desktop & Tablet Permanent / Collapsed Sidebar */}
          <div className="hidden md:flex shrink-0">
            <Sidebar />
          </div>

          {/* Mobile Slide-Out Drawer Navigation Overlay */}
          {mobileMenuOpen && (
            <div className="fixed inset-0 z-50 flex md:hidden">
              <div
                className="fixed inset-0 bg-slate-950/40 backdrop-blur-sm transition-opacity"
                onClick={() => setMobileMenuOpen(false)}
              />
              <div className="relative z-10 w-72 max-w-[80vw] bg-white border-r border-slate-200 flex flex-col h-full shadow-2xl">
                <Sidebar onNavigate={() => setMobileMenuOpen(false)} />
              </div>
            </div>
          )}

          <ContentArea>
            <Breadcrumb />
            <Outlet />
          </ContentArea>
        </div>
        <Footer />
      </div>
    </DashboardFilterProvider>
  );
};
