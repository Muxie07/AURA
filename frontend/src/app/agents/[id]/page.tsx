'use client';
import { fetchApi } from '../../lib/api';
import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Card, PageHeader, LoadingState, StatusBadge, Button } from '../../components/ui';
import { Bot, ArrowLeft, Clock, Activity, ChevronDown, ChevronRight, TerminalSquare, Zap, Cpu, Wrench } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export default function AgentRunDetail() {
  const params = useParams();
  const id = params?.id as string;
  const router = useRouter();
  
  const [run, setRun] = useState<any>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedEvent, setExpandedEvent] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'trace' | 'timeline' | 'audit'>('trace');

  useEffect(() => {
    let abortController = new AbortController();
    let isMounted = true;
    let streamRetryCount = 0;

    async function fetchRunDetails() {
      if (!id) return;
      try {
        const runRes = await fetchApi(`/runs/${id}`);
        if (runRes.ok) {
          const runData = await runRes.json();
          setRun(runData);
        }
      } catch (err) {
        console.error("Failed to fetch run details", err);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    async function startStream() {
      if (!id || !isMounted) return;
      try {
        const response = await fetchApi(`/runs/${id}/stream`, { signal: abortController.signal });
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        if (!reader) return;
        
        let buffer = "";
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop() || "";
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.slice(6);
                    try {
                        const data = JSON.parse(dataStr);
                        if (data.event_type === 'STREAM_END') {
                            setRun((prev: any) => ({ ...prev, status: data.status }));
                            abortController.abort();
                            return; // end stream gracefully
                        } else {
                            setEvents((prev) => {
                                const newEvents = [...prev];
                                if (!newEvents.find(e => e.id === data.id)) {
                                    newEvents.push(data);
                                }
                                return newEvents;
                            });
                        }
                    } catch(e) {}
                }
            }
        }
        
        // If we broke out of loop without STREAM_END and are still mounted, we should reconnect
        if (isMounted && !abortController.signal.aborted) {
            throw new Error("Stream ended unexpectedly");
        }
      } catch (err: any) {
        if (err.name !== 'AbortError' && isMounted) {
            console.error("Stream failed, reconnecting...", err);
            streamRetryCount++;
            if (streamRetryCount < 10) {
                setTimeout(startStream, Math.min(1000 * Math.pow(2, streamRetryCount), 30000));
            }
        }
      }
    }
    
    fetchRunDetails();
    startStream();

    return () => {
      isMounted = false;
      abortController.abort();
    };
  }, [id]);

  if (loading) return <div className="p-8"><LoadingState message="Loading agent details..." /></div>;
  if (!run) return (
    <div className="p-8 text-center">
      <h2 className="text-xl font-bold text-gray-900">Agent Run Not Found</h2>
      <p className="mt-2 text-gray-500">The agent run you are looking for does not exist or you do not have permission.</p>
      <Button variant="primary" className="mt-4" onClick={() => router.push('/agents')}>
        Back to Agents
      </Button>
    </div>
  );

  return (
    <div className="space-y-6 h-full flex flex-col pb-8">
      <div className="flex items-center gap-4 text-sm text-gray-500 hover:text-gray-900 cursor-pointer w-fit" onClick={() => router.push('/agents')}>
        <ArrowLeft className="w-4 h-4" /> Back to Agents
      </div>

      <PageHeader 
        title={
          <div className="flex items-center gap-3">
            <Bot className="w-8 h-8 text-blue-600 bg-blue-100 p-1.5 rounded-lg" />
            <span className="font-mono text-2xl">{run.run_id}</span>
            <StatusBadge status={run.status} className="ml-2 text-sm" />
          </div>
        }
        description="Detailed telemetry, state transitions, and tool executions for this autonomous run."
      />

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="col-span-1 md:col-span-4 flex flex-row justify-between items-center bg-white p-4 shadow-sm rounded-lg border border-gray-200">
           <div className="flex items-center gap-3">
             <div className="p-3 bg-indigo-50 text-indigo-600 rounded-full">
               <Clock className="w-5 h-5" />
             </div>
             <div>
               <p className="text-sm text-gray-500 font-medium">Latency</p>
               <p className="text-lg font-bold text-gray-900">{run.latency_ms != null ? `${run.latency_ms} ms` : 'N/A'}</p>
             </div>
           </div>
           
           <div className="flex items-center gap-3">
             <div className="p-3 bg-green-50 text-green-600 rounded-full">
               <Cpu className="w-5 h-5" />
             </div>
             <div>
               <p className="text-sm text-gray-500 font-medium">Tokens (In / Out)</p>
               <p className="text-lg font-bold text-gray-900">
                 {run.total_tokens_input ?? 0} / {run.total_tokens_output ?? 0}
               </p>
             </div>
           </div>

           <div className="flex items-center gap-3">
             <div className="p-3 bg-yellow-50 text-yellow-600 rounded-full">
               <Wrench className="w-5 h-5" />
             </div>
             <div>
               <p className="text-sm text-gray-500 font-medium">Tools Called</p>
               <p className="text-lg font-bold text-gray-900">{run.tool_call_count ?? 0}</p>
             </div>
           </div>
        </Card>

        <Card className="col-span-1 h-fit">
          <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4" /> Run Overview
          </h3>
          <dl className="space-y-4 text-sm">
            <div>
              <dt className="text-gray-500">Status</dt>
              <dd className="mt-1 font-medium text-gray-900"><StatusBadge status={run.status} /></dd>
            </div>
            <div>
              <dt className="text-gray-500">Started At</dt>
              <dd className="mt-1 font-medium text-gray-900">
                {run.started_at ? new Date(run.started_at).toLocaleString() : 'N/A'}
                {run.started_at && <span className="text-xs text-gray-400 block">{formatDistanceToNow(new Date(run.started_at))} ago</span>}
              </dd>
            </div>
            {run.completed_at && (
              <div>
                <dt className="text-gray-500">Completed At</dt>
                <dd className="mt-1 font-medium text-gray-900">
                  {new Date(run.completed_at).toLocaleString()}
                </dd>
              </div>
            )}
            <div>
              <dt className="text-gray-500">Total Events</dt>
              <dd className="mt-1 font-medium text-gray-900">{events.length}</dd>
            </div>
          </dl>
        </Card>

        <Card className="col-span-1 md:col-span-3 flex flex-col">
          <div className="border-b border-gray-200 mb-4 flex gap-4">
            <button 
                onClick={() => setActiveTab('trace')}
                className={`py-2 px-1 border-b-2 text-sm font-medium ${activeTab === 'trace' ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
            >
                Execution Trace
            </button>
            <button 
                onClick={() => setActiveTab('timeline')}
                className={`py-2 px-1 border-b-2 text-sm font-medium ${activeTab === 'timeline' ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
            >
                Timeline
            </button>
            <button 
                onClick={() => setActiveTab('audit')}
                className={`py-2 px-1 border-b-2 text-sm font-medium ${activeTab === 'audit' ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
            >
                Audit Log
            </button>
          </div>
          
          <div className="flex-1 bg-gray-50 rounded-lg border border-gray-200 overflow-hidden flex flex-col min-h-[500px]">
            {events.length === 0 ? (
              <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">
                No events recorded for this run.
              </div>
            ) : (
              <div className="overflow-y-auto max-h-[600px]">
                  {activeTab === 'trace' && (
                      <ul className="divide-y divide-gray-200">
                        {events.map((event, idx) => (
                          <li key={idx} className="bg-white">
                            <div 
                              className="px-4 py-3 flex items-start gap-3 hover:bg-gray-50 cursor-pointer"
                              onClick={() => setExpandedEvent(expandedEvent === String(idx) ? null : String(idx))}
                            >
                              <div className="mt-0.5 text-gray-400">
                                {expandedEvent === String(idx) ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex justify-between items-center mb-1">
                                  <span className="text-sm font-semibold text-gray-900">{event.event_type}</span>
                                  <span className="text-xs text-gray-500 flex items-center gap-1">
                                    {event.duration_ms != null && <span className="font-mono bg-gray-100 px-1 py-0.5 rounded text-gray-600 mr-2">{event.duration_ms} ms</span>}
                                    <Clock className="w-3 h-3" /> {new Date(event.timestamp).toLocaleTimeString()}
                                  </span>
                                </div>
                                <p className="text-sm text-gray-600 truncate">{event.component ? `[${event.component}]` : ''} {event.message || "Execution event recorded"}</p>
                              </div>
                            </div>
                            {expandedEvent === String(idx) && (
                              <div className="px-4 py-3 bg-gray-900 text-gray-100 text-xs overflow-x-auto border-t border-gray-200">
                                <pre className="font-mono">
                                  {JSON.stringify(event.metadata || event, null, 2)}
                                </pre>
                              </div>
                            )}
                          </li>
                        ))}
                      </ul>
                  )}
                  {activeTab === 'timeline' && (
                      <div className="p-6 relative">
                        <div className="absolute left-9 top-0 bottom-0 w-0.5 bg-gray-200"></div>
                        <ul className="space-y-6 relative">
                            {events.map((event, idx) => (
                                <li key={idx} className="flex gap-4 items-start">
                                    <div className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 border-4 border-white flex items-center justify-center z-10 shadow-sm">
                                        <div className="w-2 h-2 rounded-full bg-blue-600"></div>
                                    </div>
                                    <div className="flex-1 bg-white p-4 rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
                                        <div className="flex justify-between mb-1">
                                            <span className="font-medium text-gray-900 text-sm">{event.event_type}</span>
                                            <span className="text-xs text-gray-500">{new Date(event.timestamp).toLocaleTimeString()}</span>
                                        </div>
                                        <div className="text-xs text-gray-600">
                                            <span className="font-semibold">{event.component}</span>
                                            {event.duration_ms != null && <span className="ml-2 text-indigo-600 font-medium">took {event.duration_ms}ms</span>}
                                        </div>
                                    </div>
                                </li>
                            ))}
                        </ul>
                      </div>
                  )}
                  {activeTab === 'audit' && (
                      <div className="p-0">
                          <table className="min-w-full divide-y divide-gray-200">
                              <thead className="bg-gray-50">
                                  <tr>
                                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Timestamp</th>
                                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Event</th>
                                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Component</th>
                                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Duration</th>
                                  </tr>
                              </thead>
                              <tbody className="bg-white divide-y divide-gray-200 text-sm">
                                  {events.map((event, idx) => (
                                      <tr key={idx} className="hover:bg-gray-50">
                                          <td className="px-4 py-2 whitespace-nowrap text-gray-500 font-mono text-xs">{new Date(event.timestamp).toISOString()}</td>
                                          <td className="px-4 py-2 whitespace-nowrap font-medium text-gray-900">{event.event_type}</td>
                                          <td className="px-4 py-2 whitespace-nowrap text-gray-600">{event.component}</td>
                                          <td className="px-4 py-2 whitespace-nowrap text-right text-gray-500 font-mono">
                                              {event.duration_ms != null ? `${event.duration_ms}ms` : '-'}
                                          </td>
                                      </tr>
                                  ))}
                              </tbody>
                          </table>
                      </div>
                  )}
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
