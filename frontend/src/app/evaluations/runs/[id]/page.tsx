"use client";
import { useEffect, useState } from 'react';
import { APIError, fetchApi } from '../../../lib/api';
import Link from 'next/link';
import { CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/solid';

type EvaluationResult = {
  example_id: string; input_prompt?: string; expected_tools?: string[]; actual_output: string | null; passed: boolean;
  tools_used: string[]; error_message: string | null; latency_ms: number;
};
type RunDetails = {
  run: { id: string; model: string; status: string; success_rate: number; sample_count: number; avg_latency_ms: number; expected_count: number };
  results: EvaluationResult[];
};

export default function RunDetailsPage({ params }: { params: { id: string } }) {
  const [data, setData] = useState<RunDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const load = async () => {
      try {
        const response = await fetchApi('/eval/runs/' + params.id);
        const next = await response.json() as RunDetails;
        if (stopped) return;
        setData(next);
        setLoadError(null);
        setIsLoading(false);
        if (next.run.status === 'pending' || next.run.status === 'running') timer = setTimeout(load, 1500);
      } catch (error) {
        if (!stopped) {
          setLoadError(error instanceof Error ? error.message : String(error));
          setIsLoading(false);
          if (!(error instanceof APIError) || error.status === 0 || error.status >= 500) {
            timer = setTimeout(load, 3000);
          }
        }
      }
    };
    void load();
    return () => { stopped = true; if (timer) clearTimeout(timer); };
  }, [params.id]);

  if (isLoading) return <div className="p-8">Loading run details...</div>;
  if (!data) return <div className="p-8 text-red-700" role="alert">Failed to load evaluation run: {loadError || 'No response.'}</div>;

  const run = data.run;
  const results: EvaluationResult[] = data.results || [];
  const active = run.status === 'pending' || run.status === 'running';

  return (
    <div className="p-8 max-w-7xl mx-auto h-full overflow-y-auto">
      <div className="mb-6 flex justify-between items-start">
        <div>
          <Link href="/evaluations" className="text-sm text-blue-600 hover:underline mb-2 inline-block">← Back to Evaluations</Link>
          <h1 className="text-2xl font-bold text-gray-900">Run Details</h1>
          <p className="text-sm text-gray-500 mt-1">Model: <span className="font-semibold text-gray-800">{run.model}</span> | Results: {results.length} / {run.expected_count}</p>
          <p className={run.status === 'failed' ? 'mt-2 text-sm font-medium text-red-700' : active ? 'mt-2 text-sm font-medium text-blue-700' : 'mt-2 text-sm font-medium text-green-700'}>Status: {run.status}</p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold" style={{ color: run.success_rate >= 0.8 ? 'green' : 'red' }}>{(run.success_rate * 100).toFixed(1)}% Pass</p>
          <p className="text-sm text-gray-500 mt-1">Avg Latency: {Math.round(run.avg_latency_ms)}ms</p>
        </div>
      </div>
      {active && <p className="mb-4 text-sm text-blue-700" role="status">Evaluation is running. Persisted results appear as each example finishes.</p>}
      {loadError && <p className="mb-4 text-sm text-red-700" role="alert">Could not refresh run status: {loadError}</p>}
      {run.status === 'failed' && <p className="mb-4 rounded bg-red-50 p-3 text-sm text-red-800">The evaluation run failed. Persisted example results are shown below.</p>}
      <div className="bg-white shadow rounded-lg border border-gray-200 overflow-hidden">
        {results.length === 0 ? <p className="p-4 text-sm text-gray-500">{active ? 'No example results persisted yet.' : 'This run has no persisted example results.'}</p> : (
          <ul className="divide-y divide-gray-200">
            {results.map((result, idx) => (
              <li key={result.example_id} className="p-4 sm:px-6 hover:bg-gray-50">
                <div className="flex flex-col space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      {result.passed ? <CheckCircleIcon className="w-5 h-5 text-green-500" /> : <XCircleIcon className="w-5 h-5 text-red-500" />}
                      <span className="text-sm font-semibold text-gray-900">Result {idx + 1}: {result.passed ? 'Passed' : 'Failed'}</span>
                    </div>
                    <span className="text-xs text-gray-400">Latency: {result.latency_ms}ms</span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div><h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Actual Output</h4><div className="mt-1 bg-gray-100 p-3 rounded-md text-sm text-gray-800 font-mono h-32 overflow-y-auto whitespace-pre-wrap">{result.actual_output || 'No output.'}</div></div>
                    <div><h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Analysis</h4><div className="mt-1 flex flex-col space-y-2">
                      <p className="text-sm"><span className="font-medium text-gray-700">Tools Used: </span>{result.tools_used?.length ? result.tools_used.join(', ') : 'None'}</p>
                      {!result.passed && <div className="bg-red-50 text-red-700 p-2 rounded-md text-sm border border-red-200"><strong>Failure Reason: </strong>{result.error_message || 'The example failed without an error message.'}</div>}
                    </div></div>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
