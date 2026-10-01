import os

path = "frontend/src/app/page.tsx"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# Fix substring safety
text = text.replace("r.run_id.substring(0,8)", "String(r.run_id).substring(0,8)")

# Fix formatDistanceToNow safety for runs
text = text.replace("Started {formatDistanceToNow(new Date(r.started_at))} ago", "Started {r.started_at ? formatDistanceToNow(new Date(r.started_at)) + ' ago' : 'recently'}")

# Fix formatDistanceToNow safety for approvals
text = text.replace("{formatDistanceToNow(new Date(a.created_at))} ago", "{a.created_at ? formatDistanceToNow(new Date(a.created_at)) + ' ago' : 'recently'}")

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated page.tsx safety")
