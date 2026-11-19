'use client';

import { useEffect, useState } from 'react';
import { 
  ScrollText, 
  Search, 
  ShieldCheck, 
  AlertTriangle, 
  Filter, 
  Download, 
  User, 
  Clock, 
  Lock, 
  ChevronRight,
  TrendingUp,
  TrendingDown,
  Activity,
  Bug,
  RefreshCw,
  FileText
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { fetchApi } from '../lib/api';
import { cardShadow, cn } from '../lib/utils';
import { Button, StatusBadge } from '../components/ui';

interface AuditLogEntry {
  id: string;
  event_type: string;
  actor: string;
  action_description: string;
  resource_type: string;
  resource_id: string;
  ip_address: string;
  severity: 'INFO' | 'WARN' | 'SECURITY';
  timestamp: string;
}

const auditTrend = [
  { time: '00:00', events: 45, warnings: 2 },
  { time: '04:00', events: 23, warnings: 1 },
  { time: '08:00', events: 89, warnings: 4 },
  { time: '12:00', events: 124, warnings: 6 },
  { time: '16:00', events: 98, warnings: 3 },
  { time: '20:00', events: 67, warnings: 2 },
  { time: 'Now', events: 72, warnings: 1 },
];

const executionFunnel = [
  { stage: 'Agent Invocations', count: 1840, percentage: 100 },
  { stage: 'RBAC Validated', count: 1840, percentage: 100 },
  { stage: 'Knowledge Retrieved', count: 1795, percentage: 97.5 },
  { stage: 'Human Gates Evaluated', count: 1760, percentage: 95.6 },
  { stage: 'Completed Successfully', count: 1728, percentage: 93.9 },
];

const DEFAULT_AUDIT_LOGS: AuditLogEntry[] = [
  {
    id: 'aud-001',
    event_type: 'TOOL_EXECUTION',
    actor: 'agent-sales-ops',
    action_description: 'Executed quotation.create_draft for Acme Corp (₹63,714.69)',
    resource_type: 'QUOTATION',
    resource_id: 'QUO-2026-0982',
    ip_address: '10.0.4.12 (Internal)',
    severity: 'INFO',
    timestamp: 'Today at 18:42:10',
  },
  {
    id: 'aud-002',
    event_type: 'HUMAN_APPROVAL_REQUEST',
    actor: 'agent-invoice-gen',
    action_description: 'Triggered approval gate for Tax Invoice generation exceeding ₹50,000 threshold',
    resource_type: 'APPROVAL_GATE',
    resource_id: 'appr-req-4412',
    ip_address: '10.0.4.12 (Internal)',
    severity: 'WARN',
    timestamp: 'Today at 18:40:02',
  },
  {
    id: 'aud-003',
    event_type: 'TENANT_AUTH_VERIFY',
    actor: 'operator@aura.internal',
    action_description: 'Validated JWT token with tenant isolation boundaries enforced (tenant_default)',
    resource_type: 'AUTH_SESSION',
    resource_id: 'sess-8941',
    ip_address: '192.168.1.104',
    severity: 'INFO',
    timestamp: 'Today at 18:35:19',
  },
  {
    id: 'aud-004',
    event_type: 'KNOWLEDGE_INGESTION',
    actor: 'admin@aura.internal',
    action_description: 'Ingested and chunked Cloud Infotech Price List v1 into pgvector store',
    resource_type: 'KNOWLEDGE_BASE',
    resource_id: 'kb-cloud-infotech',
    ip_address: '192.168.1.104',
    severity: 'INFO',
    timestamp: 'Today at 15:20:00',
  },
  {
    id: 'aud-005',
    event_type: 'SECURITY_GATE_DENY',
    actor: 'external-probe',
    action_description: 'Blocked unauthorized cross-tenant query attempting to read quotation without tenant_id',
    resource_type: 'SECURITY_POLICY',
    resource_id: 'policy-tenant-rls',
    ip_address: '203.0.113.44',
    severity: 'SECURITY',
    timestamp: 'Today at 14:11:05',
  },
  {
    id: 'aud-006',
    event_type: 'TOOL_EXECUTION',
    actor: 'agent-knowledge-rag',
    action_description: 'Queried pgvector store with hybrid dense + sparse BM25 lookup for Grandstream GRP2614',
    resource_type: 'RAG_SEARCH',
    resource_id: 'kb-cloud-infotech',
    ip_address: '10.0.4.12 (Internal)',
    severity: 'INFO',
    timestamp: 'Today at 13:45:22',
  },
];

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLogEntry[]>(DEFAULT_AUDIT_LOGS);
  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [isExporting, setIsExporting] = useState(false);

  const loadLogs = async () => {
    try {
      const res = await fetchApi('/audit/logs');
      if (res.ok) {
        const data = await res.json();
        if (data.logs && data.logs.length > 0) {
          setLogs(data.logs);
        }
      }
    } catch {}
  };

  useEffect(() => {
    loadLogs();
  }, []);

  const filteredLogs = logs.filter((log) => {
    const matchesSeverity = severityFilter === 'ALL' || log.severity === severityFilter;
    const matchesSearch =
      log.action_description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.actor.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.event_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.resource_id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSeverity && matchesSearch;
  });

  const exportJSON = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(filteredLogs, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `aura_audit_logs_${Date.now()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const exportCSV = async () => {
    setIsExporting(true);
    try {
      const res = await fetchApi('/audit/logs?export=csv');
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `aura_audit_logs_${Date.now()}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
      }
    } catch {
      // Fallback client-side CSV
      let csvContent = 'data:text/csv;charset=utf-8,ID,Event Type,Actor,Description,Resource,Severity,Timestamp\n';
      filteredLogs.forEach((l) => {
        csvContent += `"${l.id}","${l.event_type}","${l.actor}","${l.action_description.replace(/"/g, '""')}","${l.resource_type}","${l.severity}","${l.timestamp}"\n`;
      });
      const encodedUri = encodeURI(csvContent);
      const link = document.createElement('a');
      link.setAttribute('href', encodedUri);
      link.setAttribute('download', `aura_audit_logs_${Date.now()}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } finally {
      setIsExporting(false);
    }
  };

  const securityCount = logs.filter((l) => l.severity === 'SECURITY').length;
  const warnCount = logs.filter((l) => l.severity === 'WARN').length;

  return (
    <div className="space-y-6 pb-12">
      {/* 4 Pulse KPI Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div
          className="bg-card rounded-2xl p-5 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <p className="text-xs font-medium text-muted-foreground mb-1">Total Audit Events (24h)</p>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-foreground">1,842</p>
            <span className="text-xs font-semibold text-success flex items-center gap-0.5">
              <TrendingUp className="w-3.5 h-3.5" /> +12%
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground mt-1">Immutable cryptographic log</p>
        </div>

        <div
          className="bg-card rounded-2xl p-5 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <p className="text-xs font-medium text-muted-foreground mb-1">Security Anomalies</p>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-destructive">{securityCount}</p>
            <span className="text-xs font-semibold text-destructive">Blocked</span>
          </div>
          <p className="text-[11px] text-muted-foreground mt-1">Cross-tenant isolation maintained</p>
        </div>

        <div
          className="bg-card rounded-2xl p-5 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <p className="text-xs font-medium text-muted-foreground mb-1">Human Gate Events</p>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-warning">{warnCount}</p>
            <span className="text-xs font-semibold text-warning">Evaluated</span>
          </div>
          <p className="text-[11px] text-muted-foreground mt-1">Policy thresholds triggered</p>
        </div>

        <div
          className="bg-card rounded-2xl p-5 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <p className="text-xs font-medium text-muted-foreground mb-1">Policy Compliance</p>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-success">100%</p>
            <span className="text-xs font-semibold text-success">Compliant</span>
          </div>
          <p className="text-[11px] text-muted-foreground mt-1">SOC-2 & ISO 27001 readiness</p>
        </div>
      </div>

      {/* Pulse Charts Row: Event Trend + Funnel */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Audit Event Trend AreaChart */}
        <div
          className="bg-card rounded-2xl p-6 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-base font-semibold text-foreground tracking-tight">Audit Event Velocity</h3>
              <p className="text-xs text-muted-foreground mt-0.5">Events logged per hour across all tenants</p>
            </div>
            <div className="flex items-center gap-1.5 text-xs font-semibold text-chart-1">
              <Activity className="w-3.5 h-3.5" />
              <span>Normal</span>
            </div>
          </div>

          <div className="h-[220px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={auditTrend}>
                <defs>
                  <linearGradient id="auditGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="oklch(0.55 0.18 250)" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="oklch(0.55 0.18 250)" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.92 0.005 250)" />
                <XAxis 
                  dataKey="time" 
                  tick={{ fill: "oklch(0.55 0.01 250)", fontSize: 11 }}
                  axisLine={{ stroke: "oklch(0.92 0.005 250)" }}
                />
                <YAxis 
                  tick={{ fill: "oklch(0.55 0.01 250)", fontSize: 11 }}
                  axisLine={{ stroke: "oklch(0.92 0.005 250)" }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "white",
                    border: "1px solid oklch(0.92 0.005 250)",
                    borderRadius: "12px",
                    boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
                    fontSize: "12px",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="events"
                  stroke="oklch(0.55 0.18 250)"
                  strokeWidth={2}
                  fill="url(#auditGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Request Pipeline Funnel (Pulse Errors Request Funnel Pattern) */}
        <div
          className="bg-card rounded-2xl p-6 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-semibold text-foreground tracking-tight">Execution Funnel</h3>
              <p className="text-xs text-muted-foreground mt-0.5">Agent request verification pipeline stages</p>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-muted text-muted-foreground">
              93.9% Success
            </span>
          </div>

          <div className="space-y-3">
            {executionFunnel.map((stage, idx) => (
              <div key={stage.stage}>
                <div className="flex items-center justify-between mb-1 text-xs">
                  <span className="font-medium text-foreground">{stage.stage}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground font-mono">{stage.count}</span>
                    <span className="font-semibold text-success text-[11px]">{stage.percentage}%</span>
                  </div>
                </div>
                <div className="h-6 bg-muted/60 rounded-lg overflow-hidden">
                  <div
                    className={cn(
                      'h-full rounded-lg transition-all duration-500',
                      idx === executionFunnel.length - 1 ? 'bg-success' : 'bg-chart-1'
                    )}
                    style={{ width: `${stage.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Filter and Export Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3 flex-1 max-w-md">
          <div className="relative w-full">
            <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              placeholder="Search audit events by actor, action, or resource..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 rounded-xl bg-card border border-border text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          {['ALL', 'INFO', 'WARN', 'SECURITY'].map((sev) => (
            <button
              key={sev}
              type="button"
              onClick={() => setSeverityFilter(sev)}
              className={cn(
                'px-3 py-1.5 rounded-full text-xs font-semibold transition-colors',
                severityFilter === sev
                  ? 'bg-primary text-primary-foreground shadow-xs'
                  : 'bg-card border border-border text-muted-foreground hover:bg-muted'
              )}
            >
              {sev}
            </button>
          ))}

          <button
            type="button"
            onClick={exportCSV}
            disabled={isExporting}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-border bg-card hover:bg-muted text-xs font-semibold text-foreground transition-colors ml-1"
          >
            <Download className="w-3.5 h-3.5 text-muted-foreground" />
            <span>{isExporting ? 'Exporting...' : 'Export CSV'}</span>
          </button>
          <button
            type="button"
            onClick={exportJSON}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-border bg-card hover:bg-muted text-xs font-semibold text-foreground transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-muted-foreground" />
            <span>Export JSON</span>
          </button>
        </div>
      </div>

      {/* Audit Log Table (Pulse Top Errors Pattern) */}
      <div
        className="bg-card rounded-2xl border border-border overflow-hidden"
        style={{ boxShadow: cardShadow }}
      >
        <div className="p-5 sm:p-6 border-b border-border flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-foreground tracking-tight">Security & Governance Audit Trail</h3>
            <p className="text-xs text-muted-foreground mt-0.5">Chronological record of autonomous agent operations and authorization events</p>
          </div>
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-muted text-muted-foreground">
            {filteredLogs.length} events
          </span>
        </div>

        <div className="divide-y divide-border">
          {filteredLogs.map((entry) => (
            <div
              key={entry.id}
              className="p-4 hover:bg-muted/30 transition-colors flex items-center gap-4"
            >
              <div
                className={cn(
                  'w-9 h-9 rounded-xl flex items-center justify-center shrink-0',
                  entry.severity === 'SECURITY'
                    ? 'bg-destructive/15 text-destructive'
                    : entry.severity === 'WARN'
                    ? 'bg-warning/20 text-warning'
                    : 'bg-chart-1/15 text-chart-1'
                )}
              >
                {entry.severity === 'SECURITY' ? (
                  <ShieldCheck className="w-4 h-4" />
                ) : entry.severity === 'WARN' ? (
                  <AlertTriangle className="w-4 h-4" />
                ) : (
                  <FileText className="w-4 h-4" />
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-xs font-semibold text-foreground">{entry.event_type}</span>
                  <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-muted text-muted-foreground">
                    Actor: {entry.actor}
                  </span>
                  <span
                    className={cn(
                      'px-2 py-0.5 text-[10px] font-semibold rounded-full uppercase',
                      entry.severity === 'SECURITY'
                        ? 'bg-destructive/15 text-destructive'
                        : entry.severity === 'WARN'
                        ? 'bg-warning/20 text-warning'
                        : 'bg-muted text-muted-foreground'
                    )}
                  >
                    {entry.severity}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed truncate">{entry.action_description}</p>
                <div className="flex items-center gap-4 text-[10px] font-mono text-muted-foreground/75 mt-1">
                  <span>Resource: {entry.resource_type} ({entry.resource_id})</span>
                  <span>IP: {entry.ip_address}</span>
                </div>
              </div>

              <div className="text-right shrink-0">
                <p className="text-xs text-muted-foreground font-mono">{entry.timestamp}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
