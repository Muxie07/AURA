'use client';
import { useState } from 'react';
import { 
  Users2, 
  Building2, 
  Plus, 
  ShieldCheck, 
  Mail, 
  Key, 
  UserPlus, 
  Lock,
  CheckCircle2
} from 'lucide-react';

interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: 'TENANT_ADMIN' | 'DEVELOPER' | 'OPERATOR' | 'AUDITOR';
  status: 'ACTIVE' | 'INVITED';
  last_login: string;
}

const MEMBERS: TeamMember[] = [
  {
    id: 'user-1',
    name: 'Mufeed (Workspace Lead)',
    email: 'mufeed@aura.internal',
    role: 'TENANT_ADMIN',
    status: 'ACTIVE',
    last_login: 'Just now',
  },
  {
    id: 'user-2',
    name: 'Sales Operations Lead',
    email: 'sales.ops@aura.internal',
    role: 'OPERATOR',
    status: 'ACTIVE',
    last_login: '1 hour ago',
  },
  {
    id: 'user-3',
    name: 'Compliance Auditor',
    email: 'compliance@aura.internal',
    role: 'AUDITOR',
    status: 'ACTIVE',
    last_login: 'Yesterday',
  },
  {
    id: 'user-4',
    name: 'Platform Engineer',
    email: 'infra@aura.internal',
    role: 'DEVELOPER',
    status: 'ACTIVE',
    last_login: '3 days ago',
  }
];

export default function TenantsPage() {
  const [members, setMembers] = useState<TeamMember[]>(MEMBERS);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Team & Multi-Tenant Boundaries</h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
              Row-Level Security (RLS)
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Enterprise RBAC management, tenant boundaries, and member access governance.
          </p>
        </div>

        <button className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 transition shadow-xs">
          <UserPlus className="h-4 w-4" /> Invite Team Member
        </button>
      </div>

      {/* Tenant Summary Banner */}
      <div className="bg-slate-50/70 p-5 rounded-2xl border border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center font-bold">
            <Building2 className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900">Current Organization: Enterprise Production</h3>
            <p className="text-xs text-slate-500 font-mono">tenant_id: 1c06ade7-cb6b-4cc3-b86e-d2e6a5d96d44</p>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs">
          <div>
            <span className="text-slate-400 block text-[10px]">Data Boundary</span>
            <span className="font-semibold text-emerald-600">Isolated PostgreSQL Schema</span>
          </div>
          <div>
            <span className="text-slate-400 block text-[10px]">Active Members</span>
            <span className="font-semibold text-slate-900">{members.length} Users</span>
          </div>
        </div>
      </div>

      {/* Team Members Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100">
          <h2 className="text-sm font-bold text-slate-900">Assigned Team Members & Roles</h2>
          <p className="text-[11px] text-slate-500">Every member action is signed with cryptographic JWT identity.</p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold">
                <th className="py-3 px-4">Member</th>
                <th className="py-3 px-4">Email</th>
                <th className="py-3 px-4">Assigned RBAC Role</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Last Active</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {members.map((m) => (
                <tr key={m.id} className="hover:bg-slate-50/60 transition">
                  <td className="py-3 px-4 font-bold text-slate-900">
                    {m.name}
                  </td>
                  <td className="py-3 px-4 text-slate-600 font-mono text-[11px]">
                    {m.email}
                  </td>
                  <td className="py-3 px-4">
                    <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                      {m.role}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                      {m.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-500">
                    {m.last_login}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
