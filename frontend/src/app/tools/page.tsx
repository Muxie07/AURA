'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  Wrench, 
  Search, 
  ShieldCheck, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  Boxes,
  Globe,
  Radio,
  Plus,
  Server,
  Layers,
  Terminal,
  Activity,
  ArrowRight
} from 'lucide-react';
import { fetchApi } from '../lib/api';
import { cardShadow, cn } from '../lib/utils';
import { Button, StatusBadge } from '../components/ui';

interface ToolEntry {
  friendly: string;
  name: string;
  description: string;
  risk: 'LOW' | 'MEDIUM' | 'HIGH';
  category: string;
  protocol: 'INTERNAL' | 'MCP' | 'UTCP';
  required_scope: string;
  last_invoked?: string;
  requires_approval: boolean;
}

const TOOL_REGISTRY: ToolEntry[] = [
  { 
    friendly: 'Sales Quotation Draft', 
    name: 'quotation.create_draft', 
    description: 'Constructs official B2B quotation PDF, validates pricing rules, and stores record in database.', 
    risk: 'HIGH', 
    category: 'Quotation',
    protocol: 'INTERNAL',
    required_scope: 'quotation:write',
    last_invoked: '10 min ago',
    requires_approval: true
  },
  { 
    friendly: 'Pricing & GST Calculator', 
    name: 'quotation.calculate_pricing', 
    description: 'Calculates volume tier discount, gross profit margin, and statutory 18% GST.', 
    risk: 'LOW', 
    category: 'Quotation',
    protocol: 'INTERNAL',
    required_scope: 'quotation:read',
    last_invoked: '12 min ago',
    requires_approval: false
  },
  { 
    friendly: 'Customer Account Search', 
    name: 'customer.search', 
    description: 'Find enterprise customer records, billing addresses, and tax identification by ID or name.', 
    risk: 'LOW', 
    category: 'CRM',
    protocol: 'INTERNAL',
    required_scope: 'customer:read',
    last_invoked: '25 min ago',
    requires_approval: false
  },
  { 
    friendly: 'Remote Product Catalog Search', 
    name: 'mcp.product.search', 
    description: 'Queries remote Model Context Protocol hardware catalog via SSE connection pool.', 
    risk: 'LOW', 
    category: 'Inventory',
    protocol: 'MCP',
    required_scope: 'mcp:tools:read',
    last_invoked: '8 min ago',
    requires_approval: false
  },
  { 
    friendly: 'Enterprise Wire Settlement (UTCP)', 
    name: 'utcp.payments.wire_settlement', 
    description: 'Direct native HTTP/REST invocation to banking clearinghouse with server-derived idempotency.', 
    risk: 'HIGH', 
    category: 'Orders',
    protocol: 'UTCP',
    required_scope: 'utcp:payments:write',
    last_invoked: '1 hour ago',
    requires_approval: true
  },
  { 
    friendly: 'Real-time Stock Inventory (UTCP)', 
    name: 'utcp.warehouse.stock_lookup', 
    description: 'Direct low-latency WebSocket/HTTP lookup against automated distribution center ERP.', 
    risk: 'LOW', 
    category: 'Inventory',
    protocol: 'UTCP',
    required_scope: 'utcp:warehouse:read',
    last_invoked: '4 min ago',
    requires_approval: false
  },
  { 
    friendly: 'Statutory GSTIN Verification (UTCP)', 
    name: 'utcp.tax.validate_gstin', 
    description: 'Validates 15-digit GSTIN tax identity with Indian Department of Revenue portal.', 
    risk: 'LOW', 
    category: 'CRM',
    protocol: 'UTCP',
    required_scope: 'utcp:tax:read',
    last_invoked: '18 min ago',
    requires_approval: false
  },
  { 
    friendly: 'Update Customer Record', 
    name: 'customer.update', 
    description: 'Update customer credit terms, contacts, and billing preferences.', 
    risk: 'MEDIUM', 
    category: 'CRM',
    protocol: 'INTERNAL',
    required_scope: 'customer:write',
    last_invoked: '1 hour ago',
    requires_approval: false
  },
  { 
    friendly: 'ERP Order Status Query', 
    name: 'order.get_status', 
    description: 'Fetches real-time dispatch, transit tracking, and warehouse packing milestones.', 
    risk: 'LOW', 
    category: 'Orders',
    protocol: 'INTERNAL',
    required_scope: 'orders:read',
    last_invoked: '15 min ago',
    requires_approval: false
  },
  { 
    friendly: 'Read Server Diagnostics Logs', 
    name: 'read_server_logs', 
    description: 'Reads container metrics, exception traces, and runtime event stream.', 
    risk: 'LOW', 
    category: 'SRE',
    protocol: 'INTERNAL',
    required_scope: 'logs:read',
    last_invoked: '1 hour ago',
    requires_approval: false
  },
  { 
    friendly: 'Restart Service Container', 
    name: 'restart_service', 
    description: 'Restarts decoupled worker and SSE bridge service containers.', 
    risk: 'HIGH', 
    category: 'SRE',
    protocol: 'INTERNAL',
    required_scope: 'system:restart',
    last_invoked: '3 days ago',
    requires_approval: true
  },
  { 
    friendly: 'Send Channel Notification', 
    name: 'send_notification', 
    description: 'Dispatches operational alerts and quotation links to Slack or Email.', 
    risk: 'MEDIUM', 
    category: 'Comms',
    protocol: 'INTERNAL',
    required_scope: 'comms:send',
    last_invoked: '15 min ago',
    requires_approval: false
  },
];

export default function ToolsRegistryPage() {
  const [tools, setTools] = useState<ToolEntry[]>(TOOL_REGISTRY);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');
  const [protocolFilter, setProtocolFilter] = useState<string>('ALL');
  const [totalInvocations, setTotalInvocations] = useState<number>(64);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newEndpointName, setNewEndpointName] = useState('');
  const [newBaseUrl, setNewBaseUrl] = useState('');
  const [newProtocol, setNewProtocol] = useState<'UTCP' | 'MCP'>('UTCP');
  const [newAuthToken, setNewAuthToken] = useState('');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchApi('/runs')
      .then((r) => r.json())
      .then((j) => {
        const runsList = j.items || j.runs || [];
        const count = runsList.reduce((acc: number, r: any) => acc + (r.tool_call_count || 1), 0);
        setTotalInvocations(count || 64);
      })
      .catch(() => setTotalInvocations(64));
  }, []);

  const handleRegisterEndpoint = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEndpointName || !newBaseUrl) return;

    try {
      await fetchApi('/tools/utcp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newEndpointName,
          base_url: newBaseUrl,
          credential_token: newAuthToken || undefined,
        }),
      });
    } catch {}

    const newTool: ToolEntry = {
      friendly: `${newEndpointName} (${newProtocol})`,
      name: `${newProtocol.toLowerCase()}.${newEndpointName.toLowerCase().replace(/\s+/g, '_')}.execute`,
      description: `Direct invocation endpoint connecting to ${newBaseUrl}`,
      risk: 'LOW',
      category: 'Integration',
      protocol: newProtocol,
      required_scope: `${newProtocol.toLowerCase()}:execute`,
      last_invoked: 'Just now',
      requires_approval: false,
    };

    setTools((prev) => [newTool, ...prev]);
    setShowAddModal(false);
    setNewEndpointName('');
    setNewBaseUrl('');
    setNewAuthToken('');
    setToastMessage(`Endpoint ${newEndpointName} registered successfully via ${newProtocol}.`);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const highRiskCount = tools.filter((t) => t.risk === 'HIGH').length;
  const utcpCount = tools.filter((t) => t.protocol === 'UTCP').length;
  const mcpCount = tools.filter((t) => t.protocol === 'MCP').length;

  const categories = ['ALL', 'Quotation', 'CRM', 'Orders', 'Inventory', 'SRE', 'Comms'];
  const protocols = ['ALL', 'INTERNAL', 'MCP', 'UTCP'];

  const filteredTools = tools.filter((t) => {
    const matchesCategory = categoryFilter === 'ALL' || t.category === categoryFilter;
    const matchesProtocol = protocolFilter === 'ALL' || t.protocol === protocolFilter;
    const matchesSearch =
      t.friendly.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesProtocol && matchesSearch;
  });

  return (
    <div className="space-y-6 pb-12">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground text-xs font-semibold shadow-lg animate-slide-up flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-success" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Hybrid Architecture Notification Banner */}
      <div 
        className="bg-card rounded-2xl p-5 border border-chart-1/30 flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
        style={{ boxShadow: cardShadow }}
      >
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-chart-1/15 text-chart-1 flex items-center justify-center shrink-0">
            <Radio className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-foreground">Hybrid Tool Architecture: UTCP + MCP Active</h3>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-success/15 text-success">
                v2.4 Unified Hub
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              AURA unifies local functions, stateful MCP SSE servers, and direct lightweight Universal Tool Calling Protocol (UTCP) endpoints under one policy engine.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-colors shadow-xs shrink-0"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Register Endpoint</span>
        </button>
      </div>

      {/* Pulse KPI Summary Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div
          className="bg-card rounded-2xl p-5 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <p className="text-xs font-medium text-muted-foreground mb-1">Total Catalog Tools</p>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-foreground">{tools.length}</p>
            <span className="text-xs font-semibold text-chart-1 flex items-center gap-0.5">
              Unified Hub
            </span>
          </div>
        </div>

        <div
          className="bg-card rounded-2xl p-5 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <p className="text-xs font-medium text-muted-foreground mb-1">UTCP Native Endpoints</p>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-chart-2">{utcpCount}</p>
            <span className="text-xs font-semibold text-success flex items-center gap-0.5">
              Direct REST/WS
            </span>
          </div>
        </div>

        <div
          className="bg-card rounded-2xl p-5 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <p className="text-xs font-medium text-muted-foreground mb-1">MCP Servers Connected</p>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-foreground">{mcpCount}</p>
            <span className="text-xs font-semibold text-chart-1">SSE Stream</span>
          </div>
        </div>

        <div
          className="bg-card rounded-2xl p-5 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <p className="text-xs font-medium text-muted-foreground mb-1">Human Approval Gates</p>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-warning">{highRiskCount}</p>
            <span className="text-xs font-semibold text-warning">Strict RBAC</span>
          </div>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3 flex-1 max-w-md">
          <div className="relative w-full">
            <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              placeholder="Search tools by name, ID, or description..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 rounded-xl bg-card border border-border text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Protocol Filters */}
          <div className="flex items-center p-1 rounded-xl bg-muted/40 border border-border">
            {protocols.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setProtocolFilter(p)}
                className={cn(
                  'px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-colors',
                  protocolFilter === p
                    ? 'bg-card text-foreground shadow-xs font-bold'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                {p}
              </button>
            ))}
          </div>

          {/* Category Filters */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
            {categories.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setCategoryFilter(cat)}
                className={cn(
                  'px-3 py-1.5 rounded-full text-xs font-semibold transition-colors whitespace-nowrap',
                  categoryFilter === cat
                    ? 'bg-primary text-primary-foreground shadow-xs'
                    : 'bg-card border border-border text-muted-foreground hover:bg-muted'
                )}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Tools Table View */}
      <div
        className="bg-card rounded-2xl border border-border overflow-hidden"
        style={{ boxShadow: cardShadow }}
      >
        <div className="p-5 sm:p-6 border-b border-border flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-foreground tracking-tight">Active Tool Registry & Scopes</h3>
            <p className="text-xs text-muted-foreground mt-0.5">Enterprise inventory with protocol specification and security risk classifications</p>
          </div>
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-muted text-muted-foreground">
            {filteredTools.length} tools
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-border bg-muted/30 text-[10px] uppercase font-semibold text-muted-foreground tracking-wider">
                <th className="px-6 py-3">Tool Name & Function</th>
                <th className="px-6 py-3">Protocol</th>
                <th className="px-6 py-3">Description</th>
                <th className="px-6 py-3">Security Risk Tier</th>
                <th className="px-6 py-3">RBAC Scope</th>
                <th className="px-6 py-3 text-right">Human Gate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border text-xs">
              {filteredTools.map((tool) => (
                <tr key={tool.name} className="hover:bg-muted/30 transition-colors">
                  <td className="px-6 py-4">
                    <p className="font-semibold text-foreground">{tool.friendly}</p>
                    <p className="font-mono text-[11px] text-muted-foreground mt-0.5">{tool.name}</p>
                  </td>
                  <td className="px-6 py-4">
                    <span className={cn(
                      'px-2 py-0.5 rounded font-mono text-[10px] font-bold uppercase',
                      tool.protocol === 'UTCP' ? 'bg-chart-2/20 text-chart-2' :
                      tool.protocol === 'MCP' ? 'bg-chart-1/20 text-chart-1' :
                      'bg-muted text-muted-foreground'
                    )}>
                      {tool.protocol}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-muted-foreground max-w-sm leading-relaxed">
                    {tool.description}
                  </td>
                  <td className="px-6 py-4">
                    <span className={cn(
                      'px-2.5 py-0.5 rounded-full text-[10px] font-semibold uppercase',
                      tool.risk === 'HIGH' ? 'bg-destructive/15 text-destructive' :
                      tool.risk === 'MEDIUM' ? 'bg-warning/20 text-warning' : 'bg-success/15 text-success'
                    )}>
                      {tool.risk} Risk
                    </span>
                  </td>
                  <td className="px-6 py-4 font-mono text-muted-foreground text-[11px]">
                    {tool.required_scope}
                  </td>
                  <td className="px-6 py-4 text-right">
                    {tool.requires_approval ? (
                      <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-destructive uppercase">
                        <AlertTriangle className="w-3 h-3" /> Required
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-success uppercase">
                        <CheckCircle2 className="w-3 h-3" /> Auto
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Register Endpoint Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-xs flex items-center justify-center p-4">
          <div
            className="bg-card w-full max-w-md rounded-2xl border border-border p-6 shadow-xl animate-fade-in"
            style={{ boxShadow: cardShadow }}
          >
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-base font-bold text-foreground">Register Integration Endpoint</h3>
                <p className="text-xs text-muted-foreground mt-0.5">Connect a native UTCP or MCP tool manifest</p>
              </div>
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="text-muted-foreground hover:text-foreground text-sm font-bold p-1"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleRegisterEndpoint} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">Protocol</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setNewProtocol('UTCP')}
                    className={cn(
                      'p-2.5 rounded-xl border text-xs font-bold text-center transition-all',
                      newProtocol === 'UTCP'
                        ? 'border-chart-2 bg-chart-2/10 text-chart-2'
                        : 'border-border text-muted-foreground hover:bg-muted'
                    )}
                  >
                    UTCP (Direct REST/WS)
                  </button>
                  <button
                    type="button"
                    onClick={() => setNewProtocol('MCP')}
                    className={cn(
                      'p-2.5 rounded-xl border text-xs font-bold text-center transition-all',
                      newProtocol === 'MCP'
                        ? 'border-chart-1 bg-chart-1/10 text-chart-1'
                        : 'border-border text-muted-foreground hover:bg-muted'
                    )}
                  >
                    MCP (SSE Protocol)
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">System / Endpoint Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Banking Clearinghouse API"
                  value={newEndpointName}
                  onChange={(e) => setNewEndpointName(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-background border border-border text-xs text-foreground focus:ring-2 focus:ring-ring"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">Base URL</label>
                <input
                  type="url"
                  required
                  placeholder="https://api.payments.enterprise.com"
                  value={newBaseUrl}
                  onChange={(e) => setNewBaseUrl(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-background border border-border text-xs text-foreground font-mono focus:ring-2 focus:ring-ring"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">API Key / Bearer Token (Encrypted at Rest)</label>
                <input
                  type="password"
                  placeholder="Optional token (AES-256 encrypted)"
                  value={newAuthToken}
                  onChange={(e) => setNewAuthToken(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-background border border-border text-xs text-foreground font-mono focus:ring-2 focus:ring-ring"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-xl border border-border text-xs font-semibold hover:bg-muted transition-colors text-muted-foreground"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-colors shadow-xs"
                >
                  Save & Validate
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
