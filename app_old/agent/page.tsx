"use client";

import React, { useEffect, useState } from "react";
import { formatDistanceToNow } from "date-fns";

export default function AgentDashboard() {
  const [runs, setRuns] = useState([]);
  const [approvals, setApprovals] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [runsRes, approvalsRes] = await Promise.all([
          fetch("/api/v1/agent/runs"),
          fetch("/api/v1/agent/approvals"),
        ]);
        if (runsRes.ok) {
          const data = await runsRes.json();
          setRuns(data.runs || []);
        }
        if (approvalsRes.ok) {
          const data = await approvalsRes.json();
          setApprovals(data.approvals || []);
        }
      } catch (err) {
        console.error("Failed to fetch agent data:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const handleApprove = async (id: string) => {
    await fetch(`/api/v1/agent/approvals/${id}/approve`, { method: "POST" });
    setApprovals((prev) => prev.filter((a: any) => a.id !== id));
  };

  const handleReject = async (id: string) => {
    await fetch(`/api/v1/agent/approvals/${id}/reject`, { method: "POST" });
    setApprovals((prev) => prev.filter((a: any) => a.id !== id));
  };

  if (loading) return <div className="p-8">Loading dashboard...</div>;

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <h1 className="text-3xl font-bold">AURA Agent Dashboard</h1>
      
      {/* Approvals */}
      <section className="bg-amber-50 p-6 rounded-lg shadow-sm border border-amber-200">
        <h2 className="text-xl font-bold mb-4 text-amber-900">Pending Approvals</h2>
        {approvals.length === 0 ? (
          <p className="text-amber-700">No pending approvals.</p>
        ) : (
          <div className="space-y-4">
            {approvals.map((a: any) => (
              <div key={a.id} className="flex items-center justify-between bg-white p-4 rounded border">
                <div>
                  <p className="font-semibold text-lg">Tool: {a.tool_name}</p>
                  <p className="text-sm text-gray-600">Risk Level: {a.risk_level}</p>
                </div>
                <div className="space-x-2">
                  <button onClick={() => handleApprove(a.id)} className="bg-green-600 text-white px-4 py-2 rounded">Approve</button>
                  <button onClick={() => handleReject(a.id)} className="bg-red-600 text-white px-4 py-2 rounded">Reject</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Runs */}
      <section>
        <h2 className="text-xl font-bold mb-4">Recent Agent Runs</h2>
        <div className="overflow-hidden bg-white shadow sm:rounded-md border">
          <ul role="list" className="divide-y divide-gray-200">
            {runs.map((run: any) => (
              <li key={run.run_id}>
                <a href={`/agent/runs/${run.run_id}`} className="block hover:bg-gray-50 p-4">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-indigo-600 truncate">Run {run.run_id}</p>
                    <div className="ml-2 flex-shrink-0 flex">
                      <p className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        run.status === "COMPLETED" ? "bg-green-100 text-green-800" :
                        run.status === "FAILED" ? "bg-red-100 text-red-800" :
                        "bg-yellow-100 text-yellow-800"
                      }`}>
                        {run.status}
                      </p>
                    </div>
                  </div>
                  <div className="mt-2 sm:flex sm:justify-between">
                    <div className="sm:flex">
                      <p className="flex items-center text-sm text-gray-500">
                        {run.final_result?.substring(0, 100) || run.error_message || "No result"}
                      </p>
                    </div>
                    <div className="mt-2 flex items-center text-sm text-gray-500 sm:mt-0">
                      <p>Started {run.started_at ? formatDistanceToNow(new Date(run.started_at)) + " ago" : "N/A"}</p>
                    </div>
                  </div>
                </a>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}
