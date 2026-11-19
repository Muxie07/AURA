'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import Sidebar from './Sidebar';
import Topnav from './Topnav';
import RightPanel from './RightPanel';

const PUBLIC_PATHS = ['/login'];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const isPublic = PUBLIC_PATHS.includes(pathname);
  const [checked, setChecked] = useState(false);
  const isConversationsPage = pathname === '/conversations';
  // Default right panel to closed on /conversations to give chat maximum breathing room, open on other pages
  const [rightPanelOpen, setRightPanelOpen] = useState(!isConversationsPage);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token && !isPublic) {
      router.replace('/login');
    } else {
      setChecked(true);
    }
  }, [pathname, isPublic, router]);

  // Keep right panel closed when switching to conversations, but respect user toggles
  useEffect(() => {
    if (pathname === '/conversations') {
      setRightPanelOpen(false);
    }
  }, [pathname]);

  // Login page — no shell, render children directly
  if (isPublic) {
    return <>{children}</>;
  }

  // Auth-gated pages — clean Pulse-style loading state
  if (!checked) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-chart-1 flex items-center justify-center animate-pulse shadow-sm">
            <span className="text-primary-foreground font-bold text-sm">A</span>
          </div>
          <p className="text-xs text-muted-foreground font-mono animate-pulse">Initializing AURA Enterprise...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen h-[100dvh] w-screen max-w-full overflow-hidden bg-background text-foreground">
      {/* Left Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex flex-col flex-1 min-w-0 h-full overflow-hidden">
        <Topnav
          rightPanelOpen={rightPanelOpen}
          onToggleRightPanel={() => setRightPanelOpen(!rightPanelOpen)}
        />
        <main
          className={`flex-1 min-h-0 bg-background overflow-y-auto ${
            isConversationsPage ? 'p-2 sm:p-4' : 'p-6 lg:p-8'
          }`}
        >
          <div className={`animate-fade-in ${isConversationsPage ? 'h-full flex flex-col' : 'max-w-7xl mx-auto'}`}>
            {children}
          </div>
        </main>
      </div>

      {/* Right Operational Panel */}
      <RightPanel
        isOpen={rightPanelOpen}
        onToggle={() => setRightPanelOpen(!rightPanelOpen)}
      />
    </div>
  );
}
