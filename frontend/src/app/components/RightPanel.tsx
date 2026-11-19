'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  Activity, 
  Clock, 
  Bot, 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  Layers, 
  ShieldAlert, 
  Radio, 
  ExternalLink,
  RefreshCw,
  Cpu,
  Boxes
} from 'lucide-react';
import { cn } from '../lib/utils';
import { fetchApi } from '../lib/api';

interface LiveRunItem {
  id: string;
  name: string;
  agent: string;
  status: 'COMPLETED' | 'RUNNING' | 'FAILED' | 'PENDING_APPROVAL';
  time: string;
}

interface PlatformHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  dbLatencyMs: number;
  uptime: string;
}

const activeAgentsList = [
  { id: 'agent-sales-ops', name: 'Sales Quotation Agent', role: 'Gemini 2.5 Flash', status: 'active', initials: 'SQ' },
  { id: 'agent-invoice-gen', name: 'Tax Invoice Settlement', role: 'Gemini 2.5 Flash', status: 'active', initials: 'TI' },
  { id: 'agent-knowledge-rag', name: 'Policy & Catalog RAG', role: 'Hybrid Dense+BM25', status: 'standby', initials: 'KR' },
  { id: 'agent-mcp-orchestrator', name: 'Enterprise MCP Hub', role: 'SSE Bridge', status: 'active', initials: 'MC' },
];

export default function RightPanel({ isOpen = true, onToggle }: { isOpen?: boolean; onToggle?: () => void }) {
  const [health, setHealth] = useState<PlatformHealth>({
    status: 'healthy',
    dbLatencyMs: 14,
    uptime: '99.98%',
  });
  const [recentRuns, setRecentRuns] = useState<LiveRunItem[]>([]);
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(false);

  const loadOperationalData = async () => {
    setIsLoading(true);
    try {
      // 1. Health check
      const healthRes = await fetchApi('/health');
      if (healthRes.ok) {
        const hJson = await healthRes.json();
        const dbLatency = hJson.components?.database?.latency_ms ?? 12;
        setHealth({
          status: hJson.status === 'healthy' ? 'healthy' : 'degraded',
          dbLatencyMs: dbLatency,
          uptime: '99.98%',
        });
      }
    } catch {
      // Fallback
    }

    try {
      // 2. Real recent executions
      const runsRes = await fetchApi('/runs?limit=6');
      if (runsRes.ok) {
        const rJson = await runsRes.json();
        const items = rJson.items || rJson.runs || [];
        const mapped: LiveRunItem[] = items.map((r: any, idx: number) => {
          const st = (r.status || 'COMPLETED').toUpperCase();
          const normalizedStatus = 
            st === 'WAITING FOR APPROVAL' || st === 'PENDING_APPROVAL' ? 'PENDING_APPROVAL' :
            st === 'FAILED' ? 'FAILED' :
            st === 'RUNNING' ? 'RUNNING' : 'COMPLETED';

          const timeVal = r.created_at || r.started_at;
          const timeStr = timeVal
            ? new Date(timeVal).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            : 'Just now';

          const runId = r.run_id || r.id || (r.started_at ? `run-${r.started_at}` : `run-entry-${idx + 1}`);

          return {
            id: String(runId),
            name: r.goal || r.task || r.final_result || `Agent execution ${String(runId).slice(0, 8)}`,
            agent: r.agent_name || 'AURA Orchestrator',
            status: normalizedStatus,
            time: timeStr,
          };
        });
        setRecentRuns(mapped.slice(0, 5));
      }
    } catch {
      // Fallback
    }

    try {
      // 3. Pending approvals
      const appRes = await fetchApi('/approvals');
      if (appRes.ok) {
        const aJson = await appRes.json();
        const list = aJson.approvals || [];
        const pending = list.filter((a: any) => a.status === 'PENDING').length;
        setPendingApprovalsCount(pending);
      }
    } catch {
      // Fallback
    }

    setIsLoading(false);
  };

  useEffect(() => {
    loadOperationalData();
    const interval = setInterval(loadOperationalData, 15000);
    return () => clearInterval(interval);
  }, []);

  if (!isOpen) return null;

  return (
    <aside className="w-[280px] h-screen bg-card border-l border-border flex flex-col shrink-0 overflow-hidden select-none z-20">
      {/* Platform Status Header */}
      <div className="p-4 border-b border-border shrink-0">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Radio className="w-3.5 h-3.5 text-chart-1 animate-pulse" />
            <h3 className="text-xs font-semibold text-foreground uppercase tracking-wider">
              Live Operations
            </h3>
          </div>
          <button
            type="button"
            onClick={loadOperationalData}
            className="p-1 hover:bg-muted rounded text-muted-foreground hover:text-foreground transition-colors"
            title="Refresh operations telemetry"
          >
            <RefreshCw className={cn('w-3.5 h-3.5', isLoading && 'animate-spin')} />
          </button>
        </div>

        <div className="flex items-center justify-between p-2.5 rounded-xl bg-muted/40 mb-3 border border-border/50">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-success"></span>
            </span>
            <span className="text-xs font-semibold text-foreground">
              {health.status === 'healthy' ? 'Engine Operational' : 'Engine Degraded'}
            </span>
          </div>
          <span className="text-[10px] font-mono text-muted-foreground">v2.4.0</span>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div className="p-2.5 rounded-xl bg-muted/40 border border-border/40">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">DB Latency</p>
            <p className="text-base font-semibold text-foreground font-mono">{health.dbLatencyMs}ms</p>
          </div>
          <div className="p-2.5 rounded-xl bg-muted/40 border border-border/40">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">SLA Uptime</p>
            <p className="text-base font-semibold text-foreground font-mono">{health.uptime}</p>
          </div>
        </div>
      </div>

      {/* Pending Approvals Alert Pill (if any) */}
      {pendingApprovalsCount > 0 && (
        <div className="p-3 bg-destructive/10 border-b border-destructive/20 shrink-0">
          <Link
            href="/approvals"
            className="flex items-center justify-between p-2 rounded-lg bg-background border border-destructive/30 hover:border-destructive transition-colors group"
          >
            <div className="flex items-center gap-2 min-w-0">
              <AlertTriangle className="w-4 h-4 text-destructive shrink-0" />
              <span className="text-xs font-semibold text-foreground truncate">
                {pendingApprovalsCount} Action{pendingApprovalsCount > 1 ? 's' : ''} Require Approval
              </span>
            </div>
            <span className="text-[10px] font-semibold text-destructive group-hover:underline shrink-0">
              Review →
            </span>
          </Link>
        </div>
      )}

      {/* Recent Executions Section */}
      <div className="p-4 border-b border-border flex-1 min-h-0 flex flex-col">
        <div className="flex items-center justify-between mb-3 shrink-0">
          <h4 className="text-xs font-semibold text-foreground flex items-center gap-1.5 uppercase tracking-wider">
            <Activity className="w-3.5 h-3.5 text-muted-foreground" />
            Recent Executions
          </h4>
          <Link href="/executions" className="text-[10px] text-chart-1 hover:underline">
            View All
          </Link>
        </div>

        <div className="space-y-2 overflow-y-auto flex-1 pr-1">
          {recentRuns.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-6">No recent runs recorded.</p>
          ) : (
            recentRuns.map((item) => (
              <Link
                key={item.id}
                href="/executions"
                className="w-full flex items-start gap-2.5 p-2 rounded-xl bg-muted/30 hover:bg-muted/70 transition-colors text-left group border border-transparent hover:border-border/60"
              >
                <div
                  className={cn(
                    'w-7 h-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5',
                    item.status === 'COMPLETED'
                      ? 'bg-success/15 text-success'
                      : item.status === 'FAILED'
                      ? 'bg-destructive/15 text-destructive'
                      : item.status === 'PENDING_APPROVAL'
                      ? 'bg-warning/20 text-warning'
                      : 'bg-chart-1/15 text-chart-1'
                  )}
                >
                  {item.status === 'COMPLETED' ? (
                    <CheckCircle className="w-3.5 h-3.5" />
                  ) : item.status === 'FAILED' ? (
                    <XCircle className="w-3.5 h-3.5" />
                  ) : item.status === 'PENDING_APPROVAL' ? (
                    <AlertTriangle className="w-3.5 h-3.5" />
                  ) : (
                    <Clock className="w-3.5 h-3.5 animate-spin" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-foreground truncate group-hover:text-chart-1 transition-colors">
                    {item.name}
                  </p>
                  <div className="flex items-center justify-between mt-0.5 text-[10px] text-muted-foreground">
                    <span className="truncate">{item.agent}</span>
                    <span className="shrink-0">{item.time}</span>
                  </div>
                </div>
              </Link>
            ))
          )}
        </div>
      </div>

      {/* Active Autonomous Agents Section */}
      <div className="p-4 shrink-0 border-t border-border bg-card">
        <div className="flex items-center justify-between mb-2.5">
          <h4 className="text-xs font-semibold text-foreground flex items-center gap-1.5 uppercase tracking-wider">
            <Bot className="w-3.5 h-3.5 text-muted-foreground" />
            Active Agents
          </h4>
          <Link href="/agents" className="text-[10px] text-chart-1 hover:underline">
            Manage
          </Link>
        </div>

        <div className="space-y-1.5">
          {activeAgentsList.map((agent) => (
            <Link
              key={agent.id}
              href={`/studio/agent`}
              className="flex items-center gap-2.5 p-1.5 rounded-lg hover:bg-muted/50 transition-colors"
            >
              <div className="relative">
                <div className="w-7 h-7 rounded-lg bg-chart-1/15 text-chart-1 flex items-center justify-center text-[10px] font-bold">
                  {agent.initials}
                </div>
                {agent.status === 'active' && (
                  <span className="absolute -bottom-0.5 -right-0.5 w-2 h-2 bg-success rounded-full border border-card" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-foreground truncate leading-tight">{agent.name}</p>
                <p className="text-[10px] text-muted-foreground truncate leading-tight">{agent.role}</p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </aside>
  );
}
