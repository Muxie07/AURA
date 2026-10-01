import os

path = "frontend/src/app/page.tsx"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# Add RefreshCw import
text = text.replace("Activity, Bot, ShieldCheck, ArrowRight, Server, Zap, Database", "Activity, Bot, ShieldCheck, ArrowRight, Server, Zap, Database, RefreshCw")

# Rewrite the state and fetch logic
fetch_logic = """
  const [runs, setRuns] = useState<any[]>([]);
  const [approvals, setApprovals] = useState<any[]>([]);
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    try {
      const [runsRes, appRes, healthRes] = await Promise.all([
        fetchApi('/runs').catch(() => null),
        fetchApi('/approvals').catch(() => null),
        fetch((process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1').replace('/api/v1', '/health')).catch(() => null)
      ]);

      if (runsRes) setRuns((await runsRes.json()).runs || []);
      if (appRes) setApprovals((await appRes.json()).approvals || []);
      if (healthRes?.ok) setHealth(await healthRes.json());
      setError(null);
    } catch (err: any) {
      console.error("Dashboard fetch error:", err);
      setError(err.message || "Failed to load dashboard data");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);
"""

# Find the old state block
old_state_block_start = text.find("  const [runs, setRuns]")
old_state_block_end = text.find("  if (loading) return")
if old_state_block_start != -1 and old_state_block_end != -1:
    text = text[:old_state_block_start] + fetch_logic + text[old_state_block_end:]

# Add the refresh button to the PageHeader actions
old_actions = 'actions={<Link href="/conversations" className="inline-flex items-center justify-center rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"><Zap className="w-4 h-4 mr-2" /> Ask AURA</Link>}'
new_actions = 'actions={<div className="flex gap-3"><button onClick={() => fetchData(true)} disabled={refreshing} className="inline-flex items-center justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-700 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 disabled:opacity-50"><RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? "animate-spin" : ""}`} /> Refresh</button><Link href="/conversations" className="inline-flex items-center justify-center rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500"><Zap className="w-4 h-4 mr-2" /> Ask AURA</Link></div>}'

text = text.replace(old_actions, new_actions)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated dashboard refresh logic")
