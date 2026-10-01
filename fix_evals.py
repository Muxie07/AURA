path = "frontend/src/app/evaluations/page.tsx"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# Fix datasets array property
text = text.replace("dData.datasets || []", "dData.examples || []")

# Fix datasets rendering
text = text.replace("{ds.status || 'Active'}", "{ds.category || 'Active'}")

# Fix benchmarks rendering
text = text.replace("Score: {bm.score}", "Success: {(bm.success_rate * 100).toFixed(1)}% | Latency: {bm.avg_latency_ms}ms")

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated evaluations page.")
