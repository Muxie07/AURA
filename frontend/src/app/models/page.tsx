'use client';
import { useState } from 'react';
import { 
  Cpu, 
  CheckCircle2, 
  Key, 
  ExternalLink, 
  ShieldCheck, 
  RefreshCw, 
  Sliders,
  AlertCircle
} from 'lucide-react';

interface ModelProvider {
  id: string;
  name: string;
  status: 'ACTIVE' | 'CONFIGURED' | 'DISABLED';
  models: string[];
  latency_tier: string;
  cost_tier: string;
  description: string;
}

const PROVIDERS_DATA: ModelProvider[] = [
  {
    id: 'google',
    name: 'Google Vertex AI & Gemini API',
    status: 'ACTIVE',
    models: ['gemini-2.5-flash', 'gemini-2.5-pro'],
    latency_tier: 'Ultra Low (~350ms)',
    cost_tier: 'Lowest Cost / 1M Tokens',
    description: 'Primary platform reasoning engine powering agent planning, JSON schema validation, and tool calling.',
  },
  {
    id: 'openai',
    name: 'OpenAI Enterprise Gateway',
    status: 'CONFIGURED',
    models: ['gpt-4o', 'gpt-4o-mini'],
    latency_tier: 'Low (~600ms)',
    cost_tier: 'Standard Enterprise',
    description: 'Secondary routing provider with automatic circuit breaker fallback on rate limits.',
  },
  {
    id: 'anthropic',
    name: 'Anthropic Claude Engine',
    status: 'CONFIGURED',
    models: ['claude-3-7-sonnet', 'claude-3-5-haiku'],
    latency_tier: 'Medium (~750ms)',
    cost_tier: 'High Precision Tier',
    description: 'Specialized deep document analysis and complex multi-agent contract evaluation.',
  },
  {
    id: 'heuristic',
    name: 'AURA Adaptive Heuristic & Offline Fallback',
    status: 'ACTIVE',
    models: ['adaptive-hybrid-v1'],
    latency_tier: 'Instant (<15ms)',
    cost_tier: 'Zero Token Cost',
    description: 'Internal deterministic engine for quotations, mathematical GST computation, and catalog search.',
  }
];

export default function ModelProvidersPage() {
  const [providers, setProviders] = useState<ModelProvider[]>(PROVIDERS_DATA);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Model Providers & Circuit Routing</h1>
          <p className="text-xs text-slate-500 mt-1">
            Manage LLM credentials, set rate limits, configure circuit breaker fallbacks, and track model health.
          </p>
        </div>
      </div>

      {/* Providers Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {providers.map((p) => (
          <div
            key={p.id}
            className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div className="flex items-center gap-2.5">
                  <div className="h-8 w-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
                    <Cpu className="h-4 w-4" />
                  </div>
                  <div>
                    <h3 className="text-xs font-bold text-slate-900">{p.name}</h3>
                    <span className="text-[10px] text-slate-400 font-mono">provider_id: {p.id}</span>
                  </div>
                </div>

                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                  p.status === 'ACTIVE' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-slate-100 text-slate-600'
                }`}>
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  {p.status}
                </span>
              </div>

              <p className="text-xs text-slate-600 my-3 leading-relaxed">
                {p.description}
              </p>

              <div className="space-y-1.5 bg-slate-50 p-3 rounded-lg text-xs mb-4">
                <div className="flex justify-between">
                  <span className="text-slate-500">Latency Profile:</span>
                  <span className="font-semibold text-slate-800">{p.latency_tier}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Cost Tier:</span>
                  <span className="font-semibold text-slate-800">{p.cost_tier}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Available Models:</span>
                  <span className="font-mono text-slate-700 font-semibold">{p.models.join(', ')}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-slate-100 text-xs">
              <span className="text-[11px] text-slate-400">Keys encrypted in KMS</span>
              <button className="px-3 py-1 rounded-lg border border-slate-200 hover:bg-slate-50 font-semibold text-slate-700 transition">
                Configure Keys & Quota
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
