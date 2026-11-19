'use client';

import { useState } from 'react';
import { 
  BarChart3, 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Clock, 
  Zap, 
  Cpu, 
  ShieldCheck, 
  ArrowUpRight,
  Sparkles,
  Calendar,
  Layers,
  Activity
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts';
import { cardShadow, cn } from '../lib/utils';
import { Button } from '../components/ui';

const latencyTrend = [
  { time: '00:00', p50: 180, p95: 420, p99: 680 },
  { time: '04:00', p50: 160, p95: 390, p99: 640 },
  { time: '08:00', p50: 240, p95: 580, p99: 820 },
  { time: '12:00', p50: 290, p95: 640, p99: 920 },
  { time: '16:00', p50: 250, p95: 590, p99: 840 },
  { time: '20:00', p50: 210, p95: 490, p99: 720 },
  { time: 'Now', p50: 220, p95: 510, p99: 760 },
];

const tokenThroughput = [
  { time: '00:00', tokens: 18400 },
  { time: '04:00', tokens: 9200 },
  { time: '08:00', tokens: 48900 },
  { time: '12:00', tokens: 74200 },
  { time: '16:00', tokens: 62100 },
  { time: '20:00', tokens: 36800 },
  { time: 'Now', tokens: 42500 },
];

const agentPerformanceRows = [
  { name: 'Sales Quotation Specialist', model: 'gemini-2.5-flash', p50: 240, p95: 580, p99: 820, tokens: '640k', status: 'optimal' },
  { name: 'Tax Invoicing & GST Agent', model: 'gemini-2.5-flash', p50: 310, p95: 690, p99: 940, tokens: '380k', status: 'optimal' },
  { name: 'Knowledge & Policy RAG', model: 'adaptive-hybrid-v1', p50: 120, p95: 340, p99: 490, tokens: '140k', status: 'optimal' },
  { name: 'MCP Tool Orchestrator', model: 'mcp-jsonrpc-2.0', p50: 45, p95: 110, p99: 180, tokens: '85k', status: 'optimal' },
  { name: 'Response Faithfulness Gate', model: 'eval-suite-v1', p50: 180, p95: 410, p99: 610, tokens: '55k', status: 'optimal' },
];

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState('7d');

  return (
    <div className="space-y-6 pb-12">
      {/* 4 Pulse KPI Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div
          className="bg-card rounded-2xl p-5 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <p className="text-xs font-medium text-muted-foreground mb-1">Estimated LLM Spend</p>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-foreground font-sans">$4.28</p>
            <span className="text-xs font-semibold text-success flex items-center gap-0.5">
              <TrendingDown className="w-3.5 h-3.5" /> -14% vs budget
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground mt-1">92% via Gemini Flash (Cost-Optimized)</p>
        </div>

        <div
          className="bg-card rounded-2xl p-5 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <p className="text-xs font-medium text-muted-foreground mb-1">Total Tokens Processed</p>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-foreground font-sans">1.84M</p>
            <span className="text-xs font-semibold text-chart-1">+18.2%</span>
          </div>
          <p className="text-[11px] text-muted-foreground mt-1">1.2M Prompt • 640k Completion</p>
        </div>

        <div
          className="bg-card rounded-2xl p-5 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <p className="text-xs font-medium text-muted-foreground mb-1">P95 Inference Latency</p>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-foreground font-sans">510ms</p>
            <span className="text-xs font-semibold text-success flex items-center gap-0.5">
              <TrendingDown className="w-3.5 h-3.5" /> -45ms
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground mt-1">Sub-second execution standard</p>
        </div>

        <div
          className="bg-card rounded-2xl p-5 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <p className="text-xs font-medium text-muted-foreground mb-1">Groundedness Fidelity</p>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-foreground font-sans">0.94</p>
            <span className="text-xs font-semibold text-success flex items-center gap-0.5">
              <TrendingUp className="w-3.5 h-3.5" /> High
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground mt-1">Factual retrieval verification score</p>
        </div>
      </div>

      {/* Dual Charts Row: Latency Distribution + Token Throughput */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Latency Percentiles LineChart */}
        <div
          className="bg-card rounded-2xl p-6 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-base font-semibold text-foreground tracking-tight">Latency Distribution</h3>
              <p className="text-xs text-muted-foreground mt-0.5">P50, P95, and P99 inference latency over time (ms)</p>
            </div>
            <div className="flex items-center gap-4 text-xs font-medium">
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-chart-2" />
                <span className="text-muted-foreground">P50</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-chart-1" />
                <span className="text-muted-foreground">P95</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-chart-3" />
                <span className="text-muted-foreground">P99</span>
              </div>
            </div>
          </div>

          <div className="h-[240px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={latencyTrend}>
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
                <Line type="monotone" dataKey="p50" stroke="oklch(0.65 0.15 155)" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="p95" stroke="oklch(0.55 0.18 250)" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="p99" stroke="oklch(0.7 0.18 350)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Token Throughput AreaChart */}
        <div
          className="bg-card rounded-2xl p-6 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-base font-semibold text-foreground tracking-tight">Token Throughput</h3>
              <p className="text-xs text-muted-foreground mt-0.5">Tokens processed per hour across active models</p>
            </div>
            <div className="flex items-center gap-1.5 text-xs font-semibold text-chart-1">
              <Zap className="w-3.5 h-3.5" />
              <span>42.5k / hour</span>
            </div>
          </div>

          <div className="h-[240px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={tokenThroughput}>
                <defs>
                  <linearGradient id="tokenGradient" x1="0" y1="0" x2="0" y2="1">
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
                  dataKey="tokens"
                  stroke="oklch(0.55 0.18 250)"
                  strokeWidth={2}
                  fill="url(#tokenGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Agent Performance & Latencies Table (Pulse Service Latencies Pattern) */}
      <div
        className="bg-card rounded-2xl border border-border overflow-hidden"
        style={{ boxShadow: cardShadow }}
      >
        <div className="p-5 sm:p-6 border-b border-border">
          <h3 className="text-base font-semibold text-foreground tracking-tight">Agent Latency Benchmarks</h3>
          <p className="text-xs text-muted-foreground mt-0.5">Current percentile response latencies and token volume by agent</p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-border bg-muted/30 text-[10px] uppercase font-semibold text-muted-foreground tracking-wider">
                <th className="px-6 py-3">Agent</th>
                <th className="px-6 py-3">Inference Model</th>
                <th className="px-6 py-3 text-right">P50 Latency</th>
                <th className="px-6 py-3 text-right">P95 Latency</th>
                <th className="px-6 py-3 text-right">P99 Latency</th>
                <th className="px-6 py-3 text-right">Tokens</th>
                <th className="px-6 py-3 text-right">Efficiency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border text-xs">
              {agentPerformanceRows.map((row) => (
                <tr key={row.name} className="hover:bg-muted/30 transition-colors">
                  <td className="px-6 py-4 font-semibold text-foreground">{row.name}</td>
                  <td className="px-6 py-4 font-mono text-[11px] text-muted-foreground">{row.model}</td>
                  <td className="px-6 py-4 text-right font-mono text-muted-foreground">{row.p50}ms</td>
                  <td className="px-6 py-4 text-right font-mono text-muted-foreground">{row.p95}ms</td>
                  <td className="px-6 py-4 text-right font-mono text-muted-foreground">{row.p99}ms</td>
                  <td className="px-6 py-4 text-right font-mono text-foreground font-semibold">{row.tokens}</td>
                  <td className="px-6 py-4 text-right">
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-success/15 text-success uppercase">
                      {row.status}
                    </span>
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
