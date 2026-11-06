'use client';
import { useState, useEffect } from 'react';
import { Bell, Search, Shield, ChevronDown, LogOut, CheckCircle2 } from 'lucide-react';
import { logout } from '../lib/api';

export default function Topnav() {
  const [userName, setUserName] = useState<string>('Enterprise Operator');
  const [tenantName, setTenantName] = useState<string>('Production Org');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedName = localStorage.getItem('full_name');
      if (storedName) setUserName(storedName);
      const org = localStorage.getItem('organization_id');
      if (org) setTenantName(`Tenant (${org.slice(0, 8)}...)`);
    }
  }, []);

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200/80 bg-white/90 backdrop-blur-md px-6 z-10 transition-colors">
      {/* Global Search Bar */}
      <div className="flex items-center gap-3 w-96">
        <div className="relative w-full">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search agents, workflows, knowledge or executions..."
            className="w-full rounded-lg border border-slate-200 bg-slate-50/60 pl-9 pr-3 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all"
          />
        </div>
      </div>

      {/* Right controls: Health status, notification, user menu */}
      <div className="flex items-center gap-4">
        {/* System Health Badge */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200/60 text-emerald-700 text-xs font-medium">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span>Engine Online</span>
        </div>

        {/* Security / Compliance Badge */}
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-100 text-slate-600 text-xs font-medium">
          <Shield className="h-3.5 w-3.5 text-blue-600" />
          <span>RBAC Enforced</span>
        </div>

        <div className="h-4 w-px bg-slate-200" />

        {/* Notifications */}
        <button
          type="button"
          aria-label="Notifications"
          className="relative p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
        >
          <Bell className="h-4 w-4" />
          <span className="absolute top-1 right-1 h-1.5 w-1.5 rounded-full bg-blue-600" />
        </button>

        {/* User Profile Menu */}
        <div className="relative">
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="flex items-center gap-2.5 rounded-lg p-1.5 hover:bg-slate-50 transition-colors text-left"
          >
            <div className="h-7 w-7 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-600 text-white flex items-center justify-center font-bold text-xs shadow-xs">
              {userName.charAt(0).toUpperCase()}
            </div>
            <div className="hidden lg:block text-left">
              <p className="text-xs font-semibold text-slate-900 leading-tight">{userName}</p>
              <p className="text-[10px] text-slate-500 leading-tight">{tenantName}</p>
            </div>
            <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
          </button>

          {isDropdownOpen && (
            <div className="absolute right-0 mt-2 w-56 rounded-xl border border-slate-200 bg-white py-1.5 shadow-lg ring-1 ring-black/5 z-50">
              <div className="px-4 py-2 border-b border-slate-100">
                <p className="text-xs font-semibold text-slate-900">{userName}</p>
                <p className="text-[11px] text-slate-500 truncate">{tenantName}</p>
              </div>
              <div className="py-1">
                <a
                  href="/settings"
                  className="block px-4 py-1.5 text-xs text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  Organization Settings
                </a>
                <a
                  href="/audit"
                  className="block px-4 py-1.5 text-xs text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  My Audit Records
                </a>
              </div>
              <div className="border-t border-slate-100 pt-1">
                <button
                  onClick={() => logout()}
                  className="w-full flex items-center gap-2 px-4 py-1.5 text-xs text-red-600 hover:bg-red-50 transition-colors"
                >
                  <LogOut className="h-3.5 w-3.5" />
                  Sign Out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
