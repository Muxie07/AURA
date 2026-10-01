"use client";
import { useEffect, useState } from 'react';
import { fetchApi } from '../../../lib/api';
import Link from 'next/link';

export default function DatasetDetailsPage({ params }: { params: { id: string } }) {
  const [data, setData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetchApi(`/eval/datasets/${params.id}`);
        if (res.ok) {
          setData(await res.json());
        }
      } catch (e) {
        console.error(e);
      }
      setIsLoading(false);
    }
    load();
  }, [params.id]);

  if (isLoading) return <div className="p-8">Loading dataset details...</div>;
  if (!data) return <div className="p-8">Failed to load dataset.</div>;

  return (
    <div className="p-8 max-w-7xl mx-auto h-full overflow-y-auto">
      <div className="mb-6">
        <Link href="/evaluations" className="text-sm text-blue-600 hover:underline mb-2 inline-block">? Back to Evaluations</Link>
        <h1 className="text-2xl font-bold text-gray-900">{data.dataset.name}</h1>
        <p className="text-sm text-gray-500 mt-1">{data.dataset.description}</p>
      </div>

      <div className="bg-white shadow rounded-lg border border-gray-200 overflow-hidden">
        <div className="px-4 py-5 border-b border-gray-200 sm:px-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900">Evaluation Cases ({data.examples.length})</h3>
        </div>
        <ul className="divide-y divide-gray-200">
          {data.examples.map((ex: any, idx: number) => (
            <li key={ex.id} className="p-4 sm:px-6 hover:bg-gray-50">
              <div className="flex flex-col space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-gray-900">Case {idx + 1} {ex.is_attack && <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">Security Attack</span>}</span>
                  <span className="text-xs text-gray-400">{ex.id}</span>
                </div>
                <div className="bg-gray-100 p-3 rounded-md text-sm text-gray-800 font-mono">
                  {ex.input_prompt}
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
                  <div>
                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Expected Tools</h4>
                    <p className="text-sm mt-1">{ex.expected_tools?.length ? ex.expected_tools.join(', ') : 'None'}</p>
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Expected Content</h4>
                    <p className="text-sm mt-1">{ex.expected_output_contains?.length ? ex.expected_output_contains.join(' AND ') : 'Any'}</p>
                  </div>
                  {ex.must_not_contain?.length > 0 && (
                    <div className="col-span-full">
                      <h4 className="text-xs font-semibold text-red-500 uppercase tracking-wider">Must Not Contain</h4>
                      <p className="text-sm mt-1 text-red-700">{ex.must_not_contain.join(', ')}</p>
                    </div>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
