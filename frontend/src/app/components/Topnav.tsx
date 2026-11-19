'use client';

import { useState, useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import Link from 'next/link';
import { 
  Bell, 
  Calendar, 
  RefreshCw, 
  Plus, 
  Shield, 
  ChevronDown, 
  LogOut, 
  SidebarOpen, 
  SidebarClose, 
  Sliders, 
  Play,
  PanelRightClose,
  PanelRightOpen,
  Sparkles
} from 'lucide-react';
import { fetchApi, logout } from '../lib/api';
import { cn } from '../lib/utils';

const routeHeaders: Record<string, { title: string; subtitle: string; actionLabel: string; actionHref: string }> = {
  '/': {
    title: 'AURA Overview',
    subtitle: 'Real-time Autonomous Agent Metrics & Telemetry',
    actionLabel: 'New Execution',
    actionHref: '/conversations',
  },
  '/agents': {
    title: 'Agent Directory',
    subtitle: 'Enterprise Autonomous Agents & Service Catalog',
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
    title: 'Workflow Studio',
    subtitle: 'Multi-Agent Orchestration & Deterministic Pipelines',
    actionLabel: 'New Pipeline',
    actionHref: '/workflows',
  },
  '/executions': {
    title: 'Executions & Monitoring',
    subtitle: 'Execution Traces, Decisions, Latency & Token Usage',
    actionLabel: 'Run Agent',
    actionHref: '/conversations',
  },
  '/approvals': {
    title: 'Action Approvals',
    subtitle: 'Human-in-the-Loop Governance & Authorization Gates',
    actionLabel: 'Review Requests',
    actionHref: '/approvals',
  },
  '/knowledge': {
    title: 'Knowledge Bases',
    subtitle: 'Enterprise RAG Documents, Chunking & Vector Store',
    actionLabel: 'Add Document',
    actionHref: '/knowledge',
  },
  '/tools': {
    title: 'Tool Registry',
    subtitle: 'Enterprise Capabilities, Permissions & Security Risk Tiers',
    actionLabel: 'View Registry',
    actionHref: '/tools',
  },
  '/mcp': {
    title: 'MCP Integrations',
    subtitle: 'Model Context Protocol Servers & SSE Transports',
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
    title: 'Error Tracking & Audit',
    subtitle: 'Security Events, Tenant Access & Exception Tracing',
    actionLabel: 'Filter Logs',
    actionHref: '/audit',
  },
  '/settings': {
    title: 'Platform Settings',
    subtitle: 'Model Provider Credentials & Tenant Configuration',
    actionLabel: 'Save Changes',
    actionHref: '/settings',
  },
  '/conversations': {
    title: 'Live Agent Chat',
    subtitle: 'Autonomous Execution, Quotation & Invoicing Copilot',
    actionLabel: 'New Session',
    actionHref: '/conversations',
  },
};

interface TopnavProps {
  rightPanelOpen?: boolean;
  onToggleRightPanel?: () => void;
}

export default function Topnav({ rightPanelOpen = true, onToggleRightPanel }: TopnavProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [userName, setUserName] = useState<string>('Enterprise Operator');
  const [tenantName, setTenantName] = useState<string>('Production Org');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState<number>(0);
  const [isRefreshing, setIsRefreshing] = useState(false);

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

  const handleRefresh = () => {
    setIsRefreshing(true);
    router.refresh();
    setTimeout(() => setIsRefreshing(false), 800);
  };

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
        {/* Time Range Selector */}
        <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-border bg-muted/40 text-xs text-foreground font-medium">
          <Calendar className="w-3.5 h-3.5 text-muted-foreground" />
          <span>Last 24 hours</span>
        </div>

        {/* Refresh button */}
        <button
          type="button"
          onClick={handleRefresh}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-border bg-card hover:bg-muted text-xs text-foreground font-medium transition-colors"
          title="Refresh current page"
        >
          <RefreshCw className={cn('w-3.5 h-3.5 text-muted-foreground', isRefreshing && 'animate-spin')} />
          <span className="hidden md:inline">Refresh</span>
        </button>

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

        {/* Right Panel Toggle Button */}
        {onToggleRightPanel && (
          <button
            type="button"
            onClick={onToggleRightPanel}
            className={cn(
              'p-2 rounded-xl transition-colors',
              rightPanelOpen ? 'bg-muted text-foreground' : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            )}
            title={rightPanelOpen ? 'Collapse live operations panel' : 'Expand live operations panel'}
          >
            {rightPanelOpen ? <PanelRightClose className="w-4 h-4" /> : <PanelRightOpen className="w-4 h-4" />}
          </button>
        )}

        {/* Primary Page Action Button */}
        <Link
          href={currentRouteConfig.actionHref}
          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-semibold shadow-xs transition-colors shrink-0"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>{currentRouteConfig.actionLabel}</span>
        </Link>
      </div>
    </header>
  );
}
