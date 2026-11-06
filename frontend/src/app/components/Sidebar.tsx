'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard,
  Bot,
  Sliders,
  GitFork,
  BookOpen,
  Boxes,
  ShieldCheck,
  PlaySquare,
  CheckCircle2,
  ScrollText,
  BarChart3,
  Cpu,
  Users2,
  Settings,
  MessagesSquare
} from 'lucide-react';

export interface NavItem {
  name: string;
  href: string;
  icon: any;
  badge?: string;
  category?: string;
}

export const navigationCategories = [
  {
    category: 'Core Operations',
    items: [
      { name: 'Overview', href: '/', icon: LayoutDashboard },
      { name: 'Conversations', href: '/conversations', icon: MessagesSquare },
      { name: 'Agents', href: '/agents', icon: Bot },
      { name: 'Agent Studio', href: '/studio/agent', icon: Sliders },
      { name: 'Workflows', href: '/workflows', icon: GitFork },
      { name: 'Executions', href: '/executions', icon: PlaySquare },
      { name: 'Approvals', href: '/approvals', icon: CheckCircle2 },
    ]
  },
  {
    category: 'Knowledge & Integrations',
    items: [
      { name: 'Knowledge Bases', href: '/knowledge', icon: BookOpen },
      { name: 'MCP Integrations', href: '/mcp', icon: Boxes },
      { name: 'Tools & Permissions', href: '/tools', icon: ShieldCheck },
    ]
  },
  {
    category: 'Governance & Analytics',
    items: [
      { name: 'Audit & Activity', href: '/audit', icon: ScrollText },
      { name: 'Analytics', href: '/analytics', icon: BarChart3 },
      { name: 'Model Providers', href: '/models', icon: Cpu },
      { name: 'Team & Tenants', href: '/tenants', icon: Users2 },
      { name: 'Settings', href: '/settings', icon: Settings },
    ]
  }
];

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ');
}

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-64 flex-col border-r border-slate-200/80 bg-white shadow-sm transition-all duration-200">
      {/* Brand Header */}
      <div className="flex h-16 shrink-0 items-center justify-between px-6 border-b border-slate-100 bg-slate-50/50">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-600 text-white shadow-sm ring-1 ring-blue-500/20 font-bold text-lg">
            A
          </div>
          <div>
            <span className="text-base font-bold tracking-tight text-slate-900 block leading-tight">AURA</span>
            <span className="text-[10px] font-medium uppercase tracking-wider text-slate-500 block">Enterprise AI</span>
          </div>
        </Link>
        <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
          v2.4 Live
        </span>
      </div>

      {/* Nav Content */}
      <nav className="flex flex-1 flex-col overflow-y-auto px-3.5 py-4 space-y-6">
        {navigationCategories.map((group) => (
          <div key={group.category} className="space-y-1">
            <h2 className="px-2.5 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
              {group.category}
            </h2>
            <div className="space-y-0.5 mt-1.5">
              {group.items.map((item) => {
                const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
                const Icon = item.icon;
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={classNames(
                      isActive
                        ? 'bg-blue-50 text-blue-700 font-semibold shadow-xs border-l-2 border-blue-600'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50/80 font-medium',
                      'group flex items-center justify-between rounded-md px-2.5 py-2 text-xs transition-colors'
                    )}
                  >
                    <div className="flex items-center gap-2.5 truncate">
                      <Icon
                        className={classNames(
                          isActive ? 'text-blue-600' : 'text-slate-400 group-hover:text-slate-600',
                          'h-4 w-4 shrink-0 transition-colors'
                        )}
                      />
                      <span className="truncate">{item.name}</span>
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer / Tenant pill */}
      <div className="p-3 border-t border-slate-100 bg-slate-50/40">
        <div className="flex items-center gap-3 px-2 py-1.5 rounded-lg bg-white border border-slate-200/60 shadow-xs">
          <div className="h-7 w-7 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-xs">
            E
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold text-slate-800 truncate">Enterprise Tenant</p>
            <p className="text-[10px] text-slate-400 truncate">Default Production</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
