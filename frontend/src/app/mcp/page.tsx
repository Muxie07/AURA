'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  Boxes, 
  Plus, 
  CheckCircle2, 
  AlertTriangle, 
  ExternalLink, 
  ShieldCheck, 
  RefreshCw, 
  Server, 
  Lock,
  Search,
  Radio,
  Clock,
  Activity,
  Terminal,
  Zap,
  Trash2
} from 'lucide-react';
import { cardShadow, cn } from '../lib/utils';
import { Button, StatusBadge } from '../components/ui';
import { fetchApi } from '../lib/api';

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
  const [showAddModal, setShowAddModal] = useState(false);
  const [newServerName, setNewServerName] = useState('');
  const [newServerEndpoint, setNewServerEndpoint] = useState('');
  const [diagnosticsOutput, setDiagnosticsOutput] = useState<string | null>(null);

  const loadServers = async () => {
    try {
      const res = await fetchApi('/mcp/servers');
      if (res.ok) {
        const data = await res.json();
        if (data.servers && data.servers.length > 0) {
          setServers(data.servers);
        }
      }
    } catch {}
  };

  useEffect(() => {
    loadServers();
  }, []);

  const handleRefreshAll = async () => {
    setIsRefreshing(true);
    await loadServers();
    setIsRefreshing(false);
  };

  const runDiagnostics = async (server: MCPServer) => {
    setDiagnosticsOutput(`Connecting to ${server.name} diagnostic probe...`);
    try {
      const res = await fetchApi(`/mcp/servers/${server.id}/ping`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setDiagnosticsOutput(data.diagnostics || `Ping latency: ${data.latency_ms}ms (HEALTHY)`);
        setServers(prev => prev.map(s => s.id === server.id ? { ...s, last_ping_ms: data.latency_ms } : s));
      } else {
        setDiagnosticsOutput(`Failed to ping ${server.name}: endpoint unreachable.`);
      }
    } catch (e: any) {
      setDiagnosticsOutput(`Probe error: ${e.message}`);
    }
  };

  const handleAddServer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newServerName.trim() || !newServerEndpoint.trim()) return;

    try {
      const res = await fetchApi('/mcp/servers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newServerName,
          endpoint: newServerEndpoint,
          transport: 'sse',
        }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.server) {
          setServers([data.server, ...servers]);
        }
      }
    } catch {
      // Local fallback
      const newServer: MCPServer = {
        id: `mcp-${Date.now().toString().slice(-4)}`,
        name: newServerName,
        endpoint: newServerEndpoint,
        transport: 'sse',
        status: 'CONNECTED',
        tools_count: 2,
        scopes: ['custom:read', 'custom:query'],
        last_ping_ms: 22,
        risk_level: 'STANDARD',
        description: 'Custom connected MCP server endpoint.',
      };
      setServers([...servers, newServer]);
    }
    setNewServerName('');
    setNewServerEndpoint('');
    setShowAddModal(false);
  };

  const handleDisconnect = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to disconnect MCP server "${name}"?`)) return;
    try {
      await fetchApi(`/mcp/servers/${id}`, { method: 'DELETE' });
    } catch {}
    setServers(prev => prev.filter(s => s.id !== id));
  };

  const connectedCount = servers.filter((s) => s.status === 'CONNECTED').length;
  const totalMcpTools = servers.reduce((acc, s) => acc + s.tools_count, 0);

  return (
    <div className="space-y-6 pb-12">
      {/* Pulse KPI Summary Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div
          className="bg-card rounded-2xl p-5 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <p className="text-xs font-medium text-muted-foreground mb-1">MCP Servers</p>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-foreground">{servers.length}</p>
            <span className="text-xs font-semibold text-chart-1">Configured</span>
          </div>
        </div>

        <div
          className="bg-card rounded-2xl p-5 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <p className="text-xs font-medium text-muted-foreground mb-1">Connection Health</p>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-success">{connectedCount} Connected</p>
            <span className="text-xs font-semibold text-success flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" /> Live SSE
            </span>
          </div>
        </div>

        <div
          className="bg-card rounded-2xl p-5 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <p className="text-xs font-medium text-muted-foreground mb-1">Exported MCP Tools</p>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-foreground">{totalMcpTools}</p>
            <span className="text-xs font-semibold text-chart-2">JSON-RPC 2.0</span>
          </div>
        </div>

        <div
          className="bg-card rounded-2xl p-5 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <p className="text-xs font-medium text-muted-foreground mb-1">Average Ping Latency</p>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-foreground">
              {Math.round(servers.reduce((acc, s) => acc + s.last_ping_ms, 0) / servers.length)}ms
            </p>
            <span className="text-xs font-semibold text-success">Low Overhead</span>
          </div>
        </div>
      </div>

      {/* Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-foreground">Connected Protocol Endpoints</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Standardized Model Context Protocol servers communicating over Server-Sent Events (SSE).
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/tools"
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-chart-2/40 bg-chart-2/10 text-chart-2 text-xs font-semibold hover:bg-chart-2/20 transition-colors"
          >
            <span>UTCP Endpoints →</span>
          </Link>

          <button
            type="button"
            onClick={handleRefreshAll}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-border bg-card text-foreground text-xs font-semibold hover:bg-muted transition-colors"
          >
            <RefreshCw className={cn('w-3.5 h-3.5 text-muted-foreground', isRefreshing && 'animate-spin')} />
            <span>Ping All</span>
          </button>

          <button
            type="button"
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-semibold shadow-xs transition-colors shrink-0"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Connect Server</span>
          </button>
        </div>
      </div>

      {/* Servers Grid (Pulse Services Design Pattern) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {servers.map((server) => (
          <div
            key={server.id}
            className="bg-card rounded-2xl border border-border p-5 hover:border-primary/30 transition-all flex flex-col justify-between"
            style={{ boxShadow: cardShadow }}
          >
            <div>
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 rounded-xl bg-chart-1/15 text-chart-1 flex items-center justify-center font-bold text-xs shrink-0">
                  <Boxes className="w-5 h-5" />
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="px-2 py-0.5 text-[10px] font-semibold bg-success/15 text-success rounded-full flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" />
                    {server.status}
                  </span>
                </div>
              </div>

              <h3 className="text-sm font-bold text-foreground mb-1 leading-snug">{server.name}</h3>
              <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed mb-4">
                {server.description}
              </p>

              <div className="space-y-2 mb-4">
                <div className="p-2.5 rounded-xl bg-muted/40 border border-border/40 text-xs font-mono">
                  <div className="flex justify-between items-center text-muted-foreground mb-1 text-[10px] uppercase">
                    <span>Endpoint</span>
                    <span>{server.transport.toUpperCase()}</span>
                  </div>
                  <p className="text-foreground truncate text-[11px]">{server.endpoint}</p>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="p-2 rounded-xl bg-muted/40 border border-border/40">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Tools Available</p>
                    <p className="text-xs font-semibold text-foreground font-mono">{server.tools_count} actions</p>
                  </div>
                  <div className="p-2 rounded-xl bg-muted/40 border border-border/40">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Ping Latency</p>
                    <p className="text-xs font-semibold text-success font-mono">{server.last_ping_ms}ms</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-border flex items-center justify-between text-xs">
              <span className="text-[10px] font-mono text-muted-foreground">Scopes: {server.scopes.length} active</span>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => runDiagnostics(server)}
                  className="text-primary hover:underline font-semibold text-xs flex items-center gap-1"
                >
                  <span>Diagnostics</span>
                  <Terminal className="w-3.5 h-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => handleDisconnect(server.id, server.name)}
                  className="text-muted-foreground hover:text-destructive transition p-1"
                  title="Disconnect MCP server"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Diagnostics Console Window */}
      {diagnosticsOutput && (
        <div 
          className="bg-card rounded-2xl border border-border p-5"
          style={{ boxShadow: cardShadow }}
        >
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-xs font-bold text-foreground flex items-center gap-2">
              <Terminal className="w-4 h-4 text-chart-1" />
              Live MCP Diagnostics Terminal
            </h4>
            <button
              type="button"
              onClick={() => setDiagnosticsOutput(null)}
              className="text-[11px] text-muted-foreground hover:text-foreground"
            >
              Close Console
            </button>
          </div>
          <pre className="p-4 rounded-xl bg-muted/30 border border-border font-mono text-xs text-foreground whitespace-pre-wrap leading-relaxed">
            {diagnosticsOutput}
          </pre>
        </div>
      )}

      {/* Add Server Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div 
            className="bg-card rounded-2xl border border-border max-w-md w-full p-6 animate-scale-in"
            style={{ boxShadow: cardShadow }}
          >
            <h3 className="text-base font-bold text-foreground mb-1">Connect MCP Server</h3>
            <p className="text-xs text-muted-foreground mb-4">
              Register a Model Context Protocol endpoint for tool auto-discovery.
            </p>

            <form onSubmit={handleAddServer} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">Server Identifier</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Enterprise Logistics & Shipping Bridge"
                  value={newServerName}
                  onChange={(e) => setNewServerName(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-muted/40 border border-border text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">SSE Endpoint URL</label>
                <input
                  type="url"
                  required
                  placeholder="https://mcp.company.internal/sse"
                  value={newServerEndpoint}
                  onChange={(e) => setNewServerEndpoint(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-muted/40 border border-border text-xs text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>

              <div className="flex justify-end gap-2.5 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3.5 py-1.5 rounded-xl border border-border text-xs font-semibold text-foreground hover:bg-muted transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-xl bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition shadow-xs"
                >
                  Connect & Inspect
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
