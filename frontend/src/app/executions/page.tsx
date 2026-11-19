'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { 
  Sparkles,
  PlaySquare, 
  CheckCircle, 
  XCircle, 
  Clock, 
  AlertTriangle, 
  RefreshCw, 
  Filter, 
  Search, 
  ExternalLink, 
  Bot, 
  Cpu, 
  Wrench, 
  BookOpen, 
  Layers, 
  Terminal, 
  ShieldAlert,
  ChevronRight,
  ArrowRight
} from 'lucide-react';
import { fetchApi } from '../lib/api';
import { cardShadow, cn } from '../lib/utils';
import { Button, StatusBadge } from '../components/ui';

interface ExecutionStep {
  step_number: number;
  name: string;
  description: string;
  status: 'COMPLETED' | 'RUNNING' | 'FAILED' | 'PENDING_APPROVAL';
  duration_ms: number;
  tool_called?: string;
  tokens_used?: number;
}

interface ExecutionRun {
  id: string;
  goal: string;
  agent_name: string;
  workflow_name?: string;
  current_action?: string;
  next_action?: string;
  status: 'COMPLETED' | 'RUNNING' | 'FAILED' | 'PENDING_APPROVAL';
  created_at: string;
  execution_time_seconds: number;
  risk_level: 'READ_ONLY' | 'SIDE_EFFECT' | 'FINANCIAL' | 'HIGH_RISK';
  token_usage: {
    input: number;
    output: number;
    total: number;
  };
  steps: ExecutionStep[];
  final_result?: string;
  error_message?: string;
}

const statusConfig = {
  COMPLETED: { label: 'Completed', color: 'bg-success/15 text-success' },
  RUNNING: { label: 'Running', color: 'bg-chart-1/15 text-chart-1' },
  FAILED: { label: 'Failed', color: 'bg-destructive/15 text-destructive' },
  PENDING_APPROVAL: { label: 'Awaiting Gate', color: 'bg-warning/20 text-warning' },
};

const riskConfig = {
  READ_ONLY: { label: 'Read Only', color: 'bg-muted text-muted-foreground' },
  SIDE_EFFECT: { label: 'Side Effect', color: 'bg-chart-1/15 text-chart-1' },
  FINANCIAL: { label: 'Financial', color: 'bg-warning/20 text-warning' },
  HIGH_RISK: { label: 'High Risk', color: 'bg-destructive/15 text-destructive' },
};

export default function ExecutionsPage() {
  const [runs, setRuns] = useState<ExecutionRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<ExecutionRun | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  async function loadExecutions() {
    setIsRefreshing(true);
    try {
      const res = await fetchApi('/runs?limit=30');
      if (res.ok) {
        const data = await res.json();
        const items = data.items || data.runs || [];

        const mapped: ExecutionRun[] = items.map((r: any, idx: number) => {
          const rawStatus = (r.status || 'COMPLETED').toUpperCase();
          const normalizedStatus = 
            rawStatus === 'WAITING FOR APPROVAL' || rawStatus === 'PENDING_APPROVAL' || rawStatus === 'AWAITING_APPROVAL' ? 'PENDING_APPROVAL' :
            rawStatus === 'FAILED' ? 'FAILED' :
            rawStatus === 'RUNNING' ? 'RUNNING' : 'COMPLETED';

          const goal = r.instruction || r.user_request || r.goal || r.task || 'Process enterprise request';
          
          const rawSteps = r.steps && Array.isArray(r.steps) && r.steps.length > 0 ? r.steps : [];
          const steps: ExecutionStep[] = rawSteps.length > 0
            ? rawSteps.map((st: any, sIdx: number) => {
                const rawSt = (st.status || 'COMPLETED').toUpperCase();
                const stepStatus = 
                  rawSt === 'WAITING FOR APPROVAL' || rawSt === 'PENDING_APPROVAL' || rawSt === 'WAITING' ? 'PENDING_APPROVAL' :
                  rawSt === 'FAILED' || rawSt === 'ERROR' ? 'FAILED' :
                  rawSt === 'RUNNING' || rawSt === 'IN_PROGRESS' ? 'RUNNING' : 'COMPLETED';
                return {
                  step_number: st.step_number || (sIdx + 1),
                  name: st.name || st.title || `Step ${sIdx + 1}`,
                  description: st.description || st.output || 'Step execution recorded by runtime.',
                  status: stepStatus,
                  duration_ms: st.duration_ms || 120,
                  tool_called: st.tool_called || st.tool_name,
                  tokens_used: st.tokens_used,
                };
              })
            : [
                {
                  step_number: 1,
                  name: 'Instruction Ingestion',
                  description: `Ingested instruction: ${goal}`,
                  status: 'COMPLETED',
                  duration_ms: 65,
                  tokens_used: 95,
                },
                {
                  step_number: 2,
                  name: 'Workflow Execution & Tool Verification',
                  description: normalizedStatus === 'FAILED' ? (r.error_message || 'Execution halted with error') : (normalizedStatus === 'PENDING_APPROVAL' ? 'Awaiting Human-in-the-Loop approval gate' : 'Workflow execution completed successfully.'),
                  status: normalizedStatus,
                  duration_ms: r.latency_ms || 320,
                  tokens_used: (r.token_usage?.input || r.total_tokens_input || 180),
                }
              ];

          const runId = r.run_id || r.id || (r.started_at ? `run-${r.started_at}` : `run-entry-${idx + 1}`);
          return {
            id: String(runId),
            goal: goal,
            agent_name: r.agent_name || (r.workflow_name ? `Workflow: ${r.workflow_name}` : 'AURA Operations Agent'),
            workflow_name: r.workflow_name,
            current_action: r.current_action,
            next_action: r.next_action,
            status: normalizedStatus,
            created_at: r.created_at ? new Date(r.created_at).toLocaleString() : 'Just now',
            execution_time_seconds: r.execution_time_seconds || (r.latency_ms ? (r.latency_ms / 1000).toFixed(2) : 1.2),
            risk_level: normalizedStatus === 'PENDING_APPROVAL' ? 'FINANCIAL' : (normalizedStatus === 'FAILED' ? 'HIGH_RISK' : 'SIDE_EFFECT'),
            token_usage: {
              input: r.token_usage?.input ?? (r.total_tokens_input || 240),
              output: r.token_usage?.output ?? (r.total_tokens_output || 110),
              total: r.token_usage?.total ?? ((r.total_tokens_input || 240) + (r.total_tokens_output || 110)),
            },
            steps,
            final_result: r.final_result || r.final_response || (normalizedStatus === 'PENDING_APPROVAL' ? 'Execution suspended at Human-in-the-Loop governance gate.' : 'Execution completed.'),
            error_message: r.error_message,
          };
        });

        setRuns(mapped);
        if (mapped.length > 0 && !selectedRun) {
          setSelectedRun(mapped[0]);
        }
      }
    } catch (e) {
      console.warn('Executions load error', e);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }

  useEffect(() => {
    loadExecutions();
  }, []);

  const filteredRuns = runs.filter((r) => {
    const matchesSearch = 
      r.goal.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.agent_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = filterStatus === 'all' || r.status.toLowerCase() === filterStatus.toLowerCase();
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="flex flex-col lg:flex-row gap-6 h-[calc(100vh-140px)] min-h-[600px]">
      {/* Left Master List (Pulse Incident List Pattern - 420px wide) */}
      <div className="w-full lg:w-[420px] flex flex-col shrink-0 h-full">
        {/* Search & Refresh */}
        <div className="flex items-center gap-2 mb-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
            <input
              type="text"
              placeholder="Search by ID, agent, or task..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 rounded-xl bg-card border border-border text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
          <button
            type="button"
            onClick={loadExecutions}
            className="p-2 rounded-xl bg-card border border-border text-muted-foreground hover:text-foreground transition-colors"
            title="Refresh runs"
          >
            <RefreshCw className={cn('w-4 h-4', isRefreshing && 'animate-spin')} />
          </button>
        </div>

        {/* Filter Pills */}
        <div className="flex gap-1.5 mb-3 overflow-x-auto pb-1 shrink-0">
          {['all', 'completed', 'running', 'failed', 'pending_approval'].map((st) => (
            <button
              key={st}
              type="button"
              onClick={() => setFilterStatus(st)}
              className={cn(
                'px-2.5 py-1 text-[11px] font-semibold rounded-full transition-colors capitalize whitespace-nowrap',
                filterStatus === st
                  ? 'bg-primary text-primary-foreground shadow-xs'
                  : 'bg-card border border-border text-muted-foreground hover:bg-muted'
              )}
            >
              {st === 'pending_approval' ? 'Gate Required' : st}
            </button>
          ))}
        </div>

        {/* List of Runs */}
        <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
          {filteredRuns.length === 0 ? (
            <div className="p-8 text-center text-xs text-muted-foreground bg-card rounded-2xl border border-border">
              No executions found matching filter.
            </div>
          ) : (
            filteredRuns.map((r) => {
              const isSelected = selectedRun?.id === r.id;
              const statusCfg = statusConfig[r.status];
              const riskCfg = riskConfig[r.risk_level];

              return (
                <div
                  key={r.id}
                  onClick={() => setSelectedRun(r)}
                  className={cn(
                    'w-full text-left p-3.5 rounded-2xl border transition-all cursor-pointer',
                    isSelected
                      ? 'bg-card border-primary/40 shadow-sm ring-1 ring-primary/20'
                      : 'bg-card border-border hover:border-primary/20 hover:bg-muted/30'
                  )}
                  style={{ boxShadow: isSelected ? cardShadow : 'none' }}
                >
                  <div className="flex items-start justify-between mb-1.5">
                    <span className={cn('px-2 py-0.5 text-[10px] font-semibold rounded-full', riskCfg.color)}>
                      {riskCfg.label}
                    </span>
                    <span className="text-[10px] text-muted-foreground font-mono">{r.id.slice(0, 10)}...</span>
                  </div>

                  <p className="text-xs font-semibold text-foreground mb-1 line-clamp-2 leading-snug">
                    {r.goal}
                  </p>

                  <div className="flex items-center justify-between text-[11px] text-muted-foreground mt-2">
                    <span className={cn('px-2 py-0.5 text-[10px] font-semibold rounded-full', statusCfg.color)}>
                      {statusCfg.label}
                    </span>
                    <div className="flex items-center gap-1 font-mono text-[10px]">
                      <Clock className="w-3 h-3" />
                      <span>{r.execution_time_seconds}s</span>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Right Execution Detail (Pulse Incident Detail Pattern) */}
      <div 
        className="flex-1 bg-card rounded-2xl border border-border p-6 overflow-y-auto"
        style={{ boxShadow: cardShadow }}
      >
        {selectedRun ? (
          <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-4 border-b border-border">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className={cn(
                    'px-2.5 py-0.5 text-xs font-semibold rounded-full',
                    riskConfig[selectedRun.risk_level].color
                  )}>
                    {riskConfig[selectedRun.risk_level].label}
                  </span>
                  <span className={cn(
                    'px-2.5 py-0.5 text-xs font-semibold rounded-full',
                    statusConfig[selectedRun.status].color
                  )}>
                    {statusConfig[selectedRun.status].label}
                  </span>
                  <span className="text-xs font-mono text-muted-foreground">{selectedRun.created_at}</span>
                </div>
                <h2 className="text-lg font-bold text-foreground leading-snug">
                  {selectedRun.goal}
                </h2>
                <p className="text-xs font-mono text-muted-foreground mt-1">
                  Run ID: {selectedRun.id} • Orchestrator: {selectedRun.agent_name}
                </p>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <Link
                  href={`/conversations?resume=${selectedRun.id}`}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-semibold shadow-xs transition"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span>Open in Chat</span>
                </Link>
              </div>
            </div>

            {/* Current Activity & Recommended Next Action Banner */}
            {selectedRun.next_action && (
              <div className="p-3.5 rounded-xl bg-primary/10 border border-primary/20 flex items-start gap-3">
                <Sparkles className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 mb-0.5">
                    <h4 className="text-[11px] font-bold text-primary uppercase tracking-wider">
                      Current Activity &amp; Guidance
                    </h4>
                    {selectedRun.current_action && (
                      <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-card border border-border text-muted-foreground">
                        {selectedRun.current_action}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-foreground/90 leading-relaxed">{selectedRun.next_action}</p>
                  {selectedRun.status === 'PENDING_APPROVAL' && (
                    <div className="mt-2.5">
                      <Link 
                        href="/approvals" 
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-warning text-warning-foreground text-xs font-bold shadow-xs hover:bg-warning/90 transition"
                      >
                        <span>Open Approvals &amp; Authorize</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Failure Diagnostic Banner */}
            {selectedRun.status === 'FAILED' && selectedRun.error_message && (
              <div className="p-3.5 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive">
                <div className="flex items-center gap-2 font-bold text-xs mb-1">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>Execution Failure Diagnostic</span>
                </div>
                <p className="font-mono text-[11px] leading-relaxed text-destructive/90">{selectedRun.error_message}</p>
              </div>
            )}

            {/* 3 Summary KPI Tiles */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="p-3.5 rounded-xl bg-muted/40 border border-border/50">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Execution Duration</p>
                <p className="text-base font-bold text-foreground font-mono flex items-center gap-1.5">
                  <Clock className="w-4 h-4 text-chart-1" />
                  {selectedRun.execution_time_seconds}s
                </p>
              </div>
              <div className="p-3.5 rounded-xl bg-muted/40 border border-border/50">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Tokens Consumed</p>
                <p className="text-base font-bold text-foreground font-mono flex items-center gap-1.5">
                  <Cpu className="w-4 h-4 text-chart-2" />
                  {selectedRun.token_usage.total.toLocaleString()} tokens
                </p>
              </div>
              <div className="p-3.5 rounded-xl bg-muted/40 border border-border/50">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Steps Executed</p>
                <p className="text-base font-bold text-foreground font-mono flex items-center gap-1.5">
                  <Layers className="w-4 h-4 text-chart-1" />
                  {selectedRun.steps.length} sequential steps
                </p>
              </div>
            </div>

            {/* Step-by-Step Execution Timeline (Pulse Incident Timeline Pattern) */}
            <div>
              <h3 className="text-xs font-bold text-foreground uppercase tracking-wider mb-3">
                Execution Steps & Trace Events
              </h3>
              <div className="space-y-3">
                {selectedRun.steps.map((st) => (
                  <div key={st.step_number} className="flex items-start gap-3 p-3.5 rounded-xl bg-muted/30 border border-border/40">
                    <div className={cn(
                      'w-7 h-7 rounded-lg flex items-center justify-center shrink-0 text-xs font-bold font-mono',
                      st.status === 'COMPLETED' ? 'bg-success/15 text-success' :
                      st.status === 'FAILED' ? 'bg-destructive/15 text-destructive' :
                      st.status === 'PENDING_APPROVAL' ? 'bg-warning/20 text-warning' : 'bg-chart-1/15 text-chart-1'
                    )}>
                      {st.status === 'COMPLETED' ? <CheckCircle className="w-3.5 h-3.5" /> : st.step_number}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <h4 className="text-xs font-bold text-foreground">{st.name}</h4>
                        <span className="text-[10px] font-mono text-muted-foreground">{st.duration_ms}ms</span>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">{st.description}</p>
                      {st.tool_called && (
                        <div className="mt-1.5 flex items-center gap-2">
                          <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-muted text-foreground border border-border/60">
                            Tool: {st.tool_called}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Final Outcome / Artifact Result */}
            <div>
              <h3 className="text-xs font-bold text-foreground uppercase tracking-wider mb-2">
                Execution Outcome
              </h3>
              <div className="p-4 rounded-xl bg-muted/20 border border-border font-mono text-xs text-foreground whitespace-pre-wrap leading-relaxed">
                {selectedRun.final_result}
              </div>
            </div>
          </div>
        ) : (
          <div className="h-full flex items-center justify-center text-xs text-muted-foreground">
            Select an execution from the list to view trace details.
          </div>
        )}
      </div>
    </div>
  );
}
