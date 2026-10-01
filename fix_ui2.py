path = "frontend/src/app/conversations/page.tsx"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

QUICK_ACTIONS_DEF = """
const QUICK_ACTIONS = [
  {
    label: "API Latency",
    prompt: "Investigate our recent API latency."
  },
  {
    label: "Support Policy",
    prompt: "Summarize our customer support policy."
  },
  {
    label: "P1 Incident",
    prompt: "Find the procedure for handling a P1 incident."
  },
  {
    label: "Create Quotation",
    prompt: "Create a draft quotation for Acme Technologies."
  }
];

export default function ConversationsPage() {"""

text = text.replace("export default function ConversationsPage() {", QUICK_ACTIONS_DEF)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Injected QUICK_ACTIONS")
