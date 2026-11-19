'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { 
  ShieldAlert, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  Loader2, 
  Check, 
  X,
  RefreshCw,
  Search,
  Mail,
  ChevronDown,
  ChevronUp,
  FileText,
  Lock,
  ExternalLink,
  Sparkles,
  DollarSign
} from 'lucide-react';
import { fetchApi } from '../lib/api';
import { cardShadow, cn } from '../lib/utils';
import { Button, EmptyState } from '../components/ui';

interface ApprovalItem {
  id: string;
  agent_run_id?: string;
  run_id?: string;
  action_summary?: string;
  tool_name?: string;
  agent_name?: string;
  status: 'pending' | 'approved' | 'denied' | 'rejected' | 'executed' | 'expired' | string;
  created_at?: string;
  expires_at?: string;
  actioned_at?: string;
  args_hash?: string;
  action_details?: Record<string, any>;
  payload?: Record<string, any>;
}

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [gmailStatus, setGmailStatus] = useState<any>(null);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  async function fetchData() {
    setLoading(true);
    try {
      const res = await fetchApi('/approvals');
      if (res.ok) {
        const json = await res.json();
        const list = json.approvals || [];
        setApprovals(list);
      } else {
        setError('Failed to fetch approvals from AURA engine.');
      }

      // Fetch Gmail integration status for header indicator
      try {
        const gRes = await fetchApi('/integrations/gmail/status');
        if (gRes.ok) {
          const gJson = await gRes.json();
          setGmailStatus(gJson);
        }
      } catch {}
    } catch (err: any) {
      console.error(err);
      setError('An error occurred while connecting to the authorization service.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchData();
  }, []);

  function toggleExpand(id: string) {
    setExpandedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleAction(id: string, action: 'approve' | 'reject') {
    if (processingId) return;
    setProcessingId(id);
    try {
      const res = await fetchApi(`/approvals/${id}/${action}`, { method: 'POST' });
      if (!res.ok) {
        let msg = `Failed to ${action} approval request.`;
        try {
          const errData = await res.json();
          msg = errData.detail || errData.message || msg;
        } catch {}
        throw new Error(msg);
      }
      
      setToastMessage(`Action ${action === 'approve' ? 'authorized' : 'rejected'} successfully.`);
      setTimeout(() => setToastMessage(null), 3500);
      await fetchData();
    } catch (err: any) {
      alert(err.message || 'Unable to complete action.');
    } finally {
      setProcessingId(null);
    }
  }

  const normalizeStatus = (st: string) => (st || '').toLowerCase();

  const pendingCount = approvals.filter(a => normalizeStatus(a.status) === 'pending').length;
  const approvedCount = approvals.filter(a => normalizeStatus(a.status) === 'approved').length;
  const executedCount = approvals.filter(a => normalizeStatus(a.status) === 'executed').length;
  const rejectedCount = approvals.filter(a => ['denied', 'rejected'].includes(normalizeStatus(a.status))).length;

  const filteredApprovals = approvals.filter(a => {
    const s = normalizeStatus(a.status);
    let matchesStatus = true;
    if (filterStatus === 'PENDING') matchesStatus = s === 'pending';
    else if (filterStatus === 'APPROVED') matchesStatus = s === 'approved';
    else if (filterStatus === 'EXECUTED') matchesStatus = s === 'executed';
    else if (filterStatus === 'REJECTED') matchesStatus = s === 'denied' || s === 'rejected';

    const summary = (a.action_summary || a.tool_name || '').toLowerCase();
    const details = JSON.stringify(a.action_details || {}).toLowerCase();
    const matchesSearch = summary.includes(searchQuery.toLowerCase()) || 
                          details.includes(searchQuery.toLowerCase()) ||
                          a.id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  return (
    <div className="space-y-6 pb-12">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground text-xs font-semibold shadow-lg animate-slide-up flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Page Header with Clean Integration Link */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2">
        <div>
          <h1 className="text-xl font-bold text-foreground">Action Approvals &amp; Governance Gates</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Phase 8 AURA Action Monitor: Review proposed, awaiting approval, authorized, and executed business operations.
          </p>
        </div>
        <div className="flex items-center gap-2.5 shrink-0">
          <Link
            href="/settings#integrations"
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl border border-border bg-card hover:bg-muted text-xs text-muted-foreground hover:text-foreground transition shadow-xs"
            title="Configure Gmail Notifications in Settings"
          >
            <Mail className="w-3.5 h-3.5 text-primary" />
            <span>Gmail Gateway:</span>
            <span className={cn(
              "font-semibold text-[11px] px-1.5 py-0.5 rounded-md",
              gmailStatus?.is_connected || gmailStatus?.connected 
                ? "bg-emerald-500/15 text-emerald-500" 
                : "bg-muted text-muted-foreground"
            )}>
              {gmailStatus?.is_connected || gmailStatus?.connected ? `Connected (${gmailStatus.connected_email || 'Active'})` : "Manage in Settings"}
            </span>
          </Link>

          <Button
            variant="outline"
            size="sm"
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-1.5"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", loading && "animate-spin")} />
            <span>Refresh</span>
          </Button>
        </div>
      </div>

      {/* Top Pulse KPI Summary Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div
          className="bg-card rounded-2xl p-5 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <p className="text-xs font-medium text-muted-foreground mb-1">Awaiting Approval</p>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-amber-500">{pendingCount}</p>
            <span className={cn(
              "text-xs font-semibold",
              pendingCount > 0 ? "text-amber-500" : "text-emerald-500"
            )}>
              {pendingCount > 0 ? "Gate Active" : "All Clear"}
            </span>
          </div>
        </div>

        <div
          className="bg-card rounded-2xl p-5 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <p className="text-xs font-medium text-muted-foreground mb-1">Executed Actions</p>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-sky-500">{executedCount}</p>
            <span className="text-xs font-semibold text-sky-500">Resumed &amp; Completed</span>
          </div>
        </div>

        <div
          className="bg-card rounded-2xl p-5 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <p className="text-xs font-medium text-muted-foreground mb-1">Authorized Pending Exec</p>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-emerald-500">{approvedCount}</p>
            <span className="text-xs font-semibold text-emerald-500">Authorized</span>
          </div>
        </div>

        <div
          className="bg-card rounded-2xl p-5 border border-border"
          style={{ boxShadow: cardShadow }}
        >
          <p className="text-xs font-medium text-muted-foreground mb-1">Rejected / Blocked</p>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-destructive">{rejectedCount}</p>
            <span className="text-xs font-semibold text-muted-foreground">Denied</span>
          </div>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3 flex-1 max-w-md">
          <div className="relative w-full">
            <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              placeholder="Search by action, client, quotation ID, or parameters..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 rounded-xl bg-card border border-border text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
        </div>

        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          {[
            { id: 'ALL', label: `All (${approvals.length})` },
            { id: 'PENDING', label: `Pending (${pendingCount})` },
            { id: 'APPROVED', label: `Approved (${approvedCount})` },
            { id: 'EXECUTED', label: `Executed (${executedCount})` },
            { id: 'REJECTED', label: `Rejected (${rejectedCount})` },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setFilterStatus(tab.id)}
              className={cn(
                'px-3 py-1.5 rounded-full text-xs font-semibold transition-colors whitespace-nowrap',
                filterStatus === tab.id
                  ? 'bg-primary text-primary-foreground shadow-xs'
                  : 'bg-card border border-border text-muted-foreground hover:bg-muted'
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Approvals Listing */}
      {loading ? (
        <div className="p-12 text-center text-xs text-muted-foreground">
          <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-chart-1" />
          Loading governance approval gates...
        </div>
      ) : filteredApprovals.length === 0 ? (
        <EmptyState
          title="No Actions Matching Filter"
          description="There are currently no approval requests matching your search or status selection."
          icon={CheckCircle2}
        />
      ) : (
        <div className="space-y-4">
          {filteredApprovals.map((approval) => {
            const st = normalizeStatus(approval.status);
            const isPending = st === 'pending';
            const isApproved = st === 'approved';
            const isExecuted = st === 'executed';
            const isRejected = st === 'denied' || st === 'rejected';
            const isProcessing = processingId === approval.id;
            const isExpanded = expandedIds.has(approval.id);

            const details = approval.action_details || approval.payload || {};
            const companyName = details.company_name || details.customer_name || 'Enterprise Customer';
            const finImpact = details.financial_impact || (details.total ? `Total: $${details.total}` : 'Operational Action');
            const targetRecipient = details.target_recipient || details.recipient || 'Internal / Stakeholder';
            const actionText = approval.action_summary || approval.tool_name || 'Execute business action';

            return (
              <div
                key={approval.id}
                className={cn(
                  'bg-card rounded-2xl border p-5 transition-all',
                  isPending ? 'border-amber-500/50 shadow-sm' : isExecuted ? 'border-sky-500/30' : 'border-border'
                )}
                style={{ boxShadow: cardShadow }}
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-3">
                  <div className="flex items-start gap-3.5">
                    <div className={cn(
                      'w-10 h-10 rounded-xl flex items-center justify-center shrink-0',
                      isPending ? 'bg-amber-500/15 text-amber-500' :
                      isExecuted ? 'bg-sky-500/15 text-sky-500' :
                      isApproved ? 'bg-emerald-500/15 text-emerald-500' : 'bg-destructive/15 text-destructive'
                    )}>
                      {isPending ? (
                        <ShieldAlert className="w-5 h-5" />
                      ) : isExecuted ? (
                        <CheckCircle2 className="w-5 h-5" />
                      ) : isApproved ? (
                        <Sparkles className="w-5 h-5" />
                      ) : (
                        <XCircle className="w-5 h-5" />
                      )}
                    </div>

                    <div>
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-muted text-muted-foreground font-mono">
                          ID: {approval.id.slice(0, 12)}...
                        </span>
                        <span className={cn(
                          'text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase',
                          isPending ? 'bg-amber-500/20 text-amber-500' :
                          isExecuted ? 'bg-sky-500/20 text-sky-500' :
                          isApproved ? 'bg-emerald-500/15 text-emerald-500' : 'bg-destructive/15 text-destructive'
                        )}>
                          {isPending ? 'Awaiting Human Approval' : isExecuted ? 'Executed & Resumed' : isApproved ? 'Authorized (Pending Exec)' : 'Rejected'}
                        </span>
                        {approval.args_hash && (
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-muted text-muted-foreground flex items-center gap-1">
                            <Lock className="w-3 h-3 text-emerald-500" />
                            SHA-256: {approval.args_hash.slice(0, 8)}...
                          </span>
                        )}
                      </div>

                      <h3 className="text-sm font-bold text-foreground leading-snug">
                        {actionText}
                      </h3>

                      <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1 flex-wrap">
                        <span>Client: <strong className="text-foreground">{companyName}</strong></span>
                        <span>&bull;</span>
                        <span>Recipient: <strong className="text-foreground">{targetRecipient}</strong></span>
                        <span>&bull;</span>
                        <span>Impact: <strong className="text-foreground">{finImpact}</strong></span>
                        {approval.created_at && (
                          <>
                            <span>&bull;</span>
                            <span>{new Date(approval.created_at).toLocaleString()}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Actions for Pending */}
                  {isPending && (
                    <div className="flex items-center gap-2.5 shrink-0 sm:self-center">
                      <button
                        type="button"
                        onClick={() => handleAction(approval.id, 'reject')}
                        disabled={isProcessing}
                        className="px-3.5 py-1.5 rounded-xl border border-destructive/30 text-destructive hover:bg-destructive/10 text-xs font-semibold transition-colors disabled:opacity-50 flex items-center gap-1.5"
                      >
                        {isProcessing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <X className="w-3.5 h-3.5" />}
                        <span>Reject</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => handleAction(approval.id, 'approve')}
                        disabled={isProcessing}
                        className="px-4 py-1.5 rounded-xl bg-emerald-500 text-white hover:bg-emerald-600 text-xs font-semibold shadow-xs transition-colors disabled:opacity-50 flex items-center gap-1.5"
                      >
                        {isProcessing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                        <span>Authorize Action</span>
                      </button>
                    </div>
                  )}
                </div>

                {/* Evidence & Details Toggle Button */}
                <div className="pt-2 border-t border-border/50 flex items-center justify-between">
                  <button
                    type="button"
                    onClick={() => toggleExpand(approval.id)}
                    className="inline-flex items-center gap-1.5 text-xs text-primary hover:underline font-semibold"
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>{isExpanded ? 'Hide Evidence & Snapshot' : 'Inspect Evidence & Cryptographic Snapshot'}</span>
                    {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  </button>

                  <span className="text-[11px] font-mono text-muted-foreground">
                    Tool: {approval.tool_name || 'external_tool'}
                  </span>
                </div>

                {/* Expanded Structured Evidence Drawer (Phase 2 & Phase 8) */}
                {isExpanded && (
                  <div className="mt-3 p-4 rounded-xl bg-muted/40 border border-border/60 text-xs space-y-3 animate-fade-in">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div>
                        <span className="text-muted-foreground font-semibold block mb-0.5">Business Objective:</span>
                        <p className="text-foreground">{details.business_objective || 'N/A'}</p>
                      </div>
                      <div>
                        <span className="text-muted-foreground font-semibold block mb-0.5">Policy Justification:</span>
                        <p className="text-foreground">{details.why_necessary || details.approval_policy || 'External side-effect gate.'}</p>
                      </div>
                      <div>
                        <span className="text-muted-foreground font-semibold block mb-0.5">Financial Impact:</span>
                        <p className="text-emerald-500 font-semibold">{finImpact}</p>
                      </div>
                      <div>
                        <span className="text-muted-foreground font-semibold block mb-0.5">Operational Risk:</span>
                        <p className="text-amber-500">{details.risks_and_uncertainties || 'Irreversible external dispatch upon authorization.'}</p>
                      </div>
                    </div>

                    <div>
                      <span className="text-muted-foreground font-semibold block mb-1">Frozen Action Parameters Snapshot:</span>
                      <pre className="font-mono text-[11px] text-foreground bg-card p-3 rounded-lg border border-border overflow-x-auto max-h-48 whitespace-pre-wrap">
                        {JSON.stringify(details.exact_parameters || details, null, 2)}
                      </pre>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1 border-t border-border/40">
                      <span>Cryptographic Checksum: <code className="font-mono text-foreground">{approval.args_hash || 'SHA-256'}</code></span>
                      {approval.agent_run_id && (
                        <Link href={`/observability`} className="text-primary hover:underline flex items-center gap-1">
                          <span>View Run Traces</span>
                          <ExternalLink className="w-3 h-3" />
                        </Link>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
