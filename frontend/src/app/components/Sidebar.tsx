'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '../lib/utils';
import { fetchApi, logout } from '../lib/api';
import {
  LayoutDashboard,
  Bot,
  GitFork,
  BookOpen,
  Boxes,
  Wrench,
  CheckCircle2,
  PlaySquare,
  ScrollText,
  Settings,
  MessagesSquare,
  Mail,
  Moon,
  Sun,
  Zap,
  LogOut,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

interface NavItem {
  name: string;
  href: string;
  icon: LucideIcon;
  badge?: number | string;
  badgeColor?: 'red' | 'yellow' | 'green';
}

const buildItems: NavItem[] = [
  { name: 'Studio', href: '/agents', icon: Bot },
  { name: 'Workflows', href: '/workflows', icon: GitFork },
  { name: 'Knowledge', href: '/knowledge', icon: BookOpen },
  { name: 'Tools', href: '/tools', icon: Wrench },
  { name: 'MCP Servers', href: '/mcp', icon: Boxes },
];

const runItems: NavItem[] = [
  { name: 'Overview', href: '/', icon: LayoutDashboard },
  { name: 'Chat', href: '/conversations', icon: MessagesSquare },
  { name: 'Approvals', href: '/approvals', icon: CheckCircle2, badgeColor: 'red' },
  { name: 'Logs', href: '/executions', icon: PlaySquare },
];

const workspaceItems: NavItem[] = [
  { name: 'Integrations', href: '/settings#integrations', icon: Mail },
  { name: 'Audit Log', href: '/audit', icon: ScrollText },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [userName, setUserName] = useState<string>('Enterprise Operator');
  const [userRole, setUserRole] = useState<string>('AI Operations Lead');
  const [userInitials, setUserInitials] = useState<string>('EO');
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState<number>(0);
  const [isDarkMode, setIsDarkMode] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedName = localStorage.getItem('full_name') || 'Enterprise Operator';
      setUserName(storedName);
      const initials = storedName
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2);
      setUserInitials(initials || 'EO');

      const org = localStorage.getItem('organization_id');
      if (org) {
        setUserRole(`Org: ${org.slice(0, 8)}...`);
      }
    }

    // Fetch real pending approvals count
    async function loadApprovals() {
      try {
        const res = await fetchApi('/approvals');
        if (res.ok) {
          const json = await res.json();
          const list = json.approvals || [];
          const pending = list.filter((a: any) => a.status === 'PENDING').length;
          setPendingApprovalsCount(pending);
        }
      } catch (err) {
        // Quiet fallback
      }
    }
    loadApprovals();
  }, [pathname]);

  const toggleTheme = () => {
    setIsDarkMode(!isDarkMode);
    if (typeof document !== 'undefined') {
      document.documentElement.classList.toggle('dark');
    }
  };

  return (
    <aside className="w-[260px] h-screen bg-card border-r border-border flex flex-col shrink-0 select-none z-20">
      {/* Brand Header */}
      <div className="h-16 px-5 flex items-center gap-3 border-b border-border shrink-0">
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="w-9 h-9 rounded-xl bg-chart-1 flex items-center justify-center shadow-xs group-hover:scale-105 transition-transform">
            <Zap className="w-5 h-5 text-primary-foreground" />
          </div>
          <div>
            <span className="font-semibold text-foreground text-[15px] tracking-tight block leading-tight">
              AURA
            </span>
            <span className="text-[10px] text-muted-foreground font-mono block">Enterprise AI</span>
          </div>
        </Link>
      </div>

      {/* Navigation Links Scroll Area */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-5">
        {[
          { label: 'Build', items: buildItems },
          { label: 'Run', items: runItems },
          { label: 'Workspace', items: workspaceItems },
        ].map((section) => (
          <div key={section.label}>
            <p className="px-3 mb-1.5 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
              {section.label}
            </p>
            <nav className="space-y-0.5">
              {section.items.map((item) => {
                const base = item.href.split('#')[0];
                const isActive = base === '/' ? pathname === '/' : pathname === base || pathname.startsWith(base + '/');
                const badge = item.name === 'Approvals' && pendingApprovalsCount > 0 ? pendingApprovalsCount : undefined;
                return <NavButton key={item.href} item={{ ...item, badge }} isActive={isActive} />;
              })}
            </nav>
          </div>
        ))}
      </div>

      {/* User Footer with Theme Toggle and Logout */}
      <div className="p-3 border-t border-border bg-card shrink-0 space-y-2">
        <div className="flex items-center gap-2.5 p-2 rounded-xl bg-muted/40 hover:bg-muted/70 transition-colors">
          <div className="w-8 h-8 rounded-full bg-chart-1/20 text-chart-1 flex items-center justify-center font-medium text-xs shrink-0">
            {userInitials}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-foreground truncate leading-tight">{userName}</p>
            <p className="text-[10px] text-muted-foreground truncate leading-tight">{userRole}</p>
          </div>
          <button
            type="button"
            onClick={toggleTheme}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-background transition-colors"
            title="Toggle theme"
          >
            {isDarkMode ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
          </button>
          <button
            type="button"
            onClick={logout}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
            title="Sign out"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </aside>
  );
}

function NavButton({ item, isActive }: { item: NavItem; isActive: boolean }) {
  const Icon = item.icon;

  const badgeColorClass = {
    red: 'bg-destructive/15 text-destructive font-semibold',
    yellow: 'bg-warning/20 text-warning font-semibold',
    green: 'bg-success/15 text-success font-semibold',
  };

  return (
    <Link
      href={item.href}
      className={cn(
        'w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs transition-all duration-200',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        isActive
          ? 'bg-primary text-primary-foreground font-semibold shadow-xs'
          : 'text-foreground/75 hover:bg-muted/80 hover:text-foreground'
      )}
    >
      <Icon className={cn('w-4 h-4 shrink-0', isActive ? 'text-primary-foreground' : 'text-muted-foreground')} />
      <span className="flex-1 text-left truncate">{item.name}</span>
      {item.badge !== undefined && item.badge !== null && item.badge !== 0 && (
        <span
          className={cn(
            'text-[10px] px-1.5 py-0.5 rounded-full font-mono shrink-0',
            isActive
              ? 'bg-primary-foreground/20 text-primary-foreground'
              : item.badgeColor
              ? badgeColorClass[item.badgeColor]
              : 'bg-muted text-muted-foreground'
          )}
        >
          {item.badge}
        </span>
      )}
    </Link>
  );
}
