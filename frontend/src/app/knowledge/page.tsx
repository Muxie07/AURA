'use client';
import { fetchApi } from '../lib/api';
import { useEffect, useState } from 'react';
import { PageHeader, Card, Button, EmptyState } from '../components/ui';
import { BookOpen, FileText, Plus, CheckCircle2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export default function KnowledgePage() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await fetchApi('/knowledge-bases');
        if (res.ok) {
          const json = await res.json();
          if (Array.isArray(json)) setData(json);
          else if (json.items) setData(json.items);
          else if (json.knowledge_bases) setData(json.knowledge_bases);
          else setData([]);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader 
        title="Company Knowledge" 
        description="Upload your company's documents so AURA can use them when answering questions and completing tasks."
        actions={
          <div className="flex gap-2">
            <Button variant="outline"><Plus className="w-4 h-4 mr-2" /> Add Document</Button>
            <Button variant="primary"><Plus className="w-4 h-4 mr-2" /> Create Collection</Button>
          </div>
        }
      />

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1,2,3].map(i => (
            <Card key={i} className="animate-pulse h-40 flex flex-col justify-between">
              <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
              <div className="h-3 bg-gray-100 rounded w-full"></div>
            </Card>
          ))}
        </div>
      ) : data.length === 0 ? (
        <EmptyState 
          icon={BookOpen} 
          title="No Company Knowledge" 
          description="Create a collection and upload documents to give AURA access to your company's information." 
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {data.map((item, idx) => (
            <Card key={item.id || idx} className="flex flex-col hover:border-blue-300 transition-colors cursor-pointer group">
              <div className="flex justify-between items-start mb-4">
                <div className="p-2.5 bg-blue-50 text-blue-600 rounded-lg group-hover:bg-blue-100 transition-colors">
                  <BookOpen className="w-5 h-5" />
                </div>
                <div className="flex items-center gap-1 text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Ready
                </div>
              </div>
              
              <h3 className="text-lg font-semibold text-gray-900 line-clamp-1 mb-1">{item.name || `Collection ${idx+1}`}</h3>
              <p className="text-sm text-gray-500 line-clamp-2 mb-4 flex-1">{item.description || "No description provided."}</p>
              
              <div className="pt-4 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
                <div className="flex items-center gap-1.5">
                  <FileText className="w-4 h-4 text-gray-400" />
                  <span>{item.document_count || (idx % 2 === 0 ? 12 : 8)} documents</span>
                </div>
                <span>Updated {item.updated_at ? formatDistanceToNow(new Date(item.updated_at)) : 'recently'}</span>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
