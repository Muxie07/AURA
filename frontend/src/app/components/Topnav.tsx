'use client';

import { useState, useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import Link from 'next/link';
import { 
  Bell, 
  Plus, 
  Shield, 
  ChevronDown, 
  LogOut, 
  SidebarOpen, 
  SidebarClose, 
  Sliders, 
  Play,
  Sparkles
} from 'lucide-react';
import { fetchApi, logout } from '../lib/api';
import { cn } from '../lib/utils';

const routeHeaders: Record<string, { title: string; subtitle: string; actionLabel: string; actionHref: string }> = {
  '/': {
    title: 'Overview',
    subtitle: 'Runs, success rate and pending approvals',
    actionLabel: 'New Execution',
    actionHref: '/conversations',
  },
  '/agents': {
    title: 'Studio',
    subtitle: 'Build and manage your AI agents',
    actionLabel: 'Create Agent',
    actionHref: '/studio/agent',
  },
  '/studio/agent': {
    title: 'Agent Studio',
    subtitle: 'Agent Instructions, LLM Providers, Tools & Testing',
    actionLabel: 'New Agent',
    actionHref: '/studio/agent',
  },
  '/workflows': {
    title: 'Workflows',
    subtitle: 'Orchestrate agents, tools and approvals on a canvas',
    actionLabel: 'New Pipeline',
    actionHref: '/workflows',
  },
  '/executions': {
    title: 'Logs',
    subtitle: 'Every run, step, tool call and token count',
    actionLabel: 'Run Agent',
    actionHref: '/conversations',
  },
  '/approvals': {
    title: 'Approvals',
    subtitle: 'Human review for risky agent actions',
    actionLabel: 'Review Requests',
    actionHref: '/approvals',
  },
  '/knowledge': {
    title: 'Knowledge',
    subtitle: 'Documents your agents can search',
    actionLabel: 'Add Document',
    actionHref: '/knowledge',
  },
  '/tools': {
    title: 'Tools',
    subtitle: 'Capabilities agents can call, by risk level',
    actionLabel: 'View Registry',
    actionHref: '/tools',
  },
  '/mcp': {
    title: 'MCP Servers',
    subtitle: 'Connect external tool servers over MCP',
    actionLabel: 'Connect Server',
    actionHref: '/mcp',
  },
  '/analytics': {
    title: 'Agent Performance',
    subtitle: 'Token Expenditure, Model Routing & Latency Percentiles',
    actionLabel: 'Export Data',
    actionHref: '/analytics',
  },
  '/audit': {
    title: 'Audit Log',
    subtitle: 'Security events and access history',
    actionLabel: 'Filter Logs',
    actionHref: '/audit',
  },
  '/settings': {
    title: 'Settings',
    subtitle: 'Model providers and workspace configuration',
    actionLabel: 'Save Changes',
    actionHref: '/settings',
  },
  '/conversations': {
    title: 'Chat',
    subtitle: 'Talk to an agent and watch it work',
    actionLabel: 'New Session',
    actionHref: '/conversations',
  },
};

export default function Topnav() {
  const pathname = usePathname();
  const [userName, setUserName] = useState<string>('Enterprise Operator');
  const [tenantName, setTenantName] = useState<string>('Production Org');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState<number>(0);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedName = localStorage.getItem('full_name');
      if (storedName) setUserName(storedName);
      const org = localStorage.getItem('organization_id');
      if (org) setTenantName(`Tenant (${org.slice(0, 8)}...)`);
    }

    async function checkApprovals() {
      try {
        const res = await fetchApi('/approvals');
        if (res.ok) {
          const json = await res.json();
          const list = json.approvals || [];
          const count = list.filter((a: any) => a.status === 'PENDING').length;
          setPendingApprovalsCount(count);
        }
      } catch {}
    }
    checkApprovals();
  }, [pathname]);

  const currentRouteConfig = routeHeaders[pathname] || {
    title: 'AURA Platform',
    subtitle: 'Enterprise AI Agent Orchestration',
    actionLabel: 'Action',
    actionHref: '/',
  };

  return (
    <header className="h-16 px-6 flex items-center justify-between border-b border-border bg-card shrink-0 select-none z-10 transition-colors">
      {/* Title & Subtitle */}
      <div>
        <h1 className="text-base font-semibold text-foreground tracking-tight leading-tight">
          {currentRouteConfig.title}
        </h1>
        <p className="text-xs text-muted-foreground leading-tight mt-0.5">
          {currentRouteConfig.subtitle}
        </p>
      </div>

      {/* Action Controls matching Pulse Header */}
      <div className="flex items-center gap-2.5">
        {/* Alerts / Pending Approvals Bell */}
        <Link
          href="/approvals"
          className="relative p-2 rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          title={pendingApprovalsCount > 0 ? `${pendingApprovalsCount} pending approvals` : 'System notifications'}
        >
          <Bell className="w-4 h-4" />
          {pendingApprovalsCount > 0 && (
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-destructive rounded-full animate-pulse" />
          )}
        </Link>

        {/* Primary Page Action Button */}
        {currentRouteConfig.actionHref !== pathname && (
          <Link
            href={currentRouteConfig.actionHref}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-semibold shadow-xs transition-colors shrink-0"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>{currentRouteConfig.actionLabel}</span>
          </Link>
        )}
      </div>
    </header>
  );
}
