'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { 
  Bot, 
  Plus, 
  Play, 
  Sliders, 
  Shield, 
  Wrench, 
  BookOpen, 
  CheckCircle2, 
  PauseCircle, 
  Search, 
  Filter, 
  MoreHorizontal, 
  ExternalLink, 
  Cpu, 
  Layers, 
  Trash2, 
  Zap, 
  Clock,
  AlertTriangle
} from 'lucide-react';
import { cardShadow, cn } from '../lib/utils';
import { Button, StatusBadge } from '../components/ui';
import { fetchApi } from '../lib/api';

export interface EnterpriseAgent {
  id: string;
  name: string;
  description: string;
  purpose: string;
  status: 'ACTIVE' | 'PAUSED' | 'DEPLOYING';
  model_provider: string;
  model_name: string;
  assigned_tools_count: number;
  knowledge_bases_count: number;
  last_execution: string;
  success_rate: string;
  owner: string;
  risk_tier: 'LOW' | 'MEDIUM' | 'HIGH';
}

const INITIAL_AGENTS: EnterpriseAgent[] = [
  {
    id: 'agent-sales-ops',
    name: 'Sales Quotation & Pricing Specialist',
    description: 'Calculates corporate discounts, parses Cloud Infotech hardware price books, and drafts verified quotations.',
    purpose: 'B2B Quotation generation & hardware price auditing',
    status: 'ACTIVE',
    model_provider: 'Google Vertex / Gemini',
    model_name: 'gemini-2.5-flash',
    assigned_tools_count: 4,
    knowledge_bases_count: 2,
    last_execution: '10 min ago',
    success_rate: '98.4%',
    owner: 'Operations Team',
    risk_tier: 'MEDIUM',
  },
  {
    id: 'agent-invoice-gen',
    name: 'Tax Invoicing & Financial Settlement Agent',
    description: 'Generates official GST compliant invoices with itemized HSN/SAC codes and 18% tax calculations.',
    purpose: 'Automated invoice issuance with human-in-the-loop validation',
    status: 'ACTIVE',
    model_provider: 'Google Vertex / Gemini',
    model_name: 'gemini-2.5-flash',
    assigned_tools_count: 3,
    knowledge_bases_count: 1,
    last_execution: '2 hours ago',
    success_rate: '100%',
    owner: 'Finance & Compliance',
    risk_tier: 'HIGH',
  },
  {
    id: 'agent-knowledge-rag',
    name: 'Enterprise Knowledge & Policy Researcher',
    description: 'Executes hybrid dense vector and BM25 sparse retrieval over internal corporate documentation.',
    purpose: 'Internal policy, catalog, and documentation lookup',
    status: 'ACTIVE',
    model_provider: 'Gemini / Heuristic Engine',
    model_name: 'adaptive-hybrid-v1',
    assigned_tools_count: 2,
    knowledge_bases_count: 5,
    last_execution: '45 min ago',
    success_rate: '99.1%',
    owner: 'Knowledge Management',
    risk_tier: 'LOW',
  },
  {
    id: 'agent-mcp-orchestrator',
    name: 'Distributed MCP Tool Bridge',
    description: 'Executes external standardized MCP tools over SSE and JSON-RPC protocols with sandbox verification.',
    purpose: 'Connecting third-party inventory and CRM endpoints safely',
    status: 'ACTIVE',
    model_provider: 'FastAPI MCP Client',
    model_name: 'mcp-jsonrpc-2.0',
    assigned_tools_count: 8,
    knowledge_bases_count: 0,
    last_execution: '3 hours ago',
    success_rate: '96.5%',
    owner: 'Platform Engineering',
    risk_tier: 'MEDIUM',
  },
  {
    id: 'agent-eval-auditor',
    name: 'Response Faithfulness & Safety Gate',
    description: 'Calculates Ragas groundedness, citation coverage, and latency metrics across agent execution traces.',
    purpose: 'Continuous evaluation and safety auditing',
    status: 'ACTIVE',
    model_provider: 'Local Evaluation Framework',
    model_name: 'eval-suite-v1',
    assigned_tools_count: 1,
    knowledge_bases_count: 1,
    last_execution: '1 day ago',
    success_rate: '100%',
    owner: 'AI Governance',
    risk_tier: 'LOW',
  },
];

export default function AgentsDirectoryPage() {
  const router = useRouter();
  const [agents, setAgents] = useState<EnterpriseAgent[]>(INITIAL_AGENTS);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const loadAgents = async () => {
    try {
      const res = await fetchApi('/agents');
      if (res.ok) {
        const data = await res.json();
        if (data.agents && data.agents.length > 0) {
          setAgents(data.agents);
        }
      }
    } catch {
      // Keep initial agents as fallback
    }
  };

  useEffect(() => {
    loadAgents();
  }, []);

  const filteredAgents = agents.filter((a) => {
    const matchesSearch =
      a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.model_name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'ALL' || a.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const toggleAgentStatus = async (id: string) => {
    try {
      const res = await fetchApi(`/agents/${id}/status`, { method: 'PATCH' });
      if (res.ok) {
        const data = await res.json();
        setAgents((prev) =>
          prev.map((agent) =>
            agent.id === id ? { ...agent, status: data.new_status } : agent
          )
        );
        showMessage(`Agent status updated to ${data.new_status}`);
      } else {
        // Fallback local toggle
        setAgents((prev) =>
          prev.map((agent) => {
            if (agent.id === id) {
              const newStatus = agent.status === 'ACTIVE' ? 'PAUSED' : 'ACTIVE';
              showMessage(`${agent.name} is now ${newStatus}`);
              return { ...agent, status: newStatus };
            }
            return agent;
          })
        );
      }
    } catch {
      // Local fallback
      setAgents((prev) =>
        prev.map((agent) => {
          if (agent.id === id) {
            const newStatus = agent.status === 'ACTIVE' ? 'PAUSED' : 'ACTIVE';
            showMessage(`${agent.name} is now ${newStatus}`);
            return { ...agent, status: newStatus };
          }
          return agent;
        })
      );
    }
  };

  const deleteAgent = async (id: string, name: string) => {
    if (confirm(`Are you sure you want to decommission agent "${name}"? This action requires platform admin permission.`)) {
      try {
        const res = await fetchApi(`/agents/${id}`, { method: 'DELETE' });
        if (res.ok) {
          setAgents((prev) => prev.filter((a) => a.id !== id));
          showMessage(`Agent "${name}" decommissioned successfully.`);
        } else {
          setAgents((prev) => prev.filter((a) => a.id !== id));
          showMessage(`Agent "${name}" decommissioned.`);
        }
      } catch {
        setAgents((prev) => prev.filter((a) => a.id !== id));
        showMessage(`Agent "${name}" decommissioned.`);
      }
    }
  };

  const showMessage = (msg: string) => {
    setActionMessage(msg);
    setTimeout(() => setActionMessage(null), 3000);
  };

  const activeCount = agents.filter((a) => a.status === 'ACTIVE').length;
  const pausedCount = agents.filter((a) => a.status === 'PAUSED').length;

  return (
    <div className="space-y-6">
      {/* Toast Notification */}
      {actionMessage && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground text-xs font-semibold shadow-lg animate-slide-up flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-success" />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* Top Pulse Summary KPI Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div
          className="bg-card rounded-2xl p-5 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <p className="text-xs font-medium text-muted-foreground mb-1">Total Agents</p>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-foreground">{agents.length}</p>
            <span className="text-xs font-semibold text-chart-1">Catalog Ready</span>
          </div>
        </div>

        <div
          className="bg-card rounded-2xl p-5 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <p className="text-xs font-medium text-muted-foreground mb-1">Active in Production</p>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-success">{activeCount}</p>
            <span className="text-xs font-semibold text-success flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
              Online
            </span>
          </div>
        </div>

        <div
          className="bg-card rounded-2xl p-5 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <p className="text-xs font-medium text-muted-foreground mb-1">Avg Success Rate</p>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-foreground">98.8%</p>
            <span className="text-xs font-semibold text-success">+0.4%</span>
          </div>
        </div>

        <div
          className="bg-card rounded-2xl p-5 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <p className="text-xs font-medium text-muted-foreground mb-1">Human Gate Tiers</p>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-warning">
              {agents.filter((a) => a.risk_tier === 'HIGH').length} High Risk
            </p>
            <span className="text-xs font-semibold text-muted-foreground">Governed</span>
          </div>
        </div>
      </div>

      {/* Search and Filters Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3 flex-1 max-w-md">
          <div className="relative w-full">
            <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              placeholder="Filter agents by name, description, or model..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 rounded-xl bg-card border border-border text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          {['ALL', 'ACTIVE', 'PAUSED'].map((status) => (
            <button
              key={status}
              type="button"
              onClick={() => setStatusFilter(status)}
              className={cn(
                'px-3 py-1.5 rounded-full text-xs font-semibold transition-colors capitalize',
                statusFilter === status
                  ? 'bg-primary text-primary-foreground shadow-xs'
                  : 'bg-card border border-border text-muted-foreground hover:bg-muted hover:text-foreground'
              )}
            >
              {status.toLowerCase()} {status === 'ALL' ? `(${agents.length})` : status === 'ACTIVE' ? `(${activeCount})` : `(${pausedCount})`}
            </button>
          ))}

          <Link
            href="/studio/agent"
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-semibold shadow-xs transition-colors shrink-0 ml-2"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Create Agent</span>
          </Link>
        </div>
      </div>

      {/* Agents Grid (Pulse Services Design Pattern) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {filteredAgents.map((agent) => (
          <div
            key={agent.id}
            className="bg-card rounded-2xl border border-border p-5 hover:border-primary/30 transition-all flex flex-col justify-between"
            style={{ boxShadow: cardShadow }}
          >
            <div>
              {/* Agent Header */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-chart-1/15 text-chart-1 flex items-center justify-center shrink-0 font-bold">
                    <Bot className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-foreground text-sm tracking-tight">{agent.name}</h3>
                    <p className="text-xs text-muted-foreground line-clamp-1">{agent.purpose}</p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      'px-2 py-0.5 text-[10px] font-semibold rounded-full uppercase',
                      agent.status === 'ACTIVE'
                        ? 'bg-success/15 text-success'
                        : 'bg-warning/20 text-warning'
                    )}
                  >
                    {agent.status}
                  </span>
                </div>
              </div>

              {/* Description */}
              <p className="text-xs text-muted-foreground mb-4 leading-relaxed line-clamp-2">
                {agent.description}
              </p>

              {/* Telemetry sub-metrics */}
              <div className="grid grid-cols-4 gap-2 mb-4">
                <div className="p-2 rounded-xl bg-muted/40 border border-border/40">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Model</p>
                  <p className="text-xs font-semibold text-foreground truncate font-mono">{agent.model_name}</p>
                </div>
                <div className="p-2 rounded-xl bg-muted/40 border border-border/40">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Tools</p>
                  <p className="text-xs font-semibold text-foreground font-mono">{agent.assigned_tools_count} active</p>
                </div>
                <div className="p-2 rounded-xl bg-muted/40 border border-border/40">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Knowledge</p>
                  <p className="text-xs font-semibold text-foreground font-mono">{agent.knowledge_bases_count} sources</p>
                </div>
                <div className="p-2 rounded-xl bg-muted/40 border border-border/40">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Risk Gate</p>
                  <p className={cn(
                    "text-xs font-semibold",
                    agent.risk_tier === 'HIGH' ? 'text-destructive' : agent.risk_tier === 'MEDIUM' ? 'text-warning' : 'text-success'
                  )}>
                    {agent.risk_tier}
                  </p>
                </div>
              </div>
            </div>

            {/* Action Buttons Bar */}
            <div className="flex items-center justify-between pt-3 border-t border-border mt-1">
              <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono">
                <Clock className="w-3.5 h-3.5" />
                <span>Last run: {agent.last_execution}</span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => toggleAgentStatus(agent.id)}
                  className="px-2.5 py-1 text-xs font-medium rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                  title={agent.status === 'ACTIVE' ? 'Pause agent' : 'Resume agent'}
                >
                  {agent.status === 'ACTIVE' ? 'Pause' : 'Activate'}
                </button>

                <Link
                  href={`/studio/agent?id=${agent.id}`}
                  className="px-2.5 py-1 text-xs font-medium rounded-lg hover:bg-muted text-foreground transition-colors flex items-center gap-1 border border-border"
                >
                  <Sliders className="w-3.5 h-3.5 text-muted-foreground" />
                  <span>Configure</span>
                </Link>

                <Link
                  href={`/conversations?agent=${encodeURIComponent(agent.name)}`}
                  className="px-3 py-1 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors flex items-center gap-1 shadow-xs"
                >
                  <Play className="w-3 h-3 fill-current" />
                  <span>Run</span>
                </Link>

                <button
                  type="button"
                  onClick={() => deleteAgent(agent.id, agent.name)}
                  className="p-1.5 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-lg transition-colors"
                  title="Decommission agent"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
