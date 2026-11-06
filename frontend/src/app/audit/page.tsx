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
  ChevronRight
} from 'lucide-react';
import { fetchApi } from '../lib/api';

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

const SAMPLE_AUDIT_LOGS: AuditLogEntry[] = [
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
    action_description: 'Triggered approval gate for Tax Invoice generation exceeding ₹50,000',
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
    action_description: 'Validated JWT token with tenant isolation boundaries enforced',
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
    timestamp: 'Today at 12:14:08',
  }
];

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLogEntry[]>(SAMPLE_AUDIT_LOGS);
  const [filterSeverity, setFilterSeverity] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');

  const filteredLogs = logs.filter((l) => {
    const matchesSev = filterSeverity === 'ALL' || l.severity === filterSeverity;
    const matchesSearch = l.action_description.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          l.actor.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          l.resource_type.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSev && matchesSearch;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Audit & Security Activity Logs</h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              Immutable Trace
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Enterprise compliance ledger tracking all tool executions, user authentications, and policy evaluations.
          </p>
        </div>

        <button
          onClick={() => {
            const blob = new Blob([JSON.stringify(logs, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `aura-audit-export-${Date.now()}.json`;
            a.click();
          }}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-700 text-xs font-semibold hover:bg-slate-50 transition shadow-xs"
        >
          <Download className="h-4 w-4" /> Export Compliance Log (JSON)
        </button>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search events by actor, action description, or resource..."
            className="w-full rounded-lg border border-slate-200 bg-slate-50/60 pl-9 pr-3 py-1.5 text-xs text-slate-900 focus:border-blue-500 focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-400" />
          <span className="text-xs text-slate-500 font-medium">Severity:</span>
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700 focus:border-blue-500 focus:outline-none"
          >
            <option value="ALL">All Severities</option>
            <option value="INFO">Informational</option>
            <option value="WARN">Warnings / Approvals</option>
            <option value="SECURITY">Security Policy Actions</option>
          </select>
        </div>
      </div>

      {/* Logs Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold">
                <th className="py-3 px-4">Event & Action</th>
                <th className="py-3 px-4">Actor</th>
                <th className="py-3 px-4">Resource Target</th>
                <th className="py-3 px-4">Source IP</th>
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredLogs.map((entry) => (
                <tr key={entry.id} className="hover:bg-slate-50/60 transition">
                  <td className="py-3 px-4">
                    <span className="font-bold text-slate-900 block">{entry.event_type}</span>
                    <span className="text-slate-600 text-[11px] block mt-0.5">{entry.action_description}</span>
                  </td>
                  <td className="py-3 px-4 font-mono text-[11px] text-slate-700">
                    {entry.actor}
                  </td>
                  <td className="py-3 px-4">
                    <span className="font-semibold text-slate-800">{entry.resource_type}</span>
                    <span className="block font-mono text-[10px] text-slate-400">{entry.resource_id}</span>
                  </td>
                  <td className="py-3 px-4 font-mono text-[11px] text-slate-500">
                    {entry.ip_address}
                  </td>
                  <td className="py-3 px-4">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
                      entry.severity === 'INFO' ? 'bg-slate-100 text-slate-700' :
                      entry.severity === 'WARN' ? 'bg-amber-50 text-amber-700 border border-amber-200' :
                      'bg-red-50 text-red-700 border border-red-200'
                    }`}>
                      {entry.severity}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-500 whitespace-nowrap">
                    {entry.timestamp}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
