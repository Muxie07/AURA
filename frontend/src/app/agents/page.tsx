'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
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
  MoreVertical,
  ExternalLink,
  Search,
  Filter
} from 'lucide-react';
import { fetchApi } from '../lib/api';

export interface EnterpriseAgent {
  id: string;
  name: string;
  description: string;
  purpose: string;
  status: 'ACTIVE' | 'PAUSED' | 'DEPLOYING' | 'DRAFT';
  model_provider: string;
  model_name: string;
  assigned_tools_count: number;
  knowledge_bases_count: number;
  last_execution: string;
  owner: string;
  risk_tier: 'LOW' | 'MEDIUM' | 'HIGH';
}

const DEFAULT_ENTERPRISE_AGENTS: EnterpriseAgent[] = [
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
    last_execution: '10 minutes ago',
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
    last_execution: '45 minutes ago',
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
    owner: 'Platform Engineering',
    risk_tier: 'MEDIUM',
  },
  {
    id: 'agent-eval-auditor',
    name: 'Response Faithfulness & Eval Gate',
    description: 'Calculates Ragas groundedness, citation coverage, and latency metrics across agent execution traces.',
    purpose: 'Continuous evaluation and safety auditing',
    status: 'ACTIVE',
    model_provider: 'Local Evaluation Framework',
    model_name: 'eval-suite-v1',
    assigned_tools_count: 1,
    knowledge_bases_count: 1,
    last_execution: '1 day ago',
    owner: 'AI Governance',
    risk_tier: 'LOW',
  }
];

export default function AgentsDirectoryPage() {
  const [agents, setAgents] = useState<EnterpriseAgent[]>(DEFAULT_ENTERPRISE_AGENTS);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const filteredAgents = agents.filter(a => {
    const matchesSearch = a.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          a.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'ALL' || a.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Enterprise Agents Directory</h1>
          <p className="text-xs text-slate-500 mt-1">
            Governed AI agents configured with explicit tool sets, role permissions, and knowledge boundaries.
          </p>
        </div>
        <Link
          href="/studio/agent"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 transition shadow-xs"
        >
          <Plus className="h-4 w-4" />
          Create New Agent
        </Link>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search agents by name, purpose, or model..."
            className="w-full rounded-lg border border-slate-200 bg-slate-50/60 pl-9 pr-3 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-500 transition"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-400" />
          <span className="text-xs text-slate-500 font-medium">Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="ALL">All Statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="PAUSED">Paused</option>
            <option value="DRAFT">Draft</option>
          </select>
        </div>
      </div>

      {/* Agents Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filteredAgents.map((agent) => (
          <div
            key={agent.id}
            className="flex flex-col justify-between bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs hover:border-slate-300 hover:shadow-sm transition-all"
          >
            <div>
              {/* Card Header */}
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="flex items-center gap-2.5">
                  <div className="h-9 w-9 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
                    <Bot className="h-5 w-5" />
                  </div>
                  <div>
                    <h2 className="text-sm font-bold text-slate-900 leading-tight">{agent.name}</h2>
                    <span className="text-[10px] text-slate-400 font-medium">{agent.owner}</span>
                  </div>
                </div>
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                  agent.status === 'ACTIVE' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200/60' : 'bg-slate-100 text-slate-600'
                }`}>
                  {agent.status}
                </span>
              </div>

              {/* Description */}
              <p className="text-xs text-slate-600 line-clamp-2 mb-4 leading-relaxed">
                {agent.description}
              </p>

              {/* Key Meta Badges */}
              <div className="grid grid-cols-2 gap-2 p-2.5 bg-slate-50 rounded-lg text-[11px] mb-4">
                <div>
                  <span className="text-slate-400 block text-[10px]">Model Provider</span>
                  <span className="font-semibold text-slate-700 truncate block">{agent.model_name}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">Risk Tier</span>
                  <span className={`font-semibold inline-block ${
                    agent.risk_tier === 'HIGH' ? 'text-amber-600' : 'text-slate-700'
                  }`}>
                    {agent.risk_tier} Risk
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">Assigned Tools</span>
                  <span className="font-semibold text-slate-700">{agent.assigned_tools_count} Tools</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">Knowledge Sources</span>
                  <span className="font-semibold text-slate-700">{agent.knowledge_bases_count} Bases</span>
                </div>
              </div>
            </div>

            {/* Actions Footer */}
            <div className="flex items-center justify-between pt-3 border-t border-slate-100">
              <span className="text-[11px] text-slate-400">Run: {agent.last_execution}</span>
              <div className="flex items-center gap-1.5">
                <Link
                  href={`/studio/agent?id=${agent.id}`}
                  className="px-2.5 py-1 rounded-md border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-semibold transition"
                >
                  Configure
                </Link>
                <Link
                  href={`/conversations?agent=${agent.id}`}
                  className="px-2.5 py-1 rounded-md bg-blue-600 text-white hover:bg-blue-700 text-xs font-semibold transition flex items-center gap-1"
                >
                  <Play className="h-3 w-3" />
                  Test
                </Link>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
