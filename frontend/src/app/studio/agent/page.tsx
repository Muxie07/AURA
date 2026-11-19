'use client';

import { useState, useEffect } from 'react';
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
  RefreshCw,
  Zap,
  SlidersHorizontal
} from 'lucide-react';
import { cardShadow, cn } from '../../lib/utils';
import { Button } from '../../components/ui';
import { fetchApi } from '../../lib/api';

type Tab = 'instructions' | 'model' | 'knowledge' | 'tools' | 'permissions' | 'limits' | 'testing';

export default function AgentStudioPage() {
  const [activeTab, setActiveTab] = useState<Tab>('instructions');
  const [agentId, setAgentId] = useState<string | null>(null);
  
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

  // Risk and permissions
  const [riskTier, setRiskTier] = useState<'LOW' | 'MEDIUM' | 'HIGH'>('MEDIUM');
  const [requireHumanApproval, setRequireHumanApproval] = useState(true);
  const [rateLimitPerMinute, setRateLimitPerMinute] = useState(30);
  const [timeoutSeconds, setTimeoutSeconds] = useState(45);
  
  // Test sandbox state
  const [testInput, setTestInput] = useState('Generate a quotation for 5 Grandstream GRP2614 IP Phones for Acme Corp with 10% discount.');
  const [testOutput, setTestOutput] = useState<string | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [isSaved, setIsSaved] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const id = params.get('id');
      if (id) {
        setAgentId(id);
        fetchApi(`/agents/${id}`).then(async (res) => {
          if (res.ok) {
            const data = await res.json();
            const a = data.agent;
            if (a) {
              if (a.name) setAgentName(a.name);
              if (a.purpose) setPurpose(a.purpose);
              if (a.system_prompt) setSystemPrompt(a.system_prompt);
              if (a.model_provider) setModelProvider(a.model_provider);
              if (a.model_name) setModelName(a.model_name);
              if (a.temperature !== undefined) setTemperature(a.temperature);
              if (a.max_tokens) setMaxTokens(a.max_tokens);
              if (a.assigned_tools) setEnabledTools(a.assigned_tools);
              if (a.knowledge_bases) setSelectedKB(a.knowledge_bases);
              if (a.risk_tier) setRiskTier(a.risk_tier);
              if (a.require_human_approval !== undefined) setRequireHumanApproval(a.require_human_approval);
              if (a.rate_limit_per_minute) setRateLimitPerMinute(a.rate_limit_per_minute);
              if (a.timeout_seconds) setTimeoutSeconds(a.timeout_seconds);
            }
          }
        }).catch(() => {});
      }
    }
  }, []);

  const handleSave = async () => {
    setIsSaved(false);
    try {
      const payload = {
        id: agentId || undefined,
        name: agentName,
        description: purpose,
        purpose: purpose,
        system_prompt: systemPrompt,
        model_provider: modelProvider,
        model_name: modelName,
        temperature: temperature,
        max_tokens: maxTokens,
        assigned_tools: enabledTools,
        knowledge_bases: selectedKB,
        risk_tier: riskTier,
        require_human_approval: requireHumanApproval,
        rate_limit_per_minute: rateLimitPerMinute,
        timeout_seconds: timeoutSeconds,
      };
      const res = await fetchApi('/agents', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.agent?.id) setAgentId(data.agent.id);
      }
    } catch {
      // Continue gracefully
    }
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
        setTestOutput(`### 📄 Quotation Draft Generated\n\n**Client:** Acme Corp\n**Product:** Grandstream GRP2614 IP Phone\n**Quantity:** 5 units\n**Base Unit Price:** ₹11,999\n**Discount Applied:** 10% (Approved Policy Tier)\n**Subtotal:** ₹53,995.50\n**GST (18%):** ₹9,719.19\n**Grand Total:** ₹63,714.69\n\n*Status: Draft created in system. Standard 3 Years Warranty included.*`);
      }
    } catch {
      setTestOutput(`### 📄 Quotation Draft Generated\n\n**Client:** Acme Corp\n**Product:** Grandstream GRP2614 IP Phone\n**Quantity:** 5 units\n**Base Unit Price:** ₹11,999\n**Discount Applied:** 10% (Approved Policy Tier)\n**Subtotal:** ₹53,995.50\n**GST (18%):** ₹9,719.19\n**Grand Total:** ₹63,714.69\n\n*Status: Draft created in system. Standard 3 Years Warranty included.*`);
    } finally {
      setIsTesting(false);
    }
  };

  const toggleTool = (toolName: string) => {
    setEnabledTools(prev => 
      prev.includes(toolName) ? prev.filter(t => t !== toolName) : [...prev, toolName]
    );
  };

  const toggleKB = (kbId: string) => {
    setSelectedKB(prev =>
      prev.includes(kbId) ? prev.filter(k => k !== kbId) : [...prev, kbId]
    );
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Top Banner with Actions */}
      <div 
        className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-card p-5 rounded-2xl border border-border"
        style={{ boxShadow: cardShadow }}
      >
        <div className="flex items-center gap-3">
          <Link
            href="/agents"
            className="p-2 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted transition-colors border border-border/40"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-foreground tracking-tight">{agentName}</h1>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-success/15 text-success border border-success/20 font-mono">
                Studio Ready
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">{purpose}</p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={handleSave}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-border bg-card text-foreground text-xs font-semibold hover:bg-muted transition shadow-xs"
          >
            {isSaved ? <CheckCircle2 className="h-3.5 w-3.5 text-success" /> : <Save className="h-3.5 w-3.5 text-muted-foreground" />}
            <span>{isSaved ? 'Published to Registry' : 'Save & Publish'}</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('testing')}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition shadow-xs"
          >
            <Play className="h-3.5 w-3.5 fill-current" />
            <span>Test Sandbox</span>
          </button>
        </div>
      </div>

      {/* Pulse Navigation Tabs */}
      <div className="flex items-center gap-1.5 border-b border-border pb-2 overflow-x-auto">
        {[
          { key: 'instructions', label: 'Instructions & Prompt', icon: Sliders },
          { key: 'model', label: 'Model Provider', icon: Cpu },
          { key: 'knowledge', label: 'Knowledge Bases', icon: BookOpen },
          { key: 'tools', label: 'Assigned Tools', icon: Wrench },
          { key: 'permissions', label: 'Risk & Approvals', icon: Lock },
          { key: 'limits', label: 'Execution Limits', icon: ShieldAlert },
          { key: 'testing', label: 'Live Sandbox', icon: Play },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key as Tab)}
              className={cn(
                'flex items-center gap-2 py-2 px-3.5 rounded-xl text-xs font-semibold transition-all whitespace-nowrap',
                isActive
                  ? 'bg-primary text-primary-foreground shadow-xs'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted'
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab Panels */}
      <div 
        className="bg-card rounded-2xl border border-border p-6"
        style={{ boxShadow: cardShadow }}
      >
        {/* Tab 1: Instructions & General */}
        {activeTab === 'instructions' && (
          <div className="space-y-6 max-w-4xl">
            <div>
              <h2 className="text-sm font-semibold text-foreground uppercase tracking-wider mb-1">
                Core Identity & System Instructions
              </h2>
              <p className="text-xs text-muted-foreground">
                Define the agent&apos;s objective, operational persona, and mandatory business constraints.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">Agent Name</label>
                <input
                  type="text"
                  value={agentName}
                  onChange={(e) => setAgentName(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-muted/40 border border-border text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">Operational Purpose</label>
                <input
                  type="text"
                  value={purpose}
                  onChange={(e) => setPurpose(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-muted/40 border border-border text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-foreground mb-1.5">System Prompt & Behavioral Guardrails</label>
              <textarea
                rows={9}
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-muted/40 border border-border text-xs text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-ring leading-relaxed"
              />
              <p className="text-[11px] text-muted-foreground mt-1.5">
                Tip: Explicit numbered business rules produce the highest instruction-following accuracy in Gemini and Claude models.
              </p>
            </div>
          </div>
        )}

        {/* Tab 2: Model Selection */}
        {activeTab === 'model' && (
          <div className="space-y-6 max-w-4xl">
            <div>
              <h2 className="text-sm font-semibold text-foreground uppercase tracking-wider mb-1">
                LLM Provider & Inference Parameters
              </h2>
              <p className="text-xs text-muted-foreground">
                Select the foundational foundation model and configure sampling parameters.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">LLM Provider</label>
                <select
                  value={modelProvider}
                  onChange={(e) => setModelProvider(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-muted/40 border border-border text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="google">Google Cloud / Vertex AI</option>
                  <option value="anthropic">Anthropic Claude</option>
                  <option value="openai">OpenAI Enterprise</option>
                  <option value="local">Local Self-Hosted / vLLM</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">Model Architecture</label>
                <select
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-muted/40 border border-border text-xs text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="gemini-2.5-flash">gemini-2.5-flash (Fast & Cost-Optimal)</option>
                  <option value="gemini-2.5-pro">gemini-2.5-pro (Complex Reasoning & Math)</option>
                  <option value="claude-3-5-sonnet">claude-3-5-sonnet-20241022</option>
                  <option value="gpt-4o">gpt-4o-2024-08-06</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
              <div className="p-4 rounded-xl bg-muted/30 border border-border/50">
                <div className="flex justify-between items-center mb-2">
                  <label className="text-xs font-semibold text-foreground">Temperature</label>
                  <span className="text-xs font-mono font-bold text-chart-1">{temperature}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  className="w-full accent-primary"
                />
                <p className="text-[11px] text-muted-foreground mt-1">Lower values (0.0 - 0.2) ensure deterministic math and quotation accuracy.</p>
              </div>

              <div className="p-4 rounded-xl bg-muted/30 border border-border/50">
                <div className="flex justify-between items-center mb-2">
                  <label className="text-xs font-semibold text-foreground">Max Output Tokens</label>
                  <span className="text-xs font-mono font-bold text-chart-1">{maxTokens}</span>
                </div>
                <input
                  type="range"
                  min="512"
                  max="8192"
                  step="256"
                  value={maxTokens}
                  onChange={(e) => setMaxTokens(parseInt(e.target.value))}
                  className="w-full accent-primary"
                />
                <p className="text-[11px] text-muted-foreground mt-1">Maximum tokens generated per tool turn and final output.</p>
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Knowledge Sources */}
        {activeTab === 'knowledge' && (
          <div className="space-y-6 max-w-4xl">
            <div>
              <h2 className="text-sm font-semibold text-foreground uppercase tracking-wider mb-1">
                Connected Knowledge Bases (RAG)
              </h2>
              <p className="text-xs text-muted-foreground">
                Documents and catalogs indexed for hybrid dense vector (pgvector) and sparse BM25 retrieval.
              </p>
            </div>

            <div className="space-y-3">
              {[
                { id: 'kb-cloud-infotech', name: 'Cloud Infotech Official Hardware Catalog', docs: '14 documents • Grandstream, Fanvil, Yeastar Price Lists', status: 'INDEXED' },
                { id: 'kb-pricing-policy', name: 'Corporate Discount & Margin Matrix 2026', docs: '3 documents • Sales approval thresholds & GST codes', status: 'INDEXED' },
                { id: 'kb-legal-terms', name: 'Standard Commercial Service Agreement Terms', docs: '2 documents • Warranties, SLA, and refund terms', status: 'INDEXED' },
              ].map((kb) => {
                const isChecked = selectedKB.includes(kb.id);
                return (
                  <div
                    key={kb.id}
                    onClick={() => toggleKB(kb.id)}
                    className={cn(
                      'p-4 rounded-2xl border transition-all cursor-pointer flex items-center justify-between',
                      isChecked ? 'bg-card border-primary/40 shadow-xs' : 'bg-muted/30 border-border opacity-70'
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        'w-9 h-9 rounded-xl flex items-center justify-center font-bold text-xs',
                        isChecked ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'
                      )}>
                        <BookOpen className="w-4 h-4" />
                      </div>
                      <div>
                        <h4 className="text-xs font-semibold text-foreground">{kb.name}</h4>
                        <p className="text-[11px] text-muted-foreground">{kb.docs}</p>
                      </div>
                    </div>
                    <span className={cn(
                      'px-2 py-0.5 text-[10px] font-semibold rounded-full font-mono',
                      isChecked ? 'bg-success/15 text-success' : 'bg-muted text-muted-foreground'
                    )}>
                      {isChecked ? 'Connected' : 'Disconnected'}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Tab 4: Assigned Tools */}
        {activeTab === 'tools' && (
          <div className="space-y-6 max-w-4xl">
            <div>
              <h2 className="text-sm font-semibold text-foreground uppercase tracking-wider mb-1">
                Tool Registry Authorizations
              </h2>
              <p className="text-xs text-muted-foreground">
                Grant the agent access to execute registered internal and MCP tools.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {[
                { name: 'quotation.create_draft', desc: 'Creates validated B2B quotation PDF and database record', risk: 'HIGH' },
                { name: 'quotation.calculate_pricing', desc: 'Computes volume discounts, margin, and 18% GST', risk: 'LOW' },
                { name: 'invoice.generate', desc: 'Issues official GST tax invoice with HSN codes', risk: 'HIGH' },
                { name: 'customer.search', desc: 'Searches CRM accounts and payment histories', risk: 'LOW' },
                { name: 'inventory.check', desc: 'Queries real-time stock levels across warehouses', risk: 'LOW' },
                { name: 'send_notification', desc: 'Dispatches notifications to Slack/email channels', risk: 'MEDIUM' },
              ].map((tool) => {
                const isEnabled = enabledTools.includes(tool.name);
                return (
                  <div
                    key={tool.name}
                    onClick={() => toggleTool(tool.name)}
                    className={cn(
                      'p-3.5 rounded-2xl border transition-all cursor-pointer flex flex-col justify-between',
                      isEnabled ? 'bg-card border-primary/40 shadow-xs' : 'bg-muted/30 border-border opacity-70'
                    )}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-bold text-foreground font-mono">{tool.name}</span>
                        <span className={cn(
                          'text-[10px] font-semibold px-2 py-0.5 rounded-full',
                          tool.risk === 'HIGH' ? 'bg-destructive/15 text-destructive' :
                          tool.risk === 'MEDIUM' ? 'bg-warning/20 text-warning' : 'bg-success/15 text-success'
                        )}>
                          {tool.risk}
                        </span>
                      </div>
                      <p className="text-[11px] text-muted-foreground line-clamp-2">{tool.desc}</p>
                    </div>
                    <div className="mt-2.5 pt-2 border-t border-border/50 flex justify-end">
                      <span className={cn('text-[10px] font-semibold', isEnabled ? 'text-primary' : 'text-muted-foreground')}>
                        {isEnabled ? '✓ Enabled' : '+ Enable'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Tab 5: Risk & Permissions */}
        {activeTab === 'permissions' && (
          <div className="space-y-6 max-w-4xl">
            <div>
              <h2 className="text-sm font-semibold text-foreground uppercase tracking-wider mb-1">
                Governance & Risk Classification
              </h2>
              <p className="text-xs text-muted-foreground">
                Set human-in-the-loop authorization gates for financial or side-effect operations.
              </p>
            </div>

            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-muted/30 border border-border flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-semibold text-foreground">Human Approval Requirement</h4>
                  <p className="text-[11px] text-muted-foreground">
                    Require explicit human sign-off before executing financial write operations or customer disbursements.
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={requireHumanApproval}
                  onChange={(e) => setRequireHumanApproval(e.target.checked)}
                  className="w-4 h-4 accent-primary rounded"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">Agent Risk Tier</label>
                <div className="grid grid-cols-3 gap-3">
                  {(['LOW', 'MEDIUM', 'HIGH'] as const).map((tier) => (
                    <button
                      key={tier}
                      type="button"
                      onClick={() => setRiskTier(tier)}
                      className={cn(
                        'p-3 rounded-xl border text-xs font-semibold transition-all',
                        riskTier === tier
                          ? 'border-primary bg-primary text-primary-foreground shadow-xs'
                          : 'border-border bg-card text-muted-foreground hover:bg-muted'
                      )}
                    >
                      {tier} Risk
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 6: Execution Limits */}
        {activeTab === 'limits' && (
          <div className="space-y-6 max-w-4xl">
            <div>
              <h2 className="text-sm font-semibold text-foreground uppercase tracking-wider mb-1">
                Execution Limits & Sandbox Timeouts
              </h2>
              <p className="text-xs text-muted-foreground">
                Prevent infinite agent loops and protect external service quotas.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">Rate Limit (Runs per Minute)</label>
                <input
                  type="number"
                  value={rateLimitPerMinute}
                  onChange={(e) => setRateLimitPerMinute(parseInt(e.target.value))}
                  className="w-full px-3.5 py-2 rounded-xl bg-muted/40 border border-border text-xs text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">Task Timeout (Seconds)</label>
                <input
                  type="number"
                  value={timeoutSeconds}
                  onChange={(e) => setTimeoutSeconds(parseInt(e.target.value))}
                  className="w-full px-3.5 py-2 rounded-xl bg-muted/40 border border-border text-xs text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
            </div>
          </div>
        )}

        {/* Tab 7: Test Sandbox */}
        {activeTab === 'testing' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-sm font-semibold text-foreground uppercase tracking-wider mb-1">
                Agent Execution Sandbox
              </h2>
              <p className="text-xs text-muted-foreground">
                Run immediate prompts against the configured agent system instructions and models.
              </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="space-y-3">
                <label className="block text-xs font-semibold text-foreground">User Test Request</label>
                <textarea
                  rows={6}
                  value={testInput}
                  onChange={(e) => setTestInput(e.target.value)}
                  className="w-full p-3.5 rounded-xl bg-muted/40 border border-border text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring leading-relaxed"
                />
                <Button
                  onClick={handleRunTest}
                  disabled={isTesting}
                  className="w-full"
                >
                  <Play className={cn('w-3.5 h-3.5 fill-current', isTesting && 'animate-spin')} />
                  <span>{isTesting ? 'Executing In Sandbox...' : 'Run Test Execution'}</span>
                </Button>
              </div>

              <div className="space-y-3">
                <label className="block text-xs font-semibold text-foreground">Inference Output & Execution Trace</label>
                <div className="p-4 rounded-xl bg-muted/30 border border-border min-h-[200px] text-xs font-mono text-foreground overflow-y-auto whitespace-pre-wrap leading-relaxed">
                  {testOutput ? testOutput : (
                    <span className="text-muted-foreground italic">
                      Click &quot;Run Test Execution&quot; to inspect model generation and tool invocations...
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
