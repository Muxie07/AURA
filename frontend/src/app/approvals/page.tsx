'use client';
import { fetchApi } from '../lib/api';
import { useEffect, useState } from 'react';
import { Card, PageHeader, LoadingState, EmptyState, Button } from '../components/ui';
import { ShieldAlert, CheckCircle2, XCircle, Clock, Info, Loader2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processingId, setProcessingId] = useState<string | null>(null);

  async function fetchData() {
    try {
      const res = await fetchApi('/approvals');
      if (res.ok) {
        const json = await res.json();
        setApprovals(json.approvals || []);
      } else {
        setError('Failed to fetch approvals.');
      }
    } catch (err) {
      console.error(err);
      setError('An error occurred while fetching approvals.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchData();
  }, []);

  async function handleAction(id: string, action: 'approve' | 'reject') {
    if (processingId) return;
    setProcessingId(id);
    try {
      const res = await fetchApi(`/approvals/${id}/${action}`, { method: 'POST' });
      if (!res.ok) {
        let msg = 'Action failed';
        try {
          const errData = await res.json();
          msg = errData.detail || msg;
        } catch(e) {}
        throw new Error(msg);
      }
      
      // Successfully updated, refresh list
      await fetchData();
    } catch (err: any) {
      alert(err.message || 'Unable to complete action.');
    } finally {
      setProcessingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader 
        title="Action Required" 
        description="Review and authorize actions requested by AURA."
      />

      {loading ? (
        <LoadingState message="Loading approvals..." />
      ) : error ? (
        <div className="p-4 bg-red-50 text-red-600 rounded-lg border border-red-200">
          {error}
        </div>
      ) : approvals.length === 0 ? (
        <EmptyState 
          title="All Caught Up!" 
          description="There are no pending actions requiring your authorization at this time." 
          icon={CheckCircle2} 
        />
      ) : (
        <div className="grid gap-6">
          {approvals.map(approval => {
            const isPending = approval.status === 'PENDING';
            const isApproved = approval.status === 'APPROVED';
            const isProcessing = processingId === approval.id;
            
            return (
              <Card key={approval.id} className={`border-l-4 ${isPending ? 'border-l-amber-500' : isApproved ? 'border-l-emerald-500' : 'border-l-rose-500'}`}>
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${isPending ? 'bg-amber-50 text-amber-600' : isApproved ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'}`}>
                      {isPending ? <ShieldAlert className="w-6 h-6" /> : isApproved ? <CheckCircle2 className="w-6 h-6" /> : <XCircle className="w-6 h-6" />}
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900 text-lg">AURA wants to: <span className="font-normal text-gray-700">{approval.action_summary || approval.tool_name}</span></h3>
                      <p className="text-sm text-gray-500 flex items-center gap-1 mt-1">
                        <Clock className="w-3.5 h-3.5" /> Requested {formatDistanceToNow(new Date(approval.created_at))} ago
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${isPending ? 'bg-amber-100 text-amber-800' : isApproved ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}`}>
                      {isPending ? 'Approval Required' : isApproved ? 'Approved' : 'Rejected'}
                    </span>
                  </div>
                </div>
                
                <div className="bg-gray-50 rounded-lg p-4 border border-gray-100 mb-4">
                  <div className="flex items-start gap-2 text-sm text-gray-700 mb-2">
                    <Info className="w-4 h-4 text-blue-500 mt-0.5 shrink-0" />
                    <p><strong>Why:</strong> This action will modify company data or systems and requires human verification.</p>
                  </div>
                  
                  <details className="mt-4">
                    <summary className="text-xs text-blue-600 cursor-pointer font-medium hover:underline">View technical details</summary>
                    <div className="mt-2 text-xs text-gray-600 space-y-2">
                      <p><strong>Tool Name:</strong> <span className="font-mono">{approval.tool_name}</span></p>
                      <p><strong>Run ID:</strong> <span className="font-mono">{approval.run_id}</span></p>
                      <pre className="bg-white p-3 rounded border border-gray-200 overflow-x-auto max-h-40 mt-1">
                        {JSON.stringify(approval.payload || approval.action_details, null, 2)}
                      </pre>
                    </div>
                  </details>
                </div>

                {isPending && (
                  <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
                    <Button variant="outline" className="text-rose-600 border-rose-200 hover:bg-rose-50" onClick={() => handleAction(approval.id, 'reject')} disabled={processingId !== null}>
                      {processingId === approval.id ? <Loader2 className="w-4 h-4 animate-spin mr-2 inline" /> : null}
                      Reject
                    </Button>
                    <Button variant="primary" className="bg-emerald-600 hover:bg-emerald-700" onClick={() => handleAction(approval.id, 'approve')} disabled={processingId !== null}>
                      {processingId === approval.id ? <Loader2 className="w-4 h-4 animate-spin mr-2 inline" /> : null}
                      Approve
                    </Button>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
