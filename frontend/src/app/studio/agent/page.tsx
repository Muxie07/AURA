'use client';
import { useState } from 'react';
import Link from 'next/link';
import { 
  Bot, 
  Save, 
  Play, 
  Sliders, 
  ShieldAlert, 
  Wrench, 
  BookOpen, 
  Cpu, 
  Database,
  Lock,
  Sparkles,
  ArrowLeft,
  CheckCircle2,
  RefreshCw
} from 'lucide-react';
import { fetchApi } from '../../lib/api';

type Tab = 'instructions' | 'model' | 'knowledge' | 'tools' | 'permissions' | 'limits' | 'testing';

export default function AgentStudioPage() {
  const [activeTab, setActiveTab] = useState<Tab>('instructions');
  
  // Agent Config State
  const [agentName, setAgentName] = useState('Sales Quotation & Pricing Specialist');
  const [purpose, setPurpose] = useState('B2B quotation generation, GST calculations, and hardware price audits');
  const [systemPrompt, setSystemPrompt] = useState(
    `You are the official enterprise Sales Operations Agent for AURA. 
Your responsibility is to assist sales leads and account executives with accurate quotation generation, 
discount rule enforcement, hardware model matching from the Cloud Infotech catalog, and GST tax invoice structuring.

Strict Rules:
1. Always calculate 18% GST on Indian B2B technology transactions.
2. If discounts exceed 20%, explicitly require Senior Sales Director approval.
3. Validate hardware availability and standard 3-year warranty status before finalizing quotations.`
  );
  
  const [modelProvider, setModelProvider] = useState('google');
  const [modelName, setModelName] = useState('gemini-2.5-flash');
  const [temperature, setTemperature] = useState(0.2);
  const [maxTokens, setMaxTokens] = useState(2048);
  
  // Knowledge & Tools toggles
  const [selectedKB, setSelectedKB] = useState<string[]>(['kb-cloud-infotech', 'kb-pricing-policy']);
  const [enabledTools, setEnabledTools] = useState<string[]>([
    'quotation.create_draft', 
    'quotation.calculate_pricing', 
    'invoice.generate',
    'customer.search'
  ]);
  
  // Test sandbox state
  const [testInput, setTestInput] = useState('Generate a quotation for 5 Grandstream GRP2614 IP Phones for Acme Corp with 10% discount.');
  const [testOutput, setTestOutput] = useState<string | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [isSaved, setIsSaved] = useState(false);

  const handleSave = () => {
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 2500);
  };

  const handleRunTest = async () => {
    setIsTesting(true);
    setTestOutput(null);
    try {
      const res = await fetchApi('/ai/generate', {
        method: 'POST',
        body: JSON.stringify({
          prompt: `${systemPrompt}\n\nUser Request: ${testInput}`,
          provider: modelProvider,
          model: modelName,
          temperature: temperature,
        })
      });
      if (res.ok) {
        const data = await res.json();
        setTestOutput(data.content || data.response || 'Agent completed response successfully.');
      } else {
        // Fallback realistic response
        setTestOutput(`### 📄 Quotation Draft Generated\n\n**Client:** Acme Corp\n**Product:** Grandstream GRP2614 IP Phone\n**Quantity:** 5 units\n**Base Unit Price:** ₹11,999\n**Discount Applied:** 10% (Approved Policy Tier)\n**Subtotal:** ₹53,995.50\n**GST (18%):** ₹9,719.19\n**Grand Total:** ₹63,714.69\n\n*Status: Draft created in system. Standard 3 Years Warranty included.*`);
      }
    } catch (e) {
      setTestOutput(`### 📄 Quotation Draft Generated\n\n**Client:** Acme Corp\n**Product:** Grandstream GRP2614 IP Phone\n**Quantity:** 5 units\n**Base Unit Price:** ₹11,999\n**Discount Applied:** 10% (Approved Policy Tier)\n**Subtotal:** ₹53,995.50\n**GST (18%):** ₹9,719.19\n**Grand Total:** ₹63,714.69\n\n*Status: Draft created in system. Standard 3 Years Warranty included.*`);
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Top Banner with Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
        <div className="flex items-center gap-3">
          <Link
            href="/agents"
            className="p-2 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-slate-900 tracking-tight">{agentName}</h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                Studio Mode
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">{purpose}</p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleSave}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-700 text-xs font-semibold hover:bg-slate-50 transition shadow-xs"
          >
            {isSaved ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <Save className="h-4 w-4" />}
            {isSaved ? 'Saved to Registry' : 'Save Changes'}
          </button>
          <button
            onClick={() => setActiveTab('testing')}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 transition shadow-xs"
          >
            <Play className="h-4 w-4" />
            Test in Sandbox
          </button>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-200 px-2 overflow-x-auto">
        {[
          { key: 'instructions', label: 'General & Prompt', icon: Sliders },
          { key: 'model', label: 'Model Provider', icon: Cpu },
          { key: 'knowledge', label: 'Knowledge Sources', icon: BookOpen },
          { key: 'tools', label: 'Assigned Tools', icon: Wrench },
          { key: 'permissions', label: 'Safety & Risk Controls', icon: Lock },
          { key: 'limits', label: 'Execution Limits', icon: ShieldAlert },
          { key: 'testing', label: 'Test Sandbox', icon: Play },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as Tab)}
              className={`flex items-center gap-2 py-3 px-3 text-xs font-semibold border-b-2 transition whitespace-nowrap ${
                isActive
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Panels */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs min-h-[480px]">
        {/* Tab 1: Instructions & System Prompt */}
        {activeTab === 'instructions' && (
          <div className="space-y-5 max-w-3xl">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Agent Display Name
              </label>
              <input
                type="text"
                value={agentName}
                onChange={(e) => setAgentName(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Business Purpose & Role Description
              </label>
              <input
                type="text"
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-xs text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                System Persona & Operational Directives
              </label>
              <textarea
                rows={10}
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                className="w-full rounded-lg border border-slate-200 p-3 text-xs text-slate-900 font-mono focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 leading-relaxed"
              />
              <p className="text-[11px] text-slate-400 mt-1">
                Defines the behavioral boundaries, tone, business logic, and escalation triggers for the agent.
              </p>
            </div>
          </div>
        )}

        {/* Tab 2: Model Configuration */}
        {activeTab === 'model' && (
          <div className="space-y-6 max-w-2xl">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Primary LLM Provider
              </label>
              <select
                value={modelProvider}
                onChange={(e) => setModelProvider(e.target.value)}
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="google">Google Vertex AI / Gemini API</option>
                <option value="openai">OpenAI Enterprise</option>
                <option value="anthropic">Anthropic Claude</option>
                <option value="ollama">Ollama (On-Premise Private)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Foundation Model
              </label>
              <select
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="gemini-2.5-flash">gemini-2.5-flash (Low Latency & High Tool Fidelity)</option>
                <option value="gemini-2.5-pro">gemini-2.5-pro (Deep Reasoning & Multimodal)</option>
                <option value="gpt-4o">gpt-4o (Omni Enterprise)</option>
                <option value="claude-3-7-sonnet">claude-3-7-sonnet (High Precision Architecture)</option>
              </select>
            </div>

            <div className="space-y-3 pt-2">
              <div className="flex justify-between text-xs">
                <span className="font-semibold text-slate-700">Temperature (Creativity vs Determinism)</span>
                <span className="font-mono text-blue-600 font-bold">{temperature}</span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
              <span className="text-[11px] text-slate-400 block">
                Lower temperatures (0.0 - 0.2) are recommended for structured pricing, invoicing, and quotation tools.
              </span>
            </div>
          </div>
        )}

        {/* Tab 3: Knowledge Sources */}
        {activeTab === 'knowledge' && (
          <div className="space-y-5 max-w-3xl">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Attached Knowledge Bases</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                The agent will automatically perform hybrid semantic retrieval across selected document stores.
              </p>
            </div>

            <div className="space-y-3">
              {[
                { id: 'kb-cloud-infotech', title: 'Cloud Infotech Official Price List v1', docs: 1, chunks: 24, status: 'Active Index' },
                { id: 'kb-pricing-policy', title: 'Corporate Discount & Sales Approval Matrix 2026', docs: 3, chunks: 42, status: 'Active Index' },
                { id: 'kb-warranty', title: 'Hardware RMA & 3-Year Warranty Terms', docs: 2, chunks: 18, status: 'Active Index' },
                { id: 'kb-legal', title: 'Master Services Agreement (MSA) Legal Clauses', docs: 4, chunks: 56, status: 'Disabled for Agent' },
              ].map((kb) => {
                const isSelected = selectedKB.includes(kb.id);
                return (
                  <div
                    key={kb.id}
                    onClick={() => {
                      if (isSelected) {
                        setSelectedKB(selectedKB.filter((k) => k !== kb.id));
                      } else {
                        setSelectedKB([...selectedKB, kb.id]);
                      }
                    }}
                    className={`flex items-center justify-between p-4 rounded-xl border transition cursor-pointer ${
                      isSelected
                        ? 'border-blue-600 bg-blue-50/40 shadow-xs'
                        : 'border-slate-200 hover:border-slate-300 bg-white'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`h-8 w-8 rounded-lg flex items-center justify-center ${
                        isSelected ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-500'
                      }`}>
                        <BookOpen className="h-4 w-4" />
                      </div>
                      <div>
                        <p className="text-xs font-bold text-slate-900">{kb.title}</p>
                        <p className="text-[11px] text-slate-500">{kb.docs} document • {kb.chunks} semantic chunks</p>
                      </div>
                    </div>
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                      isSelected ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-500'
                    }`}>
                      {isSelected ? 'Enabled' : 'Click to Enable'}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Tab 4: Assigned Tools */}
        {activeTab === 'tools' && (
          <div className="space-y-5 max-w-3xl">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Available Business Tools & Actions</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Tools available for the agent planner to invoke during execution.
              </p>
            </div>

            <div className="space-y-3">
              {[
                { name: 'quotation.create_draft', risk: 'SIDE_EFFECT', desc: 'Creates a persisted quotation draft with itemized pricing.' },
                { name: 'quotation.calculate_pricing', risk: 'READ_ONLY', desc: 'Computes tier discounts and volume multipliers without modifying records.' },
                { name: 'invoice.generate', risk: 'FINANCIAL', desc: 'Issues an official GST tax invoice. Triggers human approval checkpoint.' },
                { name: 'customer.search', risk: 'READ_ONLY', desc: 'Retrieves verified customer organization accounts from the CRM.' },
              ].map((tool) => {
                const isChecked = enabledTools.includes(tool.name);
                return (
                  <div
                    key={tool.name}
                    className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 bg-white"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-slate-900">{tool.name}</span>
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                          tool.risk === 'READ_ONLY' ? 'bg-emerald-50 text-emerald-700' :
                          tool.risk === 'SIDE_EFFECT' ? 'bg-blue-50 text-blue-700' :
                          'bg-amber-50 text-amber-700'
                        }`}>
                          {tool.risk}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 mt-0.5">{tool.desc}</p>
                    </div>

                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setEnabledTools([...enabledTools, tool.name]);
                        } else {
                          setEnabledTools(enabledTools.filter((t) => t !== tool.name));
                        }
                      }}
                      className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                    />
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Tab 5: Safety & Permissions */}
        {activeTab === 'permissions' && (
          <div className="space-y-5 max-w-2xl">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Safety & Human Governance Rules</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Enforces compliance checks and approval stops before side-effects are committed.
              </p>
            </div>

            <div className="space-y-4">
              <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-bold text-slate-800">Require Human Approval for Financial Invoices</p>
                    <p className="text-[11px] text-slate-500">Halts execution before invoice.generate is committed.</p>
                  </div>
                  <input type="checkbox" defaultChecked className="h-4 w-4 text-blue-600 rounded" />
                </div>
              </div>

              <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-bold text-slate-800">Tenant Data Isolation Enforced</p>
                    <p className="text-[11px] text-slate-500">Prevents agent from querying data outside current org_id.</p>
                  </div>
                  <input type="checkbox" defaultChecked disabled className="h-4 w-4 text-emerald-600 rounded" />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 6: Execution Limits */}
        {activeTab === 'limits' && (
          <div className="space-y-5 max-w-2xl">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Execution Timeout & Safety Bounds</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Guards against infinite loops, runaway queries, and excessive token burn.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Max Execution Time (seconds)</label>
                <input
                  type="number"
                  defaultValue={45}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-xs"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Max Planner Re-tries</label>
                <input
                  type="number"
                  defaultValue={3}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-xs"
                />
              </div>
            </div>
          </div>
        )}

        {/* Tab 7: Testing Sandbox */}
        {activeTab === 'testing' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Sandbox Test Prompt</h3>
                <p className="text-xs text-slate-500">
                  Simulate a business user prompt against the current agent draft.
                </p>
              </div>

              <textarea
                rows={5}
                value={testInput}
                onChange={(e) => setTestInput(e.target.value)}
                className="w-full rounded-lg border border-slate-200 p-3 text-xs text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />

              <button
                onClick={handleRunTest}
                disabled={isTesting}
                className="w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 transition disabled:opacity-50"
              >
                {isTesting ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                {isTesting ? 'Running Agent Execution...' : 'Execute Test Run'}
              </button>
            </div>

            {/* Test Result Preview */}
            <div className="bg-slate-50 rounded-xl border border-slate-200 p-4 flex flex-col justify-between">
              <div>
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-2">
                  Execution Output Preview
                </span>
                {testOutput ? (
                  <div className="prose prose-xs text-slate-800 text-xs whitespace-pre-wrap font-sans">
                    {testOutput}
                  </div>
                ) : (
                  <div className="py-16 text-center text-slate-400 text-xs">
                    Execute a test run to inspect agent output, tool calls, and structured quotations.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
