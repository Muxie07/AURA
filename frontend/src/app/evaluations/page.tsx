"use client";

import { useCallback, useEffect, useState } from 'react';
import { APIError, fetchApi } from '../lib/api';
import Link from 'next/link';
import { PlayIcon, ArrowTrendingUpIcon } from '@heroicons/react/24/outline';

type EvaluationDataset = { id: string; name: string; description?: string; category: string; version: number };
type EvaluationRun = { id: string; dataset_id: string; model: string; provider: string; status: string; success_rate: number; avg_latency_ms: number; sample_count: number; completed_at: string | null };
type EvaluationSettings = { environment?: { aura_env?: string; llm_provider?: string; llm_model?: string }; organization?: { id: string; name: string }; user_settings?: Record<string, unknown> };
type ForecastResponse = { has_sufficient_data: boolean; message?: string; forecast: { next_24h: { expected_volume: number }; failures: { current_rate: number; risk: string }; latency: { current_ms: number; trend: string }; cost: { projected_7d_usd: number } } };
type RunDetailsResponse = { run: { id: string; model: string; status: string; success_rate: number; sample_count: number; avg_latency_ms: number; expected_count: number }; results: { example_id: string; actual_output: string | null; passed: boolean; tools_used: string[]; error_message: string | null; latency_ms: number }[] };

export default function EvaluationsPage() {
  const [datasets, setDatasets] = useState<EvaluationDataset[]>([]);
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [settings, setSettings] = useState<EvaluationSettings | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Form states for Run Evaluation
  const [selectedDataset, setSelectedDataset] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [selectedProvider, setSelectedProvider] = useState('');
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [activeRunStatus, setActiveRunStatus] = useState<string | null>(null);
  const [activeResultCount, setActiveResultCount] = useState(0);
  const [runError, setRunError] = useState<string | null>(null);

  const loadEval = useCallback(async () => {
    try {
      const [dRes, rRes, fRes, sRes] = await Promise.all([
        fetchApi('/eval/datasets').catch(() => null),
        fetchApi('/eval/runs').catch(() => null),
        fetchApi('/forecasting/').catch(() => null),
        fetchApi('/settings').catch(() => null)
      ]);

      if (dRes?.ok) {
        const dData = await dRes.json();
        setDatasets(dData.examples || []);
        if (dData.examples?.length > 0) setSelectedDataset(dData.examples[0].id);
      }
      if (rRes?.ok) {
        const rData = await rRes.json();
        setRuns(rData.runs || []);
      }
      if (fRes?.ok) {
        const fData = await fRes.json();
        setForecast(fData);
      }
      if (sRes?.ok) {
        const sData = await sRes.json();
        setSettings(sData);
        setSelectedProvider(sData.environment?.llm_provider || '');
        setSelectedModel(sData.environment?.llm_model || '');
      }
    } catch (e) {
      console.error(e);
    }
    setIsLoading(false);
  }, []);

  useEffect(() => { const timer = window.setTimeout(() => { void loadEval(); }, 0); return () => window.clearTimeout(timer); }, [loadEval]);
  useEffect(() => {
    if (!activeRunId) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const poll = async () => {
      try {
        const response = await fetchApi('/eval/runs/' + activeRunId);
        const payload = await response.json() as RunDetailsResponse;
        if (stopped) return;
        setActiveRunStatus(payload.run.status);
        setActiveResultCount(payload.results.length);
        setRunError(null);
        if (payload.run.status === 'completed' || payload.run.status === 'failed') {
          setIsEvaluating(false);
          if (payload.results.length > 0) await loadEval();
          return;
        }
      } catch (error) {
        if (!stopped) {
          setRunError(error instanceof Error ? error.message : String(error));
          if (error instanceof APIError && error.status >= 400 && error.status < 500) {
            setIsEvaluating(false);
            setActiveRunId(null);
          } else {
            timer = setTimeout(poll, 3000);
          }
        }
        return;
      }
      if (!stopped) timer = setTimeout(poll, 1500);
    };
    void poll();
    return () => { stopped = true; if (timer) clearTimeout(timer); };
  }, [activeRunId, loadEval]);

  const handleRunEvaluation = async () => {
    if (!selectedDataset) return;
    setIsEvaluating(true);
    setActiveRunId(null);
    setRunError(null);
    setActiveRunStatus('pending');
    setActiveResultCount(0);
    try {
      const res = await fetchApi('/eval/runs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dataset_id: selectedDataset,
          model: selectedModel,
          provider: selectedProvider
        })
      });
      const run = await res.json() as { run_id: string; status: string };
      setActiveRunId(run.run_id);
      setActiveRunStatus(run.status || 'pending');
    } catch (error) {
      setRunError(error instanceof Error ? error.message : String(error));
      setIsEvaluating(false);
    }
  };

  if (isLoading) {
    return <div className="p-8">Loading evaluations...</div>;
  }

  // Derived metrics
  // Group by model
  const modelStats: Record<string, { runs: number, avgPass: number, avgLat: number }> = {};
  runs.filter(r => r.status === 'completed' && r.sample_count > 0).forEach(r => {
    if (!modelStats[r.model]) modelStats[r.model] = { runs: 0, avgPass: 0, avgLat: 0 };
    modelStats[r.model].runs++;
    modelStats[r.model].avgPass += r.success_rate;
    modelStats[r.model].avgLat += r.avg_latency_ms;
  });

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 h-full overflow-y-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Agent Evaluations</h1>
          <p className="text-sm text-gray-500 mt-1">Real execution benchmarks and forecasting metrics.</p>
        </div>
      </div>

      {/* Forecasting / Top Metrics */}
      {forecast && forecast.has_sufficient_data ? (
        <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
          <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
            <ArrowTrendingUpIcon className="w-5 h-5 mr-2 text-blue-500" /> 
            Active Telemetry & Forecast
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
             <div className="bg-gray-50 p-4 rounded-md">
                <p className="text-sm text-gray-500">24h Execution Volume</p>
                <p className="text-2xl font-semibold text-gray-900">{forecast.forecast.next_24h.expected_volume}</p>
             </div>
             <div className="bg-gray-50 p-4 rounded-md">
                <p className="text-sm text-gray-500">Current Failure Rate</p>
                <p className="text-2xl font-semibold text-gray-900">{(forecast.forecast.failures.current_rate * 100).toFixed(1)}%</p>
                <p className={`text-xs mt-1 ${forecast.forecast.failures.risk === 'high' ? 'text-red-500' : 'text-green-500'}`}>
                  Risk: {forecast.forecast.failures.risk.toUpperCase()}
                </p>
             </div>
             <div className="bg-gray-50 p-4 rounded-md">
                <p className="text-sm text-gray-500">Avg Latency (24h)</p>
                <p className="text-2xl font-semibold text-gray-900">{Math.round(forecast.forecast.latency.current_ms)}ms</p>
                <p className="text-xs mt-1 text-gray-500">Trend: {forecast.forecast.latency.trend}</p>
             </div>
             <div className="bg-gray-50 p-4 rounded-md">
                <p className="text-sm text-gray-500">Est. Cost (7d Projection)</p>
                <p className="text-2xl font-semibold text-gray-900">${forecast.forecast.cost.projected_7d_usd.toFixed(2)}</p>
             </div>
          </div>
        </div>
      ) : (
        <div className="bg-yellow-50 p-6 rounded-lg border border-yellow-200">
          <p className="text-yellow-700">{forecast?.message || "Insufficient historical data for forecasting."}</p>
        </div>
      )}

      {/* Run Evaluation Box */}
      <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
        <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
          <PlayIcon className="w-5 h-5 mr-2 text-green-500" />
          Run Evaluation (Actual Execution)
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 items-end">
          <div>
             <label className="block text-sm font-medium text-gray-700">Dataset</label>
             <select className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2 border text-gray-900 bg-white" value={selectedDataset} onChange={(e)=>setSelectedDataset(e.target.value)}>
                {datasets.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
             </select>
          </div>
          <div>
             <label className="block text-sm font-medium text-gray-700">Provider</label>
             {settings?.environment?.llm_provider ? (
               <input disabled type="text" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2 border text-gray-900 bg-gray-100 cursor-not-allowed" value={selectedProvider} />
             ) : (
               <input type="text" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2 border text-red-500 bg-red-50" value="Not configured" disabled />
             )}
          </div>
          <div>
             <label className="block text-sm font-medium text-gray-700">Model</label>
             {settings?.environment?.llm_model ? (
               <input disabled type="text" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2 border text-gray-900 bg-gray-100 cursor-not-allowed" value={selectedModel} />
             ) : (
               <input type="text" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2 border text-red-500 bg-red-50" value="Not configured" disabled />
             )}
          </div>
          <div>
             <button onClick={handleRunEvaluation} disabled={isEvaluating || !settings?.environment?.llm_provider} className="w-full bg-blue-600 text-white font-medium p-2 rounded-md hover:bg-blue-700 disabled:opacity-50">
               {isEvaluating ? 'Starting...' : 'Run Benchmark'}
             </button>
          </div>
        </div>
        {(isEvaluating || runError || activeRunStatus === 'failed') && <p className="mt-4 rounded-md bg-blue-50 p-3 text-sm text-blue-800" role="status">
          {runError ? 'Evaluation request failed: ' + runError : 'Evaluation ' + (activeRunStatus || 'pending') + ' (run ' + (activeRunId || 'starting') + '); ' + activeResultCount + ' results persisted.'}
        </p>}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        
        {/* Datasets */}
        <div>
          <h3 className="text-lg font-medium text-gray-900 mb-4">Golden Datasets</h3>
          <div className="bg-white shadow rounded-lg border border-gray-200 divide-y divide-gray-200">
            {datasets.length === 0 ? <p className="p-4 text-sm text-gray-500">No datasets found.</p> : datasets.map(d => (
              <div key={d.id} className="p-4 hover:bg-gray-50">
                <div className="flex justify-between items-center">
                   <div>
                     <Link href={`/evaluations/datasets/${d.id}`} className="text-sm font-medium text-blue-600 hover:underline">{d.name}</Link>
                     <p className="text-xs text-gray-500 mt-1">{d.description}</p>
                   </div>
                   <div className="text-right">
                     <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                       v{d.version}
                     </span>
                   </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Real Model Benchmarks */}
        <div>
          <h3 className="text-lg font-medium text-gray-900 mb-4">Model Performance (Actuals)</h3>
          <div className="bg-white shadow rounded-lg border border-gray-200 divide-y divide-gray-200">
            {Object.keys(modelStats).length === 0 ? (
               <p className="p-4 text-sm text-gray-500">No benchmark runs recorded. Run an evaluation to generate real data.</p>
            ) : Object.entries(modelStats).map(([model, stat]) => (
               <div key={model} className="p-4">
                  <div className="flex justify-between items-center mb-2">
                     <span className="text-sm font-medium text-gray-900">
                       {model} 
                       {model === 'mock' && <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">TEST / MOCK EXECUTION</span>}
                     </span>
                     <span className="text-sm font-bold text-gray-900">{((stat.avgPass / stat.runs) * 100).toFixed(1)}% Pass Rate</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2.5">
                     <div className="bg-blue-600 h-2.5 rounded-full" style={{ width: `${(stat.avgPass / stat.runs) * 100}%` }}></div>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">{stat.runs} runs recorded • Avg Latency: {Math.round(stat.avgLat / stat.runs)}ms</p>
               </div>
            ))}
          </div>
        </div>

      </div>

      {/* Recent Evaluation Runs */}
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-4">Recent Evaluation Runs</h3>
        <div className="bg-white shadow rounded-lg border border-gray-200 overflow-hidden">
          {runs.length === 0 ? (
            <p className="p-4 text-sm text-gray-500">No recent runs.</p>
          ) : (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Started</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Samples</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Pass Rate</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Avg Latency</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">View</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {runs.map(r => (
                  <tr key={r.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{new Date(r.completed_at || '').toLocaleString()}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{r.model} {r.model === 'mock' && <span className="text-yellow-600 text-xs ml-1">(Mock)</span>}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{r.sample_count}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                       <span className={r.success_rate >= 0.8 ? 'text-green-600' : 'text-red-600'}>{(r.success_rate * 100).toFixed(1)}%</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{Math.round(r.avg_latency_ms)}ms</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-blue-600 hover:underline">
                      <Link href={`/evaluations/runs/${r.id}`}>Details</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
