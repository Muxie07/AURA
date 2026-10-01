import io
import re

def update_file(path, replacements):
    with io.open(path, "r", encoding="utf-8") as f:
        content = f.read()
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
        else:
            print(f"Warning: Could not find snippet in {path}")
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(content)

page_replacements = [
    (
        "import { Card, PageHeader, LoadingState, StatusBadge, EmptyState, Button } from './components/ui';",
        "import { Card, PageHeader, LoadingState, StatusBadge, EmptyState, Button } from './components/ui';\nimport { fetchApi } from './lib/api';"
    ),
    (
        "const [loading, setLoading] = useState(true);",
        "const [loading, setLoading] = useState(true);\n  const [error, setError] = useState<string | null>(null);"
    ),
    (
        """        const token = localStorage.getItem('token') || 'test-token';
        const headers = { 'Authorization': Bearer  };
        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

        const [runsRes, appRes, healthRes] = await Promise.all([
          fetch(${API_URL}/agent/runs, { headers }).catch(() => null),
          fetch(${API_URL}/agent/approvals, { headers }).catch(() => null),
          fetch(http://localhost:8000/health).catch(() => null)
        ]);

        if (runsRes?.ok) setRuns((await runsRes.json()).runs || []);
        if (appRes?.ok) setApprovals((await appRes.json()).approvals || []);
        if (healthRes?.ok) setHealth(await healthRes.json());""",
        """        const [runsRes, appRes, healthRes] = await Promise.all([
          fetchApi('/agent/runs').catch(() => null),
          fetchApi('/agent/approvals').catch(() => null),
          fetch((process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1').replace('/api/v1', '/health')).catch(() => null)
        ]);

        if (runsRes) setRuns((await runsRes.json()).runs || []);
        if (appRes) setApprovals((await appRes.json()).approvals || []);
        if (healthRes?.ok) setHealth(await healthRes.json());"""
    ),
    (
        """      } catch (err) {
        console.error("Dashboard fetch error:", err);
      } finally {""",
        """      } catch (err: any) {
        console.error("Dashboard fetch error:", err);
        setError(err.message || "Failed to load dashboard data");
      } finally {"""
    ),
    (
        """  if (loading) return <LoadingState message="Loading enterprise dashboard..." />;""",
        """  if (loading) return <LoadingState message="Loading enterprise dashboard..." />;\n  if (error) return <div className="p-4 bg-red-50 text-red-600 rounded-lg border border-red-200">Error: {error}</div>;"""
    )
]

update_file("frontend/src/app/page.tsx", page_replacements)
print("Updated page.tsx")
