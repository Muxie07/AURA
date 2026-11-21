import os

app_dir = 'frontend/src/app'

pages = {
    "agents": ("AI Agents", "Manage and monitor autonomous AI agents.", "agent/runs"),
    "conversations": ("Conversations", "View and interact with agent conversations.", "conversations"),
    "knowledge": ("Knowledge Base", "Manage RAG documents and data sources.", "knowledge-bases"),
    "tools": ("Tools Registry", "Registered tools available for agent execution.", None),
    "approvals": ("Approvals", "Pending human-in-the-loop approval requests.", "agent/approvals"),
    "observability": ("Observability", "Traces, metrics, and detailed agent logs.", None),
    "settings": ("Settings", "System configuration and API keys.", None),
}

for route, (title, desc, endpoint) in pages.items():
    is_none = str(endpoint is None).lower()
    fetch_logic = f"""
      if ({is_none}) {{
        setLoading(false);
        return;
      }}
      try {{
        const token = localStorage.getItem('token') || 'test-token';
        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
        const res = await fetch(`${{API_URL}}/{endpoint}`, {{
          headers: {{ 'Authorization': `Bearer ${{token}}` }}
        }});
        if (res.ok) {{
          const json = await res.json();
          if (Array.isArray(json)) setData(json);
          else if (json.runs) setData(json.runs);
          else if (json.approvals) setData(json.approvals);
          else if (json.conversations) setData(json.conversations);
          else setData([json]);
        }}
      }} catch (err) {{
        console.error(err);
      }} finally {{
        setLoading(false);
      }}
    """
    empty_logic = "This section is under construction." if endpoint is None else "No records found."
    content = f"""'use client';
import {{ useEffect, useState }} from 'react';

export default function Page() {{
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {{
    async function fetchData() {{{fetch_logic}}}
    fetchData();
  }}, []);

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
        <p className="mt-2 text-sm text-gray-700">{desc}</p>
      </div>

      <div className="bg-white shadow rounded-lg border border-gray-200">
        <div className="p-6">
          {{loading ? (
            <div className="animate-pulse flex space-x-4">
              <div className="flex-1 space-y-4 py-1">
                <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                <div className="space-y-2">
                  <div className="h-4 bg-gray-200 rounded"></div>
                  <div className="h-4 bg-gray-200 rounded w-5/6"></div>
                </div>
              </div>
            </div>
          ) : {is_none} || data.length === 0 ? (
            <div className="text-center py-12">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={{2}} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
              </svg>
              <h3 className="mt-2 text-sm font-semibold text-gray-900">No data available</h3>
              <p className="mt-1 text-sm text-gray-500">{empty_logic}</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-300">
                <thead>
                  <tr>
                    <th className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900">ID / Info</th>
                    <th className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {{data.map((item, idx) => (
                    <tr key={{item.id || item.run_id || idx}}>
                      <td className="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900">
                        {{item.id || item.run_id || 'Item ' + idx}}
                      </td>
                      <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                        <pre className="text-xs truncate max-w-md">{{JSON.stringify(item)}}</pre>
                      </td>
                    </tr>
                  ))}}
                </tbody>
              </table>
            </div>
          )}}
        </div>
      </div>
    </div>
  );
}}
"""
    with open(os.path.join(app_dir, route, 'page.tsx'), 'w', encoding='utf-8') as f:
        f.write(content)

print("Pages rewritten.")
