'use client';
import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import Sidebar from './Sidebar';
import Topnav from './Topnav';

const PUBLIC_PATHS = ['/login'];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const isPublic = PUBLIC_PATHS.includes(pathname);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token && !isPublic) {
      router.replace('/login');
    } else {
      setChecked(true);
    }
  }, [pathname, isPublic, router]);

  // Login page — no shell, just render children directly
  if (isPublic) {
    return <>{children}</>;
  }

  // Auth-gated pages — show spinner until we know we're authenticated
  if (!checked) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500 text-sm">Loading...</div>
      </div>
    );
  }

  const isConversationsPage = pathname === '/conversations';

  return (
    <div className="flex h-screen h-[100dvh] w-screen max-w-full overflow-hidden bg-gray-50">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0 h-full overflow-hidden">
        <Topnav />
        <main
          className={`flex-1 min-h-0 bg-gray-50 ${
            isConversationsPage
              ? 'overflow-hidden flex flex-col p-2 sm:p-4'
              : 'overflow-y-auto'
          }`}
        >
          {isConversationsPage ? (
            <div className="flex-1 min-h-0 h-full flex flex-col">
              {children}
            </div>
          ) : (
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
              {children}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
