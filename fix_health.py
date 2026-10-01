import io

with io.open("frontend/src/app/page.tsx", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("fetch(`http://localhost:8000/health`)", "fetch((process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1').replace('/api/v1', '/health'))")

with io.open("frontend/src/app/page.tsx", "w", encoding="utf-8") as f:
    f.write(content)
