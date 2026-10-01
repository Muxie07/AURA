'use client';
import { useEffect, useState } from 'react';
import { fetchApi } from '../lib/api';
import { Card, PageHeader } from '../components/ui';
import { WrenchScrewdriverIcon, CheckCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';

const TOOL_REGISTRY = [
  { friendly: 'Customer Search', name: 'customer.search', description: 'Find customer information by name, email or ID', risk: 'LOW', category: 'CRM' },
  { friendly: 'Update Customer', name: 'customer.update', description: 'Update customer records and preferences', risk: 'MEDIUM', category: 'CRM' },
  { friendly: 'Create Order', name: 'order.create', description: 'Create new orders in the system', risk: 'HIGH', category: 'Orders' },
  { friendly: 'Cancel Order', name: 'order.cancel', description: 'Cancel existing orders', risk: 'HIGH', category: 'Orders' },
  { friendly: 'Check Inventory', name: 'inventory.check', description: 'Check inventory levels and availability', risk: 'LOW', category: 'Inventory' },
  { friendly: 'Read Server Logs', name: 'read_server_logs', description: 'Read and analyze server logs for issues', risk: 'LOW', category: 'SRE' },
  { friendly: 'Restart Service', name: 'restart_service', description: 'Restart system services', risk: 'HIGH', category: 'SRE' },
  { friendly: 'Terminate Process', name: 'kill_process', description: 'Terminate OS processes', risk: 'HIGH', category: 'SRE' },
  { friendly: 'Send Notification', name: 'send_notification', description: 'Send notifications to users or teams', risk: 'MEDIUM', category: 'Comms' },
];

const RISK_COLOR: Record<string, string> = {
  LOW: 'bg-green-100 text-green-700',
  MEDIUM: 'bg-yellow-100 text-yellow-700',
  HIGH: 'bg-amber-100 text-amber-700',
};

export default function ToolsPage() {
  const [auditCount, setAuditCount] = useState<number | null>(null);

  useEffect(() => {
    fetchApi('/runs')
      .then(r => r.json())
      .then(j => setAuditCount((j.runs || []).reduce((acc: number, r: any) => acc + (r.tool_call_count || 0), 0)))
      .catch(() => setAuditCount(0));
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Available Actions"
        description="These are the actions AURA is authorized to perform on your behalf."
      />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card>
          <div>
            <p className="text-sm text-gray-500">Available Actions</p>
            <p className="text-3xl font-bold mt-1">{TOOL_REGISTRY.length}</p>
          </div>
        </Card>
        <Card>
          <div>
            <p className="text-sm text-gray-500">Require Human Approval</p>
            <p className="text-3xl font-bold mt-1 text-amber-600">{TOOL_REGISTRY.filter(t => t.risk === 'HIGH').length}</p>
          </div>
        </Card>
        <Card>
          <div>
            <p className="text-sm text-gray-500">Actions Taken (this session)</p>
            <p className="text-3xl font-bold mt-1 text-blue-600">{auditCount ?? '—'}</p>
          </div>
        </Card>
      </div>

      <Card title="Action Registry">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead>
              <tr>
                <th className="py-3 text-left text-xs font-semibold text-gray-500 uppercase">Action</th>
                <th className="py-3 text-left text-xs font-semibold text-gray-500 uppercase">Description</th>
                <th className="py-3 text-left text-xs font-semibold text-gray-500 uppercase">Security</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {TOOL_REGISTRY.map((tool) => (
                <tr key={tool.name} className="hover:bg-gray-50">
                  <td className="py-4">
                    <p className="text-sm font-semibold text-gray-900">{tool.friendly}</p>
                    <p className="text-xs text-gray-400 font-mono mt-0.5">ID: {tool.name}</p>
                  </td>
                  <td className="py-4 text-sm text-gray-600">{tool.description}</td>
                  <td className="py-4 text-sm">
                    {tool.risk === 'HIGH' ? (
                      <span className="flex items-center gap-1.5 text-amber-700 bg-amber-50 px-2.5 py-1 rounded-full inline-flex font-medium text-xs">
                        <ExclamationTriangleIcon className="w-4 h-4" />
                        Approval Required
                      </span>
                    ) : (
                      <span className="flex items-center gap-1.5 text-green-700 bg-green-50 px-2.5 py-1 rounded-full inline-flex font-medium text-xs">
                        <CheckCircleIcon className="w-4 h-4" />
                        Auto-execute
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
