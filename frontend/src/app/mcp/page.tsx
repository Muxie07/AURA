'use client';
import { useState } from 'react';
import { 
  Boxes, 
  Plus, 
  CheckCircle2, 
  AlertCircle, 
  ExternalLink, 
  ShieldCheck, 
  RefreshCw, 
  Server, 
  Lock,
  Search,
  Radio
} from 'lucide-react';

interface MCPServer {
  id: string;
  name: string;
  endpoint: string;
  transport: 'sse' | 'stdio' | 'websocket';
  status: 'CONNECTED' | 'DISCONNECTED' | 'ERROR';
  tools_count: number;
  scopes: string[];
  last_ping_ms: number;
  risk_level: 'STANDARD' | 'ELEVATED';
  description: string;
}

const MCP_SERVERS_DATA: MCPServer[] = [
  {
    id: 'mcp-aura-local',
    name: 'AURA Builtin ERP & Quotation Hub',
    endpoint: 'http://aura-mcp:8000/sse',
    transport: 'sse',
    status: 'CONNECTED',
    tools_count: 5,
    scopes: ['quotation:write', 'invoice:generate', 'catalog:read'],
    last_ping_ms: 14,
    risk_level: 'ELEVATED',
    description: 'Internal secured container executing local database pricing models and invoice issuance tools.',
  },
  {
    id: 'mcp-crm-bridge',
    name: 'Enterprise CRM & Account Registry',
    endpoint: 'http://crm-internal.local/mcp',
    transport: 'sse',
    status: 'CONNECTED',
    tools_count: 3,
    scopes: ['customer:search', 'customer:credit_limit'],
    last_ping_ms: 32,
    risk_level: 'STANDARD',
    description: 'Read-only connection to corporate customer records and payment credit histories.',
  },
  {
    id: 'mcp-inventory-sync',
    name: 'Warehouse & Cloud Infotech Stock Bridge',
    endpoint: 'https://inventory.cloudinfotech.internal/mcp/v1',
    transport: 'sse',
    status: 'CONNECTED',
    tools_count: 2,
    scopes: ['inventory:check_stock'],
    last_ping_ms: 45,
    risk_level: 'STANDARD',
    description: 'Real-time stock checks for Grandstream, Fanvil, and Yeastar hardware models.',
  }
];

export default function MCPIntegrationsPage() {
  const [servers, setServers] = useState<MCPServer[]>(MCP_SERVERS_DATA);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefreshAll = () => {
    setIsRefreshing(true);
    setTimeout(() => setIsRefreshing(false), 1200);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Model Context Protocol (MCP) Hub</h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-50 text-purple-700 border border-purple-200">
              Anthropic MCP Standard
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Governed server connections providing tools, resources, and live prompts to AURA agents.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleRefreshAll}
            disabled={isRefreshing}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-700 text-xs font-semibold hover:bg-slate-50 transition shadow-xs"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh Heartbeats
          </button>
          <button className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 transition shadow-xs">
            <Plus className="h-4 w-4" /> Connect MCP Server
          </button>
        </div>
      </div>

      {/* Servers List */}
      <div className="grid grid-cols-1 gap-4">
        {servers.map((s) => (
          <div
            key={s.id}
            className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs hover:border-slate-300 transition"
          >
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-100">
              <div className="flex items-start gap-3">
                <div className="h-10 w-10 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center shrink-0">
                  <Server className="h-5 w-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-slate-900">{s.name}</h3>
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                      {s.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">{s.description}</p>
                </div>
              </div>

              <div className="flex items-center gap-4 text-xs">
                <div className="text-right">
                  <span className="text-slate-400 block text-[10px]">Ping</span>
                  <span className="font-mono font-semibold text-slate-700">{s.last_ping_ms}ms</span>
                </div>
                <div className="text-right">
                  <span className="text-slate-400 block text-[10px]">Transport</span>
                  <span className="font-mono uppercase font-semibold text-slate-700">{s.transport}</span>
                </div>
                <div className="text-right">
                  <span className="text-slate-400 block text-[10px]">Exposed Tools</span>
                  <span className="font-semibold text-slate-900">{s.tools_count}</span>
                </div>
              </div>
            </div>

            {/* Sub-bar: Endpoint & Scopes */}
            <div className="pt-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
              <div className="flex items-center gap-2 text-slate-500 font-mono text-[11px]">
                <Radio className="h-3.5 w-3.5 text-blue-600" />
                <span>{s.endpoint}</span>
              </div>

              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-[11px] text-slate-400 mr-1">Scopes:</span>
                {s.scopes.map((scope) => (
                  <span
                    key={scope}
                    className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-[10px] font-mono"
                  >
                    {scope}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
