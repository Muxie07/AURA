import io

with io.open("frontend/src/app/conversations/page.tsx", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("""        const res = await fetch(`${API_URL}/conversations`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });""", "        const res = await fetchApi('/conversations');")

with io.open("frontend/src/app/conversations/page.tsx", "w", encoding="utf-8") as f:
    f.write(content)
