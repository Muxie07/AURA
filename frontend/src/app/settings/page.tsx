'use client';
import { fetchApi } from '../lib/api';
import { useEffect, useState } from 'react';

type SettingsResponse = {
  organization: { id: string; name: string };
  environment: { aura_env?: string; llm_provider?: string; llm_model?: string; llm_fallback_model?: string; llm_embedding_model?: string; llm_temperature?: number };
  user_settings?: { default_model?: string; default_temperature?: number | string };
};

export default function SettingsPage() {
  const [data, setData] = useState<SettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Form states (user_settings mapped)
  const [defaultModel, setDefaultModel] = useState('');
  const [defaultTemperature, setDefaultTemperature] = useState('0.7');

  useEffect(() => {
    async function load() {
      try {
        const res = await fetchApi('/settings');
        if (res.ok) {
          const json = await res.json();
          setData(json);
          setDefaultModel(json.user_settings?.default_model || json.environment?.llm_model || '');
          setDefaultTemperature(json.user_settings?.default_temperature || json.environment?.llm_temperature || '0.7');
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        setLoadError(message);
        console.error('Settings request failed:', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      await fetchApi('/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          settings: {
            default_model: defaultModel,
            default_temperature: parseFloat(defaultTemperature),
          }
        })
      });
      alert('Settings saved successfully!');
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : String(e));
    }
    setSaving(false);
  };

  if (loading) {
    return <div className="p-8">Loading settings...</div>;
  }

  if (!data) {
    return <div className="p-8 text-red-700" role="alert">Settings request failed: {loadError || "No response from the API."}</div>;
  }

  return (
    <div className="p-8 max-w-4xl space-y-8 h-full overflow-y-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="mt-2 text-sm text-gray-700">System configuration and agent defaults.</p>
      </div>

      <div className="bg-white shadow rounded-lg border border-gray-200">
        <div className="px-4 py-5 sm:p-6 space-y-6">
          
          {/* Environment/System Status */}
          <div>
            <h3 className="text-lg leading-6 font-medium text-gray-900">System Status</h3>
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-gray-50 p-4 rounded-md">
                <p className="text-sm font-medium text-gray-500">Database</p>
                <p className="mt-1 flex items-center text-sm font-semibold text-green-600">
                  <span className="w-2 h-2 mr-2 bg-green-500 rounded-full"></span> Connected
                </p>
              </div>
              <div className="bg-gray-50 p-4 rounded-md">
                <p className="text-sm font-medium text-gray-500">Redis Cache</p>
                <p className="mt-1 flex items-center text-sm font-semibold text-green-600">
                  <span className="w-2 h-2 mr-2 bg-green-500 rounded-full"></span> Connected
                </p>
              </div>
              <div className="bg-gray-50 p-4 rounded-md">
                <p className="text-sm font-medium text-gray-500">Environment</p>
                <p className="mt-1 text-sm font-semibold text-gray-900">{data.environment.aura_env}</p>
              </div>
            </div>
          </div>

          <hr />

          {/* AI Configuration */}
          <div>
            <h3 className="text-lg leading-6 font-medium text-gray-900">AI / LLM Configuration</h3>
            <p className="text-sm text-gray-500 mb-4">Core provider settings are managed securely by the server environment.</p>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700">Provider</label>
                <input disabled type="text" value={data.environment.llm_provider || 'Not configured'} className="mt-1 block w-full bg-gray-100 rounded-md border-gray-300 shadow-sm sm:text-sm text-gray-500 cursor-not-allowed" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Active Model</label>
                <input disabled type="text" value={data.environment.llm_model || 'Not configured'} className="mt-1 block w-full bg-gray-100 rounded-md border-gray-300 shadow-sm sm:text-sm text-gray-500 cursor-not-allowed" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Fallback Model</label>
                <input disabled type="text" value={data.environment.llm_fallback_model || 'None'} className="mt-1 block w-full bg-gray-100 rounded-md border-gray-300 shadow-sm sm:text-sm text-gray-500 cursor-not-allowed" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Embedding Model</label>
                <input disabled type="text" value={data.environment.llm_embedding_model || 'None'} className="mt-1 block w-full bg-gray-100 rounded-md border-gray-300 shadow-sm sm:text-sm text-gray-500 cursor-not-allowed" />
              </div>
            </div>
          </div>

          <hr />

          {/* Agent Defaults */}
          <div>
            <h3 className="text-lg leading-6 font-medium text-gray-900">Agent Defaults</h3>
            <p className="text-sm text-gray-500 mb-4">Override the default behavior for new agent executions.</p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700">Default Model</label>
                <input type="text" value={defaultModel} onChange={(e) => setDefaultModel(e.target.value)} className="mt-1 block w-full rounded-md border border-gray-300 shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm" placeholder="e.g. gpt-4o" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Default Temperature</label>
                <input type="number" step="0.1" value={defaultTemperature} onChange={(e) => setDefaultTemperature(e.target.value)} className="mt-1 block w-full rounded-md border border-gray-300 shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm" />
              </div>
            </div>
            
            {saveError && <p className="mt-4 text-sm text-red-700" role="alert">Save failed: {saveError}</p>}
            <div className="mt-6 flex justify-end">
              <button 
                onClick={handleSave} 
                disabled={saving}
                className="bg-blue-600 border border-transparent rounded-md shadow-sm py-2 px-4 inline-flex justify-center text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50">
                {saving ? 'Saving...' : 'Save Settings'}
              </button>
            </div>
          </div>

          <hr />

          {/* Security */}
          <div>
            <h3 className="text-lg leading-6 font-medium text-gray-900">Security & Organization</h3>
            <div className="mt-4 bg-gray-50 p-4 rounded-md space-y-2">
              <p className="text-sm text-gray-700"><span className="font-semibold">Tenant ID:</span> {data.organization.id}</p>
              <p className="text-sm text-gray-700"><span className="font-semibold">Tenant Name:</span> {data.organization.name}</p>
              <p className="text-sm text-gray-500 italic mt-2">API secrets are never exposed to the frontend.</p>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
