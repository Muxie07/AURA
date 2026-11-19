'use client';

import React, { useState } from 'react';
import { 
  Play, 
  Square, 
  Search, 
  BarChart3, 
  PenTool, 
  CheckCircle2, 
  Save, 
  MoreVertical, 
  Sparkles, 
  ChevronLeft, 
  ChevronRight, 
  Mail, 
  Plus, 
  Minus, 
  Maximize2, 
  Check, 
  X, 
  Terminal, 
  Database 
} from 'lucide-react';
import { cn } from '../lib/utils';
import { fetchApi } from '../lib/api';

interface AgentNode {
  id: string;
  type: 'start' | 'researcher' | 'analyst' | 'writer' | 'reviewer' | 'approval' | 'end';
  title: string;
  role: string;
  model: string;
  status: 'idle' | 'running' | 'waiting_approval' | 'completed' | 'failed';
  borderColor: string;
  badgeColor: string;
  icon: string;
  x: number; // grid layout coordinates for canvas
  y: number;
  outputLog?: string;
  config?: Record<string, any>;
}

interface WorkflowTemplate {
  id: string;
  title: string;
  description: string;
  nodeCount: number;
  isAuto?: boolean;
  nodes: AgentNode[];
}

const TEMPLATES: WorkflowTemplate[] = [
  {
    id: 'tmpl-content-review',
    title: 'Content Review Pipeline',
    description: 'Enter a topic or brief -- the Writer drafts content, the Reviewer critiques it, then you approve before publish...',
    nodeCount: 5,
    nodes: [
      { id: 'n-start', type: 'start', title: 'Start', role: 'Entry Point', model: '', status: 'idle', borderColor: 'border-emerald-500/80', badgeColor: 'bg-emerald-500/15 text-emerald-400', icon: 'start', x: 20, y: 140 },
      { id: 'n-scout', type: 'researcher', title: 'Trend Scout', role: 'Researcher', model: 'gemini-2.5-flash', status: 'idle', borderColor: 'border-cyan-500/80', badgeColor: 'bg-cyan-500/15 text-cyan-400', icon: 'search', x: 230, y: 60, outputLog: 'Synthesized 14 market trends and competitive pricing indexes.' },
      { id: 'n-analyst', type: 'analyst', title: 'Impact Analyst', role: 'Analyst', model: 'gemini-2.5-flash', status: 'idle', borderColor: 'border-amber-500/80', badgeColor: 'bg-amber-500/15 text-amber-400', icon: 'chart', x: 470, y: 60, outputLog: 'Quantified margin impact: +18.4% gross profit at standard tier.' },
      { id: 'n-moderator', type: 'writer', title: 'Roundtable Moderator', role: 'Writer', model: 'gemini-2.5-flash', status: 'idle', borderColor: 'border-purple-500/80', badgeColor: 'bg-purple-500/15 text-purple-400', icon: 'writer', x: 710, y: 60, outputLog: 'Structured commercial quotation terms & SLA clauses.' },
      { id: 'n-polish', type: 'reviewer', title: 'Fact-Check & Polish', role: 'Reviewer', model: 'gemini-2.5-flash', status: 'idle', borderColor: 'border-emerald-500/80', badgeColor: 'bg-emerald-500/15 text-emerald-400', icon: 'check', x: 470, y: 220, outputLog: 'Audited 100% compliance with corporate rate card.' },
      { id: 'n-end', type: 'end', title: 'End', role: 'Termination', model: '', status: 'idle', borderColor: 'border-slate-500/80', badgeColor: 'bg-slate-500/15 text-slate-400', icon: 'stop', x: 710, y: 220 }
    ]
  },
  {
    id: 'tmpl-quotation-pipeline',
    title: 'B2B Quotation & Approval Pipeline',
    description: 'Customer RFQ -> Catalog RAG retrieval -> LLM pricing auditor -> Human email discount approval -> Draft Quotation PDF dispatch.',
    nodeCount: 6,
    nodes: [
      { id: 'n-start', type: 'start', title: 'Start', role: 'RFQ Ingestion', model: '', status: 'idle', borderColor: 'border-emerald-500/80', badgeColor: 'bg-emerald-500/15 text-emerald-400', icon: 'start', x: 20, y: 140 },
      { id: 'n-scout', type: 'researcher', title: 'Catalog Retriever', role: 'RAG Search', model: 'gemini-2.5-flash', status: 'idle', borderColor: 'border-cyan-500/80', badgeColor: 'bg-cyan-500/15 text-cyan-400', icon: 'search', x: 230, y: 60, outputLog: 'Matched Cloud Infotech VoIP Gateways & SIP rate sheets.' },
      { id: 'n-analyst', type: 'analyst', title: 'Pricing Auditor', role: 'Discount Check', model: 'gemini-2.5-flash', status: 'idle', borderColor: 'border-amber-500/80', badgeColor: 'bg-amber-500/15 text-amber-400', icon: 'chart', x: 470, y: 60, outputLog: 'Flagged 25% discount on UC-2000-VE-8T (exceeds 20% limit).' },
      { id: 'n-moderator', type: 'approval', title: 'Human Email Sign-off', role: 'In-Email Gate', model: 'approval-engine', status: 'idle', borderColor: 'border-amber-500/90', badgeColor: 'bg-amber-500/20 text-amber-300', icon: 'mail', x: 710, y: 60, outputLog: 'Dispatched approval email with 1-click tokenized URL.' },
      { id: 'n-polish', type: 'reviewer', title: 'Quotation PDF Generator', role: 'Doc Dispatch', model: 'gemini-2.5-flash', status: 'idle', borderColor: 'border-emerald-500/80', badgeColor: 'bg-emerald-500/15 text-emerald-400', icon: 'check', x: 470, y: 220, outputLog: 'Official commercial Quotation PDF finalized and stored.' },
      { id: 'n-end', type: 'end', title: 'End', role: 'Completed RFQ', model: '', status: 'idle', borderColor: 'border-slate-500/80', badgeColor: 'bg-slate-500/15 text-slate-400', icon: 'stop', x: 710, y: 220 }
    ]
  },
  {
    id: 'tmpl-research-summarize',
    title: 'Research & Summarize',
    description: 'Provide a research question, topic, or list of resources. The Researcher investigates, the Analyst synthesizes, and the Writer formats.',
    nodeCount: 5,
    nodes: [
      { id: 'n-start', type: 'start', title: 'Start', role: 'Topic Brief', model: '', status: 'idle', borderColor: 'border-emerald-500/80', badgeColor: 'bg-emerald-500/15 text-emerald-400', icon: 'start', x: 20, y: 140 },
      { id: 'n-scout', type: 'researcher', title: 'Deep Researcher', role: 'Web & Docs', model: 'gemini-2.5-flash', status: 'idle', borderColor: 'border-cyan-500/80', badgeColor: 'bg-cyan-500/15 text-cyan-400', icon: 'search', x: 230, y: 60, outputLog: 'Retrieved 8 technical whitepapers and release notes.' },
      { id: 'n-analyst', type: 'analyst', title: 'Synthesis Engine', role: 'Data Clustering', model: 'gemini-2.5-flash', status: 'idle', borderColor: 'border-amber-500/80', badgeColor: 'bg-amber-500/15 text-amber-400', icon: 'chart', x: 470, y: 60, outputLog: 'Consolidated architectural pros/cons.' },
      { id: 'n-moderator', type: 'writer', title: 'Executive Summary Drafter', role: 'Executive Brief', model: 'gemini-2.5-flash', status: 'idle', borderColor: 'border-purple-500/80', badgeColor: 'bg-purple-500/15 text-purple-400', icon: 'writer', x: 710, y: 60, outputLog: 'Composed high-level executive memorandum.' },
      { id: 'n-polish', type: 'reviewer', title: 'Fact-Check & Citation', role: 'Reviewer', model: 'gemini-2.5-flash', status: 'idle', borderColor: 'border-emerald-500/80', badgeColor: 'bg-emerald-500/15 text-emerald-400', icon: 'check', x: 470, y: 220, outputLog: 'Verified 100% citation grounding against original documents.' },
      { id: 'n-end', type: 'end', title: 'End', role: 'Termination', model: '', status: 'idle', borderColor: 'border-slate-500/80', badgeColor: 'bg-slate-500/15 text-slate-400', icon: 'stop', x: 710, y: 220 }
    ]
  },
  {
    id: 'tmpl-code-review',
    title: 'Code Review Flow',
    description: 'Describe the feature or paste code. The Coder writes or refactors, the Reviewer audits for bugs, security risks, and regressions.',
    nodeCount: 5,
    nodes: [
      { id: 'n-start', type: 'start', title: 'Start', role: 'PR Webhook', model: '', status: 'idle', borderColor: 'border-emerald-500/80', badgeColor: 'bg-emerald-500/15 text-emerald-400', icon: 'start', x: 20, y: 140 },
      { id: 'n-scout', type: 'researcher', title: 'AST Static Auditor', role: 'Linter & Types', model: 'gemini-2.5-flash', status: 'idle', borderColor: 'border-cyan-500/80', badgeColor: 'bg-cyan-500/15 text-cyan-400', icon: 'search', x: 230, y: 60, outputLog: 'Parsed AST: 0 syntax errors, 2 warning lints.' },
      { id: 'n-analyst', type: 'analyst', title: 'Security Analyzer', role: 'SAST Audit', model: 'gemini-2.5-flash', status: 'idle', borderColor: 'border-amber-500/80', badgeColor: 'bg-amber-500/15 text-amber-400', icon: 'chart', x: 470, y: 60, outputLog: 'Passed SSRF & SQL injection vulnerability scan.' },
      { id: 'n-moderator', type: 'writer', title: 'Patch Generator', role: 'Refactorer', model: 'gemini-2.5-flash', status: 'idle', borderColor: 'border-purple-500/80', badgeColor: 'bg-purple-500/15 text-purple-400', icon: 'writer', x: 710, y: 60, outputLog: 'Prepared unified diff patch for safe review.' },
      { id: 'n-polish', type: 'reviewer', title: 'Test Harness Verifier', role: 'Integration Test', model: 'gemini-2.5-flash', status: 'idle', borderColor: 'border-emerald-500/80', badgeColor: 'bg-emerald-500/15 text-emerald-400', icon: 'check', x: 470, y: 220, outputLog: 'All unit and regression test suites passing (100%).' },
      { id: 'n-end', type: 'end', title: 'End', role: 'Merge Ready', model: '', status: 'idle', borderColor: 'border-slate-500/80', badgeColor: 'bg-slate-500/15 text-slate-400', icon: 'stop', x: 710, y: 220 }
    ]
  },
  {
    id: 'tmpl-ai-roundtable',
    title: 'AI Roundtable (Auto Discovery)',
    description: 'Autonomous multi-agent orchestration for enterprise operations with human oversight.',
    nodeCount: 5,
    isAuto: true,
    nodes: [
      { id: 'n-start', type: 'start', title: 'Start', role: 'Entry Point', model: '', status: 'idle', borderColor: 'border-emerald-500/80', badgeColor: 'bg-emerald-500/15 text-emerald-400', icon: 'start', x: 20, y: 140 },
      { id: 'n-scout', type: 'researcher', title: 'Trend Scout', role: 'Researcher', model: 'gemini-2.5-flash', status: 'idle', borderColor: 'border-cyan-500/80', badgeColor: 'bg-cyan-500/15 text-cyan-400', icon: 'search', x: 230, y: 60, outputLog: 'Analyzed environment state.' },
      { id: 'n-analyst', type: 'analyst', title: 'Impact Analyst', role: 'Analyst', model: 'gemini-2.5-flash', status: 'idle', borderColor: 'border-amber-500/80', badgeColor: 'bg-amber-500/15 text-amber-400', icon: 'chart', x: 470, y: 60, outputLog: 'Computed risk assessment matrix.' },
      { id: 'n-moderator', type: 'writer', title: 'Roundtable Moderator', role: 'Writer', model: 'gemini-2.5-flash', status: 'idle', borderColor: 'border-purple-500/80', badgeColor: 'bg-purple-500/15 text-purple-400', icon: 'writer', x: 710, y: 60, outputLog: 'Produced executive deliverable.' },
      { id: 'n-polish', type: 'reviewer', title: 'Fact-Check & Polish', role: 'Reviewer', model: 'gemini-2.5-flash', status: 'idle', borderColor: 'border-emerald-500/80', badgeColor: 'bg-emerald-500/15 text-emerald-400', icon: 'check', x: 470, y: 220, outputLog: 'Validated with enterprise benchmarks.' },
      { id: 'n-end', type: 'end', title: 'End', role: 'Termination', model: '', status: 'idle', borderColor: 'border-slate-500/80', badgeColor: 'bg-slate-500/15 text-slate-400', icon: 'stop', x: 710, y: 220 }
    ]
  }
];

export default function WorkflowsPage() {
  const [activeTab, setActiveTab] = useState<'templates' | 'agents'>('templates');
  const [searchQuery, setSearchQuery] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [workflowTitle, setWorkflowTitle] = useState('Untitled Workflow');
  const [selectedTemplateId, setSelectedTemplateId] = useState('tmpl-content-review');

  const [nodes, setNodes] = useState<AgentNode[]>(TEMPLATES[0].nodes);
  const [selectedNodeId, setSelectedNodeId] = useState<string>('n-scout');
  const [executionState, setExecutionState] = useState<'idle' | 'running' | 'waiting_approval' | 'completed'>('idle');
  const [activeStepIndex, setActiveStepIndex] = useState<number>(-1);
  const [zoomLevel, setZoomLevel] = useState<number>(100);

  // Email Notification & Approval State
  const [emailModalOpen, setEmailModalOpen] = useState(false);
  const [logsDrawerOpen, setLogsDrawerOpen] = useState(false);
  const [executionLogs, setExecutionLogs] = useState<Array<{ time: string; node: string; message: string; type: 'info' | 'success' | 'warn' | 'approval' }>>([]);
  const [simulatedEmail, setSimulatedEmail] = useState<any>(null);
  const [approvalDecided, setApprovalDecided] = useState<'approved' | 'denied' | null>(null);
  const [isSaved, setIsSaved] = useState(false);
  const [connectedEmail, setConnectedEmail] = useState<string>('approver@aura.internal');

  React.useEffect(() => {
    fetchApi('/integrations/gmail/status')
      .then(async (res: any) => {
        if (res.ok) {
          const json = await res.json();
          if (json.connected_email) setConnectedEmail(json.connected_email);
        }
      })
      .catch(() => {});
  }, []);

  const selectedNode = nodes.find(n => n.id === selectedNodeId) || nodes[0];

  // Switch template
  const handleSelectTemplate = (template: WorkflowTemplate) => {
    setSelectedTemplateId(template.id);
    setWorkflowTitle(template.title);
    setNodes(template.nodes.map(n => ({ ...n, status: 'idle' })));
    setExecutionState('idle');
    setActiveStepIndex(-1);
    setApprovalDecided(null);
    setSimulatedEmail(null);
  };

  // Run the Step-by-Step Agentic Workflow
  const handleRunWorkflow = async () => {
    if (executionState === 'running') return;

    setExecutionState('running');
    setActiveStepIndex(0);
    setApprovalDecided(null);
    setExecutionLogs([
      { time: new Date().toLocaleTimeString(), node: 'Workflow Engine', message: 'Triggered sequential execution of pipeline: ' + workflowTitle, type: 'info' }
    ]);

    // Connect to backend to persist real AgentRun & ApprovalRequest
    try {
      const execRes = await fetchApi('/workflows/execute', {
        method: 'POST',
        body: JSON.stringify({
          workflow_id: selectedTemplateId || 'tmpl-quotation-pipeline',
          input_params: { title: workflowTitle }
        })
      });
      if (execRes.ok) {
        const execData = await execRes.json();
        setExecutionLogs(l => [
          ...l,
          { time: new Date().toLocaleTimeString(), node: 'Workflow Engine', message: `Persistent Execution Record created (Run ID: ${execData.execution_id.slice(0, 8)}...). Trace available in Executions view.`, type: 'info' }
        ]);
      }
    } catch (err) {
      console.warn('Workflow backend execute sync', err);
    }

    // Reset node statuses
    setNodes(prev => prev.map(n => ({ ...n, status: 'idle' })));

    const executeNextStep = (stepIdx: number) => {
      if (stepIdx >= nodes.length) {
        setExecutionState('completed');
        setActiveStepIndex(-1);
        setExecutionLogs(l => [...l, { time: new Date().toLocaleTimeString(), node: 'Workflow Engine', message: '✓ All nodes completed successfully in pipeline.', type: 'success' }]);
        return;
      }

      const targetNode = nodes[stepIdx];
      setActiveStepIndex(stepIdx);

      // Mark this node as running
      setNodes(prev => prev.map((n, idx) => {
        if (idx === stepIdx) return { ...n, status: 'running' };
        if (idx < stepIdx) return { ...n, status: 'completed' };
        return { ...n, status: 'idle' };
      }));

      setExecutionLogs(l => [
        ...l, 
        { time: new Date().toLocaleTimeString(), node: targetNode.title, message: `Node started: executing role [${targetNode.role}]...`, type: 'info' }
      ]);

      // Check if this step is an Approval Gate (e.g. node 3 in quotation pipeline or explicit approval)
      if (targetNode.type === 'approval') {
        setTimeout(() => {
          setExecutionState('waiting_approval');
          setNodes(prev => prev.map((n, idx) => idx === stepIdx ? { ...n, status: 'waiting_approval' } : n));
          
          const mockEmail = {
            id: 'eml-' + Date.now(),
            recipient: connectedEmail,
            subject: `[AURA Action Required] Approval Needed: quotation.create_draft — 25% Commercial Discount`,
            tool_name: 'quotation.create_draft',
            action_summary: 'Commercial Quotation Draft: Cloud Infotech Partner (25% Discount on UC-2000-VE-8T)',
            args: {
              company_name: 'Cloud Infotech Partner',
              model_number: 'UC-2000-VE-8T',
              quantity: 2,
              price_tier: 'MSP (Distributor Price)',
              discount_percent: 25.0,
              total_amount: '₹1,11,732'
            },
            reason: 'Commercial discount of 25.0% exceeds the 20% auto-approval threshold.',
            approve_url: 'http://localhost:8000/api/v1/approvals/email-action?decision=approve',
            deny_url: 'http://localhost:8000/api/v1/approvals/email-action?decision=deny'
          };
          setSimulatedEmail(mockEmail);
          setEmailModalOpen(true);

          setExecutionLogs(l => [
            ...l,
            { 
              time: new Date().toLocaleTimeString(), 
              node: targetNode.title, 
              message: `🚨 Human sign-off required: Dispatched approval email to ${connectedEmail}. Waiting for authorization...`, 
              type: 'approval' 
            }
          ]);
        }, 1200);
        return;
      }

      // Standard node execution timing (1.2s to 1.6s so the user visually sees each step load & complete)
      const duration = targetNode.type === 'start' ? 600 : targetNode.type === 'end' ? 600 : 1400;

      setTimeout(() => {
        setNodes(prev => prev.map((n, idx) => idx === stepIdx ? { ...n, status: 'completed' } : n));
        setExecutionLogs(l => [
          ...l, 
          { 
            time: new Date().toLocaleTimeString(), 
            node: targetNode.title, 
            message: `✓ Completed: ${targetNode.outputLog || 'Task completed successfully.'}`, 
            type: 'success' 
          }
        ]);

        executeNextStep(stepIdx + 1);
      }, duration);
    };

    executeNextStep(0);
  };

  // Handle email decision (direct in-email approval action simulation)
  const handleEmailDecision = async (decision: 'approve' | 'deny') => {
    setApprovalDecided(decision === 'approve' ? 'approved' : 'denied');
    setEmailModalOpen(false);

    if (decision === 'approve') {
      setExecutionLogs(l => [
        ...l,
        { 
          time: new Date().toLocaleTimeString(), 
          node: 'Email Webhook', 
          message: `✓ Received In-Email Approval! Token verified. Resuming AURA execution engine...`, 
          type: 'success' 
        }
      ]);

      // Resume execution to the next node
      const currentStep = activeStepIndex;
      setNodes(prev => prev.map((n, idx) => idx === currentStep ? { ...n, status: 'completed' } : n));
      setExecutionState('running');

      setTimeout(() => {
        // Continue from next step
        const nextStep = currentStep + 1;
        if (nextStep < nodes.length) {
          setActiveStepIndex(nextStep);
          setNodes(prev => prev.map((n, idx) => idx === nextStep ? { ...n, status: 'running' } : n));
          
          setTimeout(() => {
            setNodes(prev => prev.map((n, idx) => idx === nextStep ? { ...n, status: 'completed' } : n));
            // Trigger end node
            if (nextStep + 1 < nodes.length) {
              setNodes(prev => prev.map((n, idx) => idx === nextStep + 1 ? { ...n, status: 'completed' } : n));
            }
            setExecutionState('completed');
            setExecutionLogs(l => [
              ...l,
              { time: new Date().toLocaleTimeString(), node: 'Fact-Check & Polish', message: '✓ Document signed off and dispatched.', type: 'success' },
              { time: new Date().toLocaleTimeString(), node: 'Workflow Engine', message: '✓ Pipeline execution completed in 5.8s.', type: 'success' }
            ]);
          }, 1200);
        }
      }, 800);
    } else {
      setExecutionState('idle');
      setNodes(prev => prev.map((n, idx) => idx === activeStepIndex ? { ...n, status: 'failed' } : n));
      setExecutionLogs(l => [
        ...l,
        { time: new Date().toLocaleTimeString(), node: 'Email Webhook', message: `✕ Task Authorization Denied in email. Execution halted.`, type: 'warn' }
      ]);
    }
  };

  const filteredTemplates = TEMPLATES.filter(t => 
    t.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
    t.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex flex-col h-[calc(100vh-5.5rem)] overflow-hidden bg-background text-foreground -m-6">
      {/* AgentFlow Top Navbar */}
      <header className="h-14 border-b border-border bg-card/80 backdrop-blur-md px-4 flex items-center justify-between shrink-0 z-20">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-primary font-bold text-sm">
            <Sparkles className="w-4 h-4 text-primary animate-pulse" />
            <span className="tracking-tight text-foreground">AgentFlow</span>
          </div>
          <span className="text-border">/</span>
          <div className="flex items-center gap-2">
            <input 
              type="text" 
              value={workflowTitle}
              onChange={(e) => setWorkflowTitle(e.target.value)}
              className="bg-transparent text-xs font-semibold text-foreground focus:outline-none focus:ring-1 focus:ring-primary/40 rounded px-1.5 py-0.5"
            />
            {executionState === 'idle' && (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-muted text-muted-foreground border border-border">
                Ready
              </span>
            )}
            {executionState === 'running' && (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5 animate-pulse">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                Running Step {activeStepIndex + 1}/{nodes.length}
              </span>
            )}
            {executionState === 'waiting_approval' && (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/20 text-amber-400 border border-amber-500/40 flex items-center gap-1.5 animate-pulse">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                Waiting Email Approval
              </span>
            )}
            {executionState === 'completed' && (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 flex items-center gap-1.5">
                <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                Completed
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          {/* Big Green Run Button matching Pic 2 */}
          <button
            type="button"
            onClick={handleRunWorkflow}
            disabled={executionState === 'running'}
            className={cn(
              "inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold text-white shadow-md transition-all",
              executionState === 'running' 
                ? "bg-emerald-600/70 cursor-not-allowed opacity-80" 
                : "bg-emerald-500 hover:bg-emerald-600 active:scale-95 shadow-emerald-500/25"
            )}
          >
            <Play className={cn("w-3.5 h-3.5 fill-current", executionState === 'running' && "animate-spin")} />
            <span>{executionState === 'running' ? 'Running Pipeline...' : 'Run'}</span>
          </button>

          {/* Email Preview & Simulation Button */}
          <button
            type="button"
            onClick={() => setEmailModalOpen(true)}
            className="relative inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-border bg-card hover:bg-muted text-xs font-medium text-foreground transition"
            title="Inspect or simulate In-Email Approval"
          >
            <Mail className="w-3.5 h-3.5 text-muted-foreground" />
            <span>Email Sign-off</span>
            {executionState === 'waiting_approval' && (
              <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-amber-500 rounded-full animate-ping" />
            )}
          </button>

          {/* Log Drawer Button */}
          <button
            type="button"
            onClick={() => setLogsDrawerOpen(!logsDrawerOpen)}
            className={cn(
              "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-medium transition",
              logsDrawerOpen ? "bg-primary/15 text-primary border-primary/30" : "bg-card border-border hover:bg-muted text-foreground"
            )}
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>Log</span>
          </button>

          {/* Save Button */}
          <button
            type="button"
            onClick={() => {
              setIsSaved(true);
              setTimeout(() => setIsSaved(false), 2000);
            }}
            className="p-2 rounded-xl border border-border bg-card hover:bg-muted text-foreground transition"
            title="Save Workflow"
          >
            {isSaved ? <Check className="w-4 h-4 text-emerald-400" /> : <Save className="w-4 h-4 text-muted-foreground" />}
          </button>

          {/* More options */}
          <button
            type="button"
            className="p-2 rounded-xl border border-border bg-card hover:bg-muted text-foreground transition"
          >
            <MoreVertical className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>
      </header>

      {/* Main Workspace: Left Sidebar + Canvas */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Left Sidebar (Agents & Templates) */}
        <aside 
          className={cn(
            "border-r border-border bg-card flex flex-col shrink-0 transition-all duration-300 z-10",
            sidebarOpen ? "w-72" : "w-12"
          )}
        >
          {sidebarOpen ? (
            <>
              {/* Sidebar Header with Collapse */}
              <div className="p-3.5 border-b border-border flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="p-1 rounded bg-primary/10 text-primary">
                    <Sparkles className="w-4 h-4" />
                  </div>
                  <span className="text-xs font-bold text-foreground">AgentFlow</span>
                </div>
                <button
                  type="button"
                  onClick={() => setSidebarOpen(false)}
                  className="p-1 rounded-md text-muted-foreground hover:bg-muted transition"
                  title="Collapse Sidebar"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
              </div>

              {/* Search Bar */}
              <div className="p-3 border-b border-border">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <input
                    type="text"
                    placeholder="Search agents or templates..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-8 pr-3 py-1.5 text-xs bg-muted/50 border border-border rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/40"
                  />
                </div>
              </div>

              {/* Tabs: Agents | Templates */}
              <div className="flex border-b border-border bg-muted/20">
                <button
                  type="button"
                  onClick={() => setActiveTab('agents')}
                  className={cn(
                    "flex-1 py-2 text-xs font-semibold text-center border-b-2 transition",
                    activeTab === 'agents' 
                      ? "border-primary text-foreground" 
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  )}
                >
                  Agents
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('templates')}
                  className={cn(
                    "flex-1 py-2 text-xs font-semibold text-center border-b-2 transition",
                    activeTab === 'templates' 
                      ? "border-primary text-foreground" 
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  )}
                >
                  Templates
                </button>
              </div>

              {/* Content List */}
              <div className="flex-1 overflow-y-auto p-3 space-y-3">
                {activeTab === 'templates' ? (
                  filteredTemplates.map((template) => {
                    const isSelected = template.id === selectedTemplateId;
                    return (
                      <div
                        key={template.id}
                        className={cn(
                          "p-3 rounded-2xl border transition-all text-left bg-card/60",
                          isSelected 
                            ? "border-primary/60 bg-primary/5 shadow-xs" 
                            : "border-border hover:border-primary/30"
                        )}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <h4 className="text-xs font-bold text-foreground truncate">{template.title}</h4>
                          {template.isAuto && (
                            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-primary/20 text-primary uppercase font-mono">
                              Auto
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-muted-foreground leading-relaxed line-clamp-2 mb-2.5">
                          {template.description}
                        </p>
                        <div className="flex items-center justify-between pt-1">
                          <span className="text-[10px] text-muted-foreground font-mono">
                            {template.nodeCount} nodes
                          </span>
                          <button
                            type="button"
                            onClick={() => handleSelectTemplate(template)}
                            className="px-2.5 py-1 rounded-lg border border-border bg-card hover:bg-primary hover:text-primary-foreground text-[11px] font-semibold text-foreground transition shadow-2xs"
                          >
                            Use Template
                          </button>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  /* Agents Tab - Draggable/Addable components */
                  <div className="space-y-2">
                    <p className="text-[10px] text-muted-foreground uppercase font-mono px-1">Available Agents</p>
                    {[
                      { title: 'Trend Scout', role: 'Researcher', model: 'gemini-2.5-flash', icon: Search, color: 'text-cyan-400' },
                      { title: 'Impact Analyst', role: 'Analyst', model: 'gemini-2.5-flash', icon: BarChart3, color: 'text-amber-400' },
                      { title: 'Roundtable Moderator', role: 'Writer', model: 'gemini-2.5-flash', icon: PenTool, color: 'text-purple-400' },
                      { title: 'Human Email Approval Gate', role: 'In-Email Sign-off', model: 'approval-engine', icon: Mail, color: 'text-amber-300' },
                      { title: 'Fact-Check & Polish', role: 'Reviewer', model: 'gemini-2.5-flash', icon: CheckCircle2, color: 'text-emerald-400' },
                      { title: 'Catalog RAG Engine', role: 'Hardware Rate Cards', model: 'hybrid-search', icon: Database, color: 'text-blue-400' },
                    ].map((agent, i) => {
                      const IconComp = agent.icon;
                      return (
                        <div 
                          key={i}
                          onClick={() => {
                            setExecutionLogs(l => [...l, { time: new Date().toLocaleTimeString(), node: agent.title, message: `Selected ${agent.title} (${agent.role})`, type: 'info' }]);
                          }}
                          className="p-2.5 rounded-xl border border-border bg-card/60 hover:border-primary/40 cursor-pointer transition flex items-center justify-between"
                        >
                          <div className="flex items-center gap-2.5">
                            <div className={cn("p-1.5 rounded-lg bg-muted", agent.color)}>
                              <IconComp className="w-3.5 h-3.5" />
                            </div>
                            <div>
                              <h5 className="text-xs font-semibold text-foreground">{agent.title}</h5>
                              <p className="text-[10px] text-muted-foreground">{agent.role}</p>
                            </div>
                          </div>
                          <span className="text-[9px] font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                            {agent.model}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </>
          ) : (
            /* Collapsed Sidebar */
            <div className="py-3 flex flex-col items-center gap-3">
              <button
                type="button"
                onClick={() => setSidebarOpen(true)}
                className="p-1.5 rounded-lg text-muted-foreground hover:bg-muted transition"
                title="Expand Sidebar"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </aside>

        {/* Canvas Area */}
        <div className="flex-1 bg-background relative overflow-hidden flex flex-col">
          {/* Subtle Canvas Dot Grid Pattern */}
          <div 
            className="absolute inset-0 pointer-events-none opacity-30" 
            style={{
              backgroundImage: 'radial-gradient(circle, var(--border) 1px, transparent 1px)',
              backgroundSize: '24px 24px'
            }}
          />

          {/* Banner notification when waiting for email approval */}
          {executionState === 'waiting_approval' && (
            <div className="relative z-20 mx-6 mt-4 p-3 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-between animate-fade-in shadow-md">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-amber-500/20 text-amber-400">
                  <Mail className="w-4 h-4 animate-bounce" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-foreground">Human Email Authorization Gate Triggered</h4>
                  <p className="text-[11px] text-muted-foreground">
                    Notification dispatched to <span className="font-mono text-amber-400">{connectedEmail}</span>. The recipient can approve directly inside their email client, or you can authorize here.
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setEmailModalOpen(true)}
                  className="px-3 py-1.5 rounded-xl bg-amber-500 text-slate-950 font-bold text-xs hover:bg-amber-400 transition"
                >
                  Review In-Email Action
                </button>
              </div>
            </div>
          )}

          {/* SVG Connection Layer & Node Canvas */}
          <div className="flex-1 relative overflow-auto p-8" style={{ transform: `scale(${zoomLevel / 100})`, transformOrigin: 'top left' }}>
            <svg className="absolute inset-0 w-[1200px] h-[600px] pointer-events-none z-0">
              <defs>
                <linearGradient id="gradient-flow" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#10b981" />
                  <stop offset="50%" stopColor="#06b6d4" />
                  <stop offset="100%" stopColor="#a855f7" />
                </linearGradient>
              </defs>

              {/* Path 1: Start (20,140) to Trend Scout (230,60) */}
              <path
                d="M 160 160 C 190 160, 200 95, 230 95"
                fill="none"
                stroke={activeStepIndex >= 0 ? '#10b981' : '#334155'}
                strokeWidth="2"
                strokeDasharray={activeStepIndex === 0 ? '6,6' : 'none'}
                className={activeStepIndex === 0 ? 'animate-pulse' : ''}
              />

              {/* Path 2: Trend Scout (230,60) to Impact Analyst (470,60) */}
              <path
                d="M 390 95 C 420 95, 440 95, 470 95"
                fill="none"
                stroke={activeStepIndex >= 1 ? '#06b6d4' : '#334155'}
                strokeWidth="2"
                strokeDasharray={activeStepIndex === 1 ? '6,6' : 'none'}
                className={activeStepIndex === 1 ? 'animate-pulse' : ''}
              />

              {/* Path 3: Impact Analyst (470,60) to Roundtable Moderator (710,60) */}
              <path
                d="M 630 95 C 660 95, 680 95, 710 95"
                fill="none"
                stroke={activeStepIndex >= 2 ? '#f59e0b' : '#334155'}
                strokeWidth="2"
                strokeDasharray={activeStepIndex === 2 ? '6,6' : 'none'}
                className={activeStepIndex === 2 ? 'animate-pulse' : ''}
              />

              {/* Path 4: Roundtable Moderator (710,60) curving down to Fact-Check & Polish (470,220) */}
              <path
                d="M 870 95 C 930 95, 410 255, 470 255"
                fill="none"
                stroke={activeStepIndex >= 3 ? '#a855f7' : '#334155'}
                strokeWidth="2"
                strokeDasharray={activeStepIndex === 3 ? '6,6' : 'none'}
                className={activeStepIndex === 3 ? 'animate-pulse' : ''}
              />

              {/* Path 5: Fact-Check & Polish (470,220) to End (710,220) */}
              <path
                d="M 630 255 C 660 255, 680 255, 710 255"
                fill="none"
                stroke={activeStepIndex >= 4 ? '#10b981' : '#334155'}
                strokeWidth="2"
                strokeDasharray={activeStepIndex === 4 ? '6,6' : 'none'}
                className={activeStepIndex === 4 ? 'animate-pulse' : ''}
              />
            </svg>

            {/* Render Nodes (Matching exact layout and card proportions from Pic 2) */}
            <div className="relative z-10 w-[1100px] h-[500px]">
              {nodes.map((node) => {
                const isSelected = node.id === selectedNodeId;
                const isExecuting = node.status === 'running';
                const isWaiting = node.status === 'waiting_approval';
                const isCompleted = node.status === 'completed';

                return (
                  <div
                    key={node.id}
                    onClick={() => setSelectedNodeId(node.id)}
                    style={{ left: `${node.x}px`, top: `${node.y}px` }}
                    className={cn(
                      "absolute w-[200px] p-3.5 rounded-2xl border bg-card/95 backdrop-blur-md transition-all cursor-pointer shadow-md select-none",
                      isSelected && "ring-2 ring-primary/40",
                      isExecuting && "border-primary ring-4 ring-primary/20 scale-105 shadow-lg",
                      isWaiting && "border-amber-500 ring-4 ring-amber-500/30 scale-105 animate-pulse",
                      isCompleted && "border-emerald-500/60 bg-emerald-500/5",
                      !isExecuting && !isWaiting && !isCompleted && node.borderColor
                    )}
                  >
                    {/* Left & Right Connection Ports */}
                    {node.type !== 'start' && (
                      <span className="w-2.5 h-2.5 rounded-full bg-slate-400 border-2 border-background absolute -left-1.5 top-1/2 -translate-y-1/2" />
                    )}
                    {node.type !== 'end' && (
                      <span className="w-2.5 h-2.5 rounded-full bg-slate-400 border-2 border-background absolute -right-1.5 top-1/2 -translate-y-1/2" />
                    )}

                    {/* Top Row: Icon + Title + Subtitle */}
                    <div className="flex items-start gap-2.5 mb-2">
                      <div className="p-1 rounded-lg bg-muted shrink-0 text-foreground">
                        {node.type === 'start' && <Play className="w-4 h-4 text-emerald-400" />}
                        {node.type === 'researcher' && <Search className="w-4 h-4 text-cyan-400" />}
                        {node.type === 'analyst' && <BarChart3 className="w-4 h-4 text-amber-400" />}
                        {node.type === 'writer' && <PenTool className="w-4 h-4 text-purple-400" />}
                        {node.type === 'approval' && <Mail className="w-4 h-4 text-amber-300" />}
                        {node.type === 'reviewer' && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
                        {node.type === 'end' && <Square className="w-4 h-4 text-slate-400" />}
                      </div>
                      <div className="min-w-0">
                        <h4 className="text-xs font-bold text-foreground truncate">{node.title}</h4>
                        <p className="text-[10px] text-muted-foreground truncate">{node.role}</p>
                      </div>
                    </div>

                    {/* Bottom Row: Model Badge + Status Indicator */}
                    {node.type !== 'start' && node.type !== 'end' && (
                      <div className="pt-2 border-t border-border/60 flex items-center justify-between text-[10px]">
                        <span className="font-mono text-muted-foreground flex items-center gap-1">
                          ⚡ {node.model}
                        </span>
                        <div>
                          {isExecuting && (
                            <span className="text-primary font-semibold flex items-center gap-1">
                              <span className="w-1.5 h-1.5 rounded-full bg-primary animate-ping" />
                              Running
                            </span>
                          )}
                          {isWaiting && (
                            <span className="text-amber-400 font-semibold flex items-center gap-1">
                              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" />
                              Awaiting
                            </span>
                          )}
                          {isCompleted && (
                            <span className="text-emerald-400 font-semibold flex items-center gap-1">
                              ✓ Done
                            </span>
                          )}
                          {node.status === 'idle' && (
                            <span className="text-muted-foreground flex items-center gap-1">
                              ● Idle
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Minimap (Bottom Right) matching Pic 2 */}
          <div className="absolute right-6 bottom-6 w-36 h-24 rounded-xl border border-border bg-card/90 backdrop-blur-md p-2 shadow-lg hidden sm:block pointer-events-none">
            <span className="text-[8px] font-mono text-muted-foreground uppercase">DAG Minimap</span>
            <div className="relative w-full h-14 mt-1 bg-muted/40 rounded-lg overflow-hidden border border-border/50">
              {nodes.map(n => (
                <div
                  key={n.id}
                  style={{
                    left: `${(n.x / 850) * 85}%`,
                    top: `${(n.y / 300) * 70}%`,
                    width: '18px',
                    height: '10px'
                  }}
                  className={cn(
                    "absolute rounded-xs opacity-85",
                    n.type === 'start' && "bg-emerald-500",
                    n.type === 'researcher' && "bg-cyan-500",
                    n.type === 'analyst' && "bg-amber-500",
                    n.type === 'writer' && "bg-purple-500",
                    n.type === 'approval' && "bg-amber-400",
                    n.type === 'reviewer' && "bg-emerald-500",
                    n.type === 'end' && "bg-slate-500"
                  )}
                />
              ))}
            </div>
          </div>

          {/* Zoom Controls (Bottom Left) matching Pic 2 */}
          <div className="absolute left-6 bottom-6 flex items-center gap-1 rounded-xl border border-border bg-card/90 backdrop-blur-md p-1 shadow-lg">
            <button
              type="button"
              onClick={() => setZoomLevel(prev => Math.min(prev + 10, 150))}
              className="p-1.5 rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition"
              title="Zoom In"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
            <span className="text-[10px] font-mono px-1.5 text-muted-foreground">{zoomLevel}%</span>
            <button
              type="button"
              onClick={() => setZoomLevel(prev => Math.max(prev - 10, 60))}
              className="p-1.5 rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition"
              title="Zoom Out"
            >
              <Minus className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setZoomLevel(100)}
              className="p-1.5 rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition"
              title="Reset Zoom"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Active Node Info Pill */}
          <div className="absolute left-36 bottom-6 hidden md:flex items-center gap-2 px-3 py-1.5 rounded-xl border border-border bg-card/90 backdrop-blur-md text-[11px] text-muted-foreground shadow-lg">
            <span className="font-semibold text-foreground">{selectedNode.title}</span>
            <span className="font-mono text-[10px]">({selectedNode.role})</span>
            {approvalDecided && (
              <span className="text-emerald-400 font-bold ml-1">• In-Email Status: {approvalDecided.toUpperCase()}</span>
            )}
          </div>
        </div>
      </div>

      {/* Slide-over Log Drawer */}
      {logsDrawerOpen && (
        <div className="fixed inset-y-0 right-0 w-80 bg-card border-l border-border shadow-2xl z-40 flex flex-col p-4 animate-in slide-in-from-right duration-200">
          <div className="flex items-center justify-between pb-3 border-b border-border">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-primary" />
              <h3 className="text-xs font-bold text-foreground">Pipeline Execution Logs</h3>
            </div>
            <button
              type="button"
              onClick={() => setLogsDrawerOpen(false)}
              className="p-1 rounded-lg text-muted-foreground hover:bg-muted transition"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto py-3 space-y-2.5 font-mono text-[11px]">
            {executionLogs.length === 0 ? (
              <p className="text-muted-foreground text-center py-8">No execution events recorded yet. Click &apos;Run&apos; to trigger pipeline.</p>
            ) : (
              executionLogs.map((log, i) => (
                <div 
                  key={i} 
                  className={cn(
                    "p-2.5 rounded-xl border",
                    log.type === 'success' && "bg-emerald-500/10 border-emerald-500/25 text-emerald-300",
                    log.type === 'approval' && "bg-amber-500/10 border-amber-500/30 text-amber-300",
                    log.type === 'warn' && "bg-red-500/10 border-red-500/25 text-red-300",
                    log.type === 'info' && "bg-muted/40 border-border text-muted-foreground"
                  )}
                >
                  <div className="flex items-center justify-between text-[10px] opacity-75 mb-1">
                    <span>{log.node}</span>
                    <span>{log.time}</span>
                  </div>
                  <p className="leading-relaxed">{log.message}</p>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* In-Email Approval Dialog / Simulation Modal */}
      {emailModalOpen && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="bg-card border border-border rounded-2xl max-w-lg w-full shadow-2xl overflow-hidden flex flex-col">
            {/* Email Header */}
            <div className="bg-primary/10 border-b border-border p-4 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-primary/20 text-primary">
                  <Mail className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-foreground">In-Email Human Approval</h3>
                  <p className="text-[10px] text-muted-foreground">Notification sent to {simulatedEmail?.recipient || connectedEmail}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setEmailModalOpen(false)}
                className="p-1 rounded-lg text-muted-foreground hover:bg-muted"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Email Body Simulation */}
            <div className="p-5 space-y-4 text-xs">
              <div className="p-3 rounded-xl bg-muted/40 border border-border">
                <span className="text-[10px] font-bold uppercase text-muted-foreground font-mono">Subject</span>
                <p className="font-semibold text-foreground mt-0.5">
                  {simulatedEmail?.subject || '[AURA Action Required] Approval Needed: quotation.create_draft — 25% Commercial Discount'}
                </p>
              </div>

              <div>
                <span className="text-[10px] font-bold uppercase text-muted-foreground font-mono">Task Details</span>
                <div className="mt-1.5 p-3 rounded-xl bg-card border border-border space-y-1.5 text-[11px]">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Company:</span>
                    <span className="font-semibold text-foreground">Cloud Infotech Partner</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Model:</span>
                    <span className="font-mono text-foreground">UC-2000-VE-8T (8 Port GSM Gateway)</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Discount Requested:</span>
                    <span className="font-mono font-bold text-amber-400">25.0% (Exceeds 20% auto-limit)</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Authorized Total:</span>
                    <span className="font-bold text-foreground">₹1,11,732 (excl. 18% GST)</span>
                  </div>
                </div>
              </div>

              <p className="text-[11px] text-muted-foreground leading-relaxed">
                The client receives this email with tokenized buttons. Clicking <strong>Approve this Task</strong> directly inside their email client routes back into AURA, marks the approval as approved, and resumes the agent to finalize the quotation.
              </p>

              {/* In-Email Action Buttons */}
              <div className="pt-2 border-t border-border flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => handleEmailDecision('deny')}
                  className="px-4 py-2 rounded-xl border border-destructive/40 bg-destructive/10 text-destructive text-xs font-semibold hover:bg-destructive/20 transition"
                >
                  ✕ Deny Task
                </button>
                <button
                  type="button"
                  onClick={() => handleEmailDecision('approve')}
                  className="px-4 py-2 rounded-xl bg-emerald-500 text-white text-xs font-bold hover:bg-emerald-600 transition shadow-xs flex items-center gap-1.5"
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>Approve this Task</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
