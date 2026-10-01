'use client';
import { fetchApi } from '../lib/api';
import { useEffect, useState } from 'react';
import { Card, PageHeader, LoadingState, StatusBadge, EmptyState, Button } from '../components/ui';
import { Bot, Plus, Search, CheckCircle2, Play, Activity, SearchIcon, Calculator, FileText, Wrench } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import Link from 'next/link';

export default function TasksPage() {
  const [runs, setRuns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await fetchApi('/runs');
        if (res.ok) {
          const json = await res.json();
          setRuns(json.runs || []);
        } else {
          setError('Failed to fetch tasks.');
        }
      } catch (err) {
        console.error(err);
        setError('An error occurred while fetching tasks.');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const capabilities = [
    { icon: SearchIcon, title: 'Search Company Knowledge', desc: 'Find policies, runbooks, and docs.' },
    { icon: Activity, title: 'Investigate Issues', desc: 'Analyze logs, metrics, and systems.' },
    { icon: Calculator, title: 'Calculate & Analyze', desc: 'Process pricing, costs, and data.' },
    { icon: FileText, title: 'Prepare Drafts', desc: 'Create reports, emails, and quotes.' }
  ];

  return (
    <div className="space-y-6 h-full flex flex-col">
      <PageHeader 
        title="AI Tasks" 
        description="See what the AI has worked on and what it decided."
        actions={
          <Link href="/conversations" className="inline-flex items-center justify-center rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500">
            <Plus className="w-4 h-4 mr-2" /> Start New Task
          </Link>
        }
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {capabilities.map((cap, i) => (
          <div key={i} className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex items-start gap-3">
            <div className="p-2 bg-blue-50 text-blue-600 rounded-lg shrink-0">
              <cap.icon className="w-5 h-5" />
            </div>
            <div>
              <h4 className="font-semibold text-gray-900 text-sm">{cap.title}</h4>
              <p className="text-xs text-gray-500 mt-0.5">{cap.desc}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="flex justify-between items-center bg-white p-3 rounded-lg border border-gray-200 shadow-sm">
        <div className="relative w-full max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input 
            type="text" 
            placeholder="Search past tasks..." 
            className="w-full pl-9 pr-4 py-2 bg-gray-50 border-none rounded-md text-sm focus:ring-2 focus:ring-blue-500 outline-none transition-all"
          />
        </div>
      </div>

      <Card noPadding className="flex-1">
        {loading ? (
          <LoadingState message="Loading AI tasks..." />
        ) : error ? (
          <div className="p-12 text-center text-red-600">
            <div className="p-4 bg-red-50 rounded-lg inline-block border border-red-200">
              {error}
            </div>
          </div>
        ) : runs.length === 0 ? (
          <div className="p-12">
            <EmptyState 
              title="No AI Tasks" 
              description="AURA hasn't completed any tasks yet." 
              icon={Bot} 
              action={<Link href="/conversations" className="mt-4 inline-flex items-center justify-center rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500"><Play className="w-4 h-4 mr-2" /> Start First Task</Link>}
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Task Request</th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Started</th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tools Used</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {runs.map((run) => (
                  <tr key={run.run_id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 h-8 w-8 bg-blue-100 rounded-md flex items-center justify-center text-blue-600">
                          <Bot className="h-5 w-5" />
                        </div>
                        <div className="ml-4 max-w-sm">
                          <div className="text-sm font-medium text-gray-900 truncate">
                            {run.user_request || "Unknown Task"}
                          </div>
                          <div className="text-xs text-blue-600 font-mono hover:underline mt-0.5">
                            <Link href={`/observability`}>View technical details</Link>
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <StatusBadge status={run.status} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(run.started_at).toLocaleString()}
                      <div className="text-xs text-gray-400 mt-1">{formatDistanceToNow(new Date(run.started_at))} ago</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 flex items-center gap-2">
                      <Wrench className="w-4 h-4 text-gray-400" />
                      {run.tool_call_count || 0} Actions Taken
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
