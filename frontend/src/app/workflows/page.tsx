'use client';
import { useState } from 'react';
import { 
  GitFork, 
  Play, 
  Plus, 
  Save, 
  CheckCircle2, 
  Settings, 
  FileCode, 
  Cpu, 
  Database, 
  ShieldAlert, 
  ArrowRight,
  Layers,
  Sparkles,
  Sliders
} from 'lucide-react';

interface WorkflowNode {
  id: string;
  type: 'trigger' | 'rag' | 'llm' | 'tool' | 'approval' | 'output';
  title: string;
  subtitle: string;
  config: Record<string, any>;
  x: number;
  y: number;
}

const INITIAL_NODES: WorkflowNode[] = [
  {
    id: 'node-1',
    type: 'trigger',
    title: 'Customer Quotation Request',
    subtitle: 'Event: Sales message received',
    config: { channel: 'chat_or_api' },
    x: 40,
    y: 80,
  },
  {
    id: 'node-2',
    type: 'rag',
    title: 'Cloud Infotech Catalog Retrieval',
    subtitle: 'Dense + BM25 Hybrid (Top 5)',
    config: { index: 'kb-cloud-infotech', threshold: 0.72 },
    x: 280,
    y: 80,
  },
  {
    id: 'node-3',
    type: 'llm',
    title: 'Hardware & Margin Matching',
    subtitle: 'Model: gemini-2.5-flash',
    config: { provider: 'google', temperature: 0.1 },
    x: 520,
    y: 80,
  },
  {
    id: 'node-4',
    type: 'approval',
    title: 'Manager Discount Sign-Off',
    subtitle: 'Condition: If Discount > 20%',
    config: { role: 'operations_director', timeout_hours: 24 },
    x: 760,
    y: 80,
  },
  {
    id: 'node-5',
    type: 'tool',
    title: 'Create Quotation & PDF',
    subtitle: 'Tool: quotation.create_draft',
    config: { persist: true },
    x: 1000,
    y: 80,
  },
];

export default function WorkflowsPage() {
  const [nodes, setNodes] = useState<WorkflowNode[]>(INITIAL_NODES);
  const [selectedNodeId, setSelectedNodeId] = useState<string>('node-2');
  const [isSaved, setIsSaved] = useState(false);
  const [executionState, setExecutionState] = useState<'idle' | 'running' | 'success'>('idle');

  const selectedNode = nodes.find((n) => n.id === selectedNodeId) || nodes[0];

  const handleTestRun = () => {
    setExecutionState('running');
    setTimeout(() => {
      setExecutionState('success');
      setTimeout(() => setExecutionState('idle'), 3500);
    }, 1800);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold text-slate-900 tracking-tight">Enterprise Workflow Studio</h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
              LangGraph / Dify Architecture
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Design deterministic, multi-step agent pipelines with human approval checkpoints and tool fallbacks.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => {
              setIsSaved(true);
              setTimeout(() => setIsSaved(false), 2000);
            }}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-700 text-xs font-semibold hover:bg-slate-50 transition shadow-xs"
          >
            {isSaved ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <Save className="h-4 w-4" />}
            {isSaved ? 'Workflow Saved' : 'Save Workflow'}
          </button>
          <button
            onClick={handleTestRun}
            disabled={executionState === 'running'}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 transition shadow-xs disabled:opacity-50"
          >
            <Play className="h-4 w-4" />
            {executionState === 'running' ? 'Simulating Pipeline...' : 'Test Execution'}
          </button>
        </div>
      </div>

      {/* Main Studio View: Canvas + Node Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Visual Node Flowchart */}
        <div className="lg:col-span-2 bg-slate-50/70 rounded-2xl border border-slate-200 p-6 min-h-[500px] flex flex-col justify-between relative overflow-hidden">
          {/* Canvas Background Grid Pattern */}
          <div className="absolute inset-0 bg-[radial-gradient(#cbd5e1_1px,transparent_1px)] [background-size:16px_16px] opacity-40 pointer-events-none" />

          {/* Workflow Title & Status Bar */}
          <div className="relative z-10 flex items-center justify-between pb-4 border-b border-slate-200/60">
            <span className="text-xs font-bold text-slate-800">Pipeline: B2B Hardware Quotation & Invoice</span>
            <span className="text-[11px] text-emerald-600 font-medium flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" /> Validated Graph
            </span>
          </div>

          {/* Flow Nodes Display */}
          <div className="relative z-10 space-y-4 my-auto py-6">
            <div className="flex flex-col md:flex-row items-center justify-between gap-3 overflow-x-auto pb-4">
              {nodes.map((node, idx) => {
                const isSelected = node.id === selectedNodeId;
                const isRunning = executionState === 'running';
                return (
                  <div key={node.id} className="flex items-center gap-3">
                    <div
                      onClick={() => setSelectedNodeId(node.id)}
                      className={`w-44 p-3.5 rounded-xl border transition-all cursor-pointer bg-white shadow-xs ${
                        isSelected
                          ? 'border-blue-600 ring-2 ring-blue-500/20'
                          : 'border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <span className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${
                          node.type === 'trigger' ? 'bg-purple-50 text-purple-700' :
                          node.type === 'rag' ? 'bg-emerald-50 text-emerald-700' :
                          node.type === 'llm' ? 'bg-blue-50 text-blue-700' :
                          node.type === 'approval' ? 'bg-amber-50 text-amber-700' :
                          'bg-indigo-50 text-indigo-700'
                        }`}>
                          {node.type}
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono">0{idx + 1}</span>
                      </div>
                      <h4 className="text-xs font-bold text-slate-900 leading-tight">{node.title}</h4>
                      <p className="text-[10px] text-slate-500 mt-1 truncate">{node.subtitle}</p>
                    </div>

                    {idx < nodes.length - 1 && (
                      <ArrowRight className="h-4 w-4 text-slate-400 hidden md:block shrink-0" />
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Canvas Bottom Action Bar */}
          <div className="relative z-10 flex items-center justify-between pt-4 border-t border-slate-200/60 text-xs text-slate-500">
            <span>5 Nodes Active • Linear Directed Graph</span>
            <button
              onClick={() => {
                const newNode: WorkflowNode = {
                  id: `node-${nodes.length + 1}`,
                  type: 'llm',
                  title: 'Post-Process Summarizer',
                  subtitle: 'Format email response',
                  config: {},
                  x: 0,
                  y: 0,
                };
                setNodes([...nodes, newNode]);
              }}
              className="inline-flex items-center gap-1 font-semibold text-blue-600 hover:underline"
            >
              <Plus className="h-3.5 w-3.5" /> Add Pipeline Node
            </button>
          </div>
        </div>

        {/* Right 1 Col: Node Configuration Panel */}
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs space-y-5">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Selected Node
              </span>
              <h3 className="text-sm font-bold text-slate-900">{selectedNode.title}</h3>
            </div>
            <span className="text-xs font-mono text-slate-400">{selectedNode.id}</span>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Node Title</label>
              <input
                type="text"
                value={selectedNode.title}
                onChange={(e) => {
                  setNodes(nodes.map(n => n.id === selectedNode.id ? { ...n, title: e.target.value } : n));
                }}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Description / Subtitle</label>
              <input
                type="text"
                value={selectedNode.subtitle}
                onChange={(e) => {
                  setNodes(nodes.map(n => n.id === selectedNode.id ? { ...n, subtitle: e.target.value } : n));
                }}
                className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            {selectedNode.type === 'rag' && (
              <div className="space-y-3 p-3 bg-slate-50 rounded-lg">
                <span className="text-xs font-bold text-slate-800 block">RAG Retrieval Settings</span>
                <div>
                  <label className="block text-[11px] text-slate-600 mb-1">Knowledge Source</label>
                  <select className="w-full text-xs rounded border border-slate-200 bg-white p-1.5">
                    <option>Cloud Infotech Hardware Catalog (pgvector)</option>
                    <option>Corporate Discount Matrix</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] text-slate-600 mb-1">Reranking Algorithm</label>
                  <select className="w-full text-xs rounded border border-slate-200 bg-white p-1.5">
                    <option>Reciprocal Rank Fusion (RRF k=60)</option>
                    <option>Dense Cosine Similarity Only</option>
                  </select>
                </div>
              </div>
            )}

            {selectedNode.type === 'approval' && (
              <div className="space-y-3 p-3 bg-amber-50/70 border border-amber-200/70 rounded-lg">
                <span className="text-xs font-bold text-amber-900 block">Approval Governance Gate</span>
                <p className="text-[11px] text-amber-800">
                  When reached, workflow halts execution state and posts an interactive review ticket to the Approvals inbox.
                </p>
                <div>
                  <label className="block text-[11px] text-amber-900 font-semibold mb-1">Authorized Approver Role</label>
                  <select className="w-full text-xs rounded border border-amber-300 bg-white p-1.5 text-slate-800">
                    <option>Operations Director or Finance Manager</option>
                    <option>Tenant Administrator Only</option>
                  </select>
                </div>
              </div>
            )}

            {selectedNode.type === 'tool' && (
              <div className="space-y-3 p-3 bg-slate-50 rounded-lg">
                <span className="text-xs font-bold text-slate-800 block">Tool Binding</span>
                <div>
                  <label className="block text-[11px] text-slate-600 mb-1">Tool Target</label>
                  <select className="w-full text-xs rounded border border-slate-200 bg-white p-1.5">
                    <option>quotation.create_draft</option>
                    <option>invoice.generate</option>
                    <option>customer.search</option>
                  </select>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
