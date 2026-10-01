import io

with io.open("frontend/src/app/agents/page.tsx", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("""        const res = await fetch(`${API_URL}/agent/runs`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });""", "        const res = await fetchApi('/agent/runs');")

with io.open("frontend/src/app/agents/page.tsx", "w", encoding="utf-8") as f:
    f.write(content)
