'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card, PageHeader, LoadingState, StatusBadge, EmptyState, Button } from './components/ui';
import { fetchApi } from './lib/api';
import { Activity, Bot, ShieldCheck, ArrowRight, Server, Zap, Database, RefreshCw } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export default function Dashboard() {

  const [runs, setRuns] = useState<any[]>([]);
  const [approvals, setApprovals] = useState<any[]>([]);
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    try {
      const [runsRes, appRes, healthRes] = await Promise.all([
        fetchApi('/runs').catch(() => null),
        fetchApi('/approvals').catch(() => null),
        fetch((process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1').replace('/api/v1', '/health')).catch(() => null)
      ]);

      if (runsRes) setRuns((await runsRes.json()).runs || []);
      if (appRes) setApprovals((await appRes.json()).approvals || []);
      if (healthRes?.ok) setHealth(await healthRes.json());
      setError(null);
    } catch (err: any) {
      console.error("Dashboard fetch error:", err);
      setError(err.message || "Failed to load dashboard data");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);
  if (loading) return <LoadingState message="Loading enterprise dashboard..." />;
  if (error) return <div className="p-4 bg-red-50 text-red-600 rounded-lg border border-red-200">Error: {error}</div>;

  const systemStatus = health?.status === 'ok' ? 'Healthy' : (health ? 'Degraded' : 'Unknown');

  return (
    <div className="space-y-6">
      <PageHeader 
        title="Command Center" 
        description="Overview of AURA Enterprise AI Operations. Monitor AI Tasks, system health, and pending approvals."
        actions={<div className="flex gap-3"><button onClick={() => fetchData(true)} disabled={refreshing} className="inline-flex items-center justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-700 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 disabled:opacity-50"><RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? "animate-spin" : ""}`} /> Refresh</button><Link href="/conversations" className="inline-flex items-center justify-center rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500"><Zap className="w-4 h-4 mr-2" /> Ask AURA</Link></div>}
      />

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <div className="flex items-center gap-4">
            <div className="p-3 bg-blue-50 text-blue-600 rounded-lg">
              <Server className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">System Status</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-1">{systemStatus}</h3>
            </div>
          </div>
        </Card>
        
        <Card>
          <div className="flex items-center gap-4">
            <div className="p-3 bg-indigo-50 text-indigo-600 rounded-lg">
              <Activity className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Active Tasks</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-1">{runs.filter(r => r.status?.toUpperCase() === 'RUNNING').length}</h3>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-4">
            <div className="p-3 bg-emerald-50 text-emerald-600 rounded-lg">
              <Bot className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Total AI Tasks</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-1">{runs.length}</h3>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-4">
            <div className="p-3 bg-amber-50 text-amber-600 rounded-lg">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Pending Approvals</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-1">{approvals.length}</h3>
            </div>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card 
          title={<span className="flex items-center gap-2"><Activity className="w-5 h-5 text-gray-500" /> Recent Activity</span>}
          action={<Link href="/agents" className="text-sm text-blue-600 hover:text-blue-500 flex items-center gap-1 font-medium">View all <ArrowRight className="w-4 h-4" /></Link>}
          noPadding
        >
          {runs.length === 0 ? (
            <div className="p-6">
              <EmptyState title="No recent activity" description="Start a conversation to see activity here." icon={Database} />
            </div>
          ) : (
            <ul className="divide-y divide-gray-100">
              {runs.slice(0, 6).map(r => (
                <li key={r.run_id} className="p-4 hover:bg-gray-50 transition-colors flex justify-between items-center">
                  <div className="flex items-start gap-3">
                    <div className="mt-1"><Bot className="w-5 h-5 text-gray-400" /></div>
                    <div>
                      <p className="text-sm font-medium text-gray-900 font-mono">{r.user_request || `Task ${String(r.run_id).substring(0,8)}`}</p>
                      <p className="text-xs text-gray-500">Started {r.started_at ? formatDistanceToNow(new Date(r.started_at)) + ' ago' : 'recently'}</p>
                    </div>
                  </div>
                  <StatusBadge status={r.status} />
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card 
          title={<span className="flex items-center gap-2"><ShieldCheck className="w-5 h-5 text-gray-500" /> Action Required</span>}
          action={<Link href="/approvals" className="text-sm text-blue-600 hover:text-blue-500 flex items-center gap-1 font-medium">Review <ArrowRight className="w-4 h-4" /></Link>}
          noPadding
        >
          {approvals.length === 0 ? (
            <div className="p-6">
              <EmptyState title="All caught up" description="No pending approvals require your attention." icon={ShieldCheck} />
            </div>
          ) : (
            <ul className="divide-y divide-gray-100">
              {approvals.slice(0, 6).map(a => (
                <li key={a.id} className="p-4 hover:bg-gray-50 transition-colors">
                  <div className="flex justify-between items-start mb-1">
                    <p className="text-sm font-semibold text-gray-900 flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
                      Action: {a.tool_name}
                    </p>
                    <span className="text-xs text-gray-500">{a.created_at ? formatDistanceToNow(new Date(a.created_at)) + ' ago' : 'recently'}</span>
                  </div>
                  <p className="text-sm text-gray-600 line-clamp-2 ml-4">{a.action_summary}</p>
                  <div className="mt-3 ml-4 flex gap-2">
                    <Link href="/approvals" className="inline-flex items-center justify-center rounded-md bg-blue-600 px-3 py-1 text-xs font-semibold text-white shadow-sm hover:bg-blue-500">Review</Link>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
