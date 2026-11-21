import os

app_dir = 'frontend/src/app'

dashboard_content = """'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';

export default function Dashboard() {
  const [runs, setRuns] = useState<any[]>([]);
  const [approvals, setApprovals] = useState<any[]>([]);
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const token = localStorage.getItem('token') || 'test-token';
        const headers = { 'Authorization': `Bearer ${token}` };
        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

        const [runsRes, appRes, healthRes] = await Promise.all([
          fetch(`${API_URL}/agent/runs`, { headers }),
          fetch(`${API_URL}/agent/approvals`, { headers }),
          fetch(`http://localhost:8000/health`)
        ]);

        if (runsRes.ok) setRuns((await runsRes.json()).runs || []);
        if (appRes.ok) setApprovals((await appRes.json()).approvals || []);
        if (healthRes.ok) setHealth(await healthRes.json());
      } catch (err) {
        console.error("Dashboard fetch error:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-2 text-sm text-gray-700">Overview of AURA Enterprise AI Operations.</p>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 mb-8">
        <div className="bg-white overflow-hidden shadow rounded-lg border border-gray-200">
          <div className="p-5">
            <dt className="text-sm font-medium text-gray-500 truncate">System Status</dt>
            <dd className="mt-1 text-3xl font-semibold text-gray-900">
              {health ? <span className="text-green-600">Healthy</span> : <span className="text-red-600">Unknown</span>}
            </dd>
          </div>
        </div>
        <div className="bg-white overflow-hidden shadow rounded-lg border border-gray-200">
          <div className="p-5">
            <dt className="text-sm font-medium text-gray-500 truncate">Total Agent Runs</dt>
            <dd className="mt-1 text-3xl font-semibold text-gray-900">{runs.length}</dd>
          </div>
        </div>
        <div className="bg-white overflow-hidden shadow rounded-lg border border-gray-200">
          <div className="p-5">
            <dt className="text-sm font-medium text-gray-500 truncate">Pending Approvals</dt>
            <dd className="mt-1 text-3xl font-semibold text-gray-900">{approvals.length}</dd>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-white shadow rounded-lg border border-gray-200">
          <div className="px-4 py-5 sm:px-6 border-b border-gray-200 flex justify-between items-center">
            <h3 className="text-lg leading-6 font-medium text-gray-900">Recent Agent Runs</h3>
            <Link href="/agents" className="text-sm text-blue-600 hover:text-blue-500">View all</Link>
          </div>
          <div className="p-4">
            {loading ? (
              <div className="animate-pulse space-y-4">
                <div className="h-10 bg-gray-200 rounded w-full"></div>
                <div className="h-10 bg-gray-200 rounded w-full"></div>
              </div>
            ) : runs.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-4">No recent runs found.</p>
            ) : (
              <ul className="divide-y divide-gray-200">
                {runs.slice(0, 5).map(r => (
                  <li key={r.run_id} className="py-3 flex justify-between items-center">
                    <div>
                      <p className="text-sm font-medium text-gray-900 font-mono">{r.run_id.substring(0,8)}</p>
                      <p className="text-xs text-gray-500">{new Date(r.started_at).toLocaleString()}</p>
                    </div>
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${r.status === 'COMPLETED' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
                      {r.status}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="bg-white shadow rounded-lg border border-gray-200">
          <div className="px-4 py-5 sm:px-6 border-b border-gray-200 flex justify-between items-center">
            <h3 className="text-lg leading-6 font-medium text-gray-900">Action Required</h3>
            <Link href="/approvals" className="text-sm text-blue-600 hover:text-blue-500">View approvals</Link>
          </div>
          <div className="p-4">
            {loading ? (
              <div className="animate-pulse space-y-4">
                <div className="h-10 bg-gray-200 rounded w-full"></div>
              </div>
            ) : approvals.length === 0 ? (
              <div className="text-center py-6">
                <p className="text-sm text-gray-500">All caught up! No pending approvals.</p>
              </div>
            ) : (
              <ul className="divide-y divide-gray-200">
                {approvals.slice(0, 5).map(a => (
                  <li key={a.id} className="py-3">
                    <p className="text-sm font-medium text-gray-900">Tool: {a.tool_name}</p>
                    <p className="text-xs text-gray-500 truncate">{a.action_summary}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
"""

with open(os.path.join(app_dir, 'page.tsx'), 'w', encoding='utf-8') as f:
    f.write(dashboard_content)

print("Dashboard written.")
