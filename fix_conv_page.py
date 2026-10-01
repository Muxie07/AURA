path = "frontend/src/app/conversations/page.tsx"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("fetchApi('/runs'", "fetchApi('/agent/runs'")
text = text.replace("fetchApi(`/runs/${runId}`)", "fetchApi(`/agent/runs/${runId}`)")
text = text.replace("fetchApi('/approvals'", "fetchApi('/agent/approvals'")
text = text.replace("fetchApi(`/approvals/${appId}/approve`", "fetchApi(`/agent/approvals/${appId}/approve`")
text = text.replace("fetchApi(`/approvals/${appId}/reject`", "fetchApi(`/agent/approvals/${appId}/reject`")
text = text.replace("`${API_URL}/runs/${runId}/stream`", "`${API_URL}/agent/runs/${runId}/stream`")

with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("Updated frontend conversations page")
