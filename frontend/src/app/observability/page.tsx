'use client';
import { fetchApi } from '../lib/api';
import { useEffect, useState } from 'react';
import { PageHeader, Card, StatusBadge, EmptyState } from '../components/ui';
import { Activity, Database, Wrench, Search, Clock, Cpu } from 'lucide-react';

export default function ObservabilityPage() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await fetchApi('/runs');
        if (res.ok) {
          const json = await res.json();
          setData(json.runs || []);
        } else {
          setError('Failed to fetch observability data.');
        }
      } catch (err) {
        console.error(err);
        setError('An error occurred while fetching data.');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader 
        title="Observability" 
        description="Technical audit logs, timelines, and execution traces for AURA AI Tasks." 
      />

      {loading ? (
        <div className="grid gap-6">
          <Card className="animate-pulse h-40"><div /></Card>
        </div>
      ) : error ? (
        <div className="p-4 bg-red-50 text-red-600 rounded-lg border border-red-200">
          {error}
        </div>
      ) : data.length === 0 ? (
        <EmptyState 
          icon={Activity} 
          title="No data available" 
          description="No AI tasks or traces were found." 
        />
      ) : (
        <div className="grid gap-6">
          {data.map((item, idx) => (
            <Card key={item.run_id || idx} className="overflow-hidden p-0">
              <div className="border-b border-gray-200 bg-gray-50 px-6 py-4 flex justify-between items-center">
                <div>
                  <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                    <Activity className="w-4 h-4 text-blue-600" /> AI Task Trace
                  </h3>
                  <p className="text-sm font-mono text-gray-500 mt-1">{item.run_id}</p>
                </div>
                <StatusBadge status={item.status} />
              </div>
              
              <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 space-y-6">
                  <div>
                    <h4 className="text-sm font-semibold text-gray-900 mb-2">Request</h4>
                    <div className="bg-white border border-gray-200 rounded-lg p-3 text-sm text-gray-700">
                      {item.user_request || 'No user request specified'}
                    </div>
                  </div>
                  
                  <div>
                    <h4 className="text-sm font-semibold text-gray-900 mb-2">Activity Timeline</h4>
                    <ul className="space-y-3 relative border-l border-gray-200 ml-3 pl-4">
                      <li className="relative">
                        <div className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-blue-500 ring-4 ring-white"></div>
                        <p className="text-sm text-gray-700">✓ Request received</p>
                      </li>
                      <li className="relative">
                        <div className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-blue-500 ring-4 ring-white"></div>
                        <p className="text-sm text-gray-700">✓ AI analyzed request</p>
                      </li>
                      {(item.tool_call_count || 0) > 0 && (
                        <li className="relative">
                          <div className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-amber-500 ring-4 ring-white"></div>
                          <p className="text-sm text-gray-700">✓ Actions taken (Tools executed: {item.tool_call_count})</p>
                        </li>
                      )}
                      <li className="relative">
                        <div className={`absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full ${item.status === 'COMPLETED' ? 'bg-emerald-500' : 'bg-gray-300'} ring-4 ring-white`}></div>
                        <p className="text-sm text-gray-700">{item.status === 'COMPLETED' ? '✓ Response completed' : 'Agent working...'}</p>
                      </li>
                    </ul>
                  </div>
                </div>
                
                <div className="space-y-4">
                  <div className="bg-gray-50 rounded-lg p-4 border border-gray-100">
                    <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
                      <Cpu className="w-4 h-4 text-gray-500" /> Advanced Details
                    </h4>
                    <dl className="space-y-2 text-xs">
                      <div className="flex justify-between">
                        <dt className="text-gray-500">Model</dt>
                        <dd className="font-medium text-gray-900">gemini-3.5-pro</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-gray-500">Started</dt>
                        <dd className="font-medium text-gray-900">{new Date(item.started_at).toLocaleTimeString()}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-gray-500">Tools</dt>
                        <dd className="font-medium text-gray-900">{item.tool_call_count || 0}</dd>
                      </div>
                      <div className="pt-2 mt-2 border-t border-gray-200">
                        <details>
                          <summary className="text-blue-600 cursor-pointer font-medium hover:underline">View Raw JSON</summary>
                          <pre className="mt-2 bg-white border border-gray-200 p-2 rounded overflow-x-auto text-[10px] text-gray-700">
                            {JSON.stringify(item, null, 2)}
                          </pre>
                        </details>
                      </div>
                    </dl>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
