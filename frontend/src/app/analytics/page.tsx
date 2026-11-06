'use client';
import { useState } from 'react';
import { 
  BarChart3, 
  TrendingUp, 
  DollarSign, 
  Clock, 
  Zap, 
  Cpu, 
  ShieldCheck, 
  ArrowUpRight,
  Sparkles
} from 'lucide-react';

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState('7d');

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">AI Analytics & Cost Intelligence</h1>
          <p className="text-xs text-slate-500 mt-1">
            Token expenditure, response latency distributions, model routing efficiency, and business tool usage.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 font-medium">Time Window:</span>
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 focus:border-blue-500 focus:outline-none"
          >
            <option value="24h">Past 24 Hours</option>
            <option value="7d">Past 7 Days</option>
            <option value="30d">Past 30 Days</option>
          </select>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
          <p className="text-xs font-medium text-slate-500">Estimated LLM Spend</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">$4.28</p>
          <span className="text-[11px] text-emerald-600 font-medium">92% via Gemini Flash (Cost Optimized)</span>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
          <p className="text-xs font-medium text-slate-500">Total Tokens Processed</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">1.84M</p>
          <span className="text-[11px] text-slate-500">Prompt: 1.2M • Completion: 640k</span>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
          <p className="text-xs font-medium text-slate-500">P95 Inference Latency</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">840ms</p>
          <span className="text-[11px] text-emerald-600 font-medium">Sub-second execution</span>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
          <p className="text-xs font-medium text-slate-500">Groundedness Score</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">0.94</p>
          <span className="text-[11px] text-emerald-600 font-medium">High factual retrieval fidelity</span>
        </div>
      </div>

      {/* Model Breakdown & Cost Efficiency */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs space-y-4">
          <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
            Model Routing Distribution
          </h3>

          <div className="space-y-3">
            {[
              { model: 'Gemini 2.5 Flash', share: 78, cost: '$2.12', calls: '1,420 calls' },
              { model: 'Gemini 2.5 Pro', share: 14, cost: '$1.86', calls: '84 calls' },
              { model: 'Adaptive Heuristic Engine', share: 8, cost: '$0.00 (Zero API Fee)', calls: '180 calls' },
            ].map((item) => (
              <div key={item.model} className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="font-semibold text-slate-800">{item.model}</span>
                  <span className="text-slate-500">{item.calls} • {item.cost}</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full"
                    style={{ width: `${item.share}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs space-y-4">
          <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
            Most Executed Business Tools
          </h3>

          <div className="divide-y divide-slate-100 text-xs">
            {[
              { tool: 'quotation.create_draft', calls: 342, success_rate: '99.4%' },
              { tool: 'quotation.calculate_pricing', calls: 512, success_rate: '100%' },
              { tool: 'invoice.generate', calls: 86, success_rate: '98.8%' },
              { tool: 'customer.search', calls: 418, success_rate: '100%' },
            ].map((t) => (
              <div key={t.tool} className="py-2.5 flex items-center justify-between">
                <div>
                  <span className="font-mono font-bold text-slate-900">{t.tool}</span>
                  <span className="text-[11px] text-slate-400 block">{t.calls} executions</span>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {t.success_rate} Success
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
