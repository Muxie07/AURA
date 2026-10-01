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

export default function Conversations() {
"""

text = text.replace("export default function Conversations() {", QUICK_ACTIONS_DEF)

# Update the empty state grid
old_grid = """                {[
                  "Analyze our recent API performance",
                  "Summarize company knowledge",
                  "Investigate a customer issue",
                  "Create a quotation draft for Acme Corp."
                ].map((prompt, i) => (
                  <button
                    key={i}
                    onClick={() => handleSend(prompt)}
                    className="p-4 text-sm text-gray-700 bg-white border border-gray-200 rounded-xl hover:border-blue-300 hover:shadow-md transition-all text-left shadow-sm"
                  >
                    {prompt}
                  </button>
                ))}"""

new_grid = """                {QUICK_ACTIONS.map((action, i) => (
                  <button
                    key={i}
                    onClick={() => handleSend(action.prompt)}
                    className="p-4 text-sm text-gray-700 bg-white border border-gray-200 rounded-xl hover:border-blue-300 hover:shadow-md transition-all text-left shadow-sm"
                  >
                    {action.prompt}
                  </button>
                ))}"""

text = text.replace(old_grid, new_grid)


# Add the chips to the input area
input_area_old = """        {/* Input Area */}
        <div className="p-4 border-t border-gray-200 bg-white">
          <div className="mx-auto max-w-4xl relative flex items-center">"""

input_area_new = """        {/* Input Area */}
        <div className="p-4 border-t border-gray-200 bg-white">
          {/* Active Conversation Quick Actions */}
          {activeId && (
            <div className="mx-auto max-w-4xl mb-3">
              <div className="text-xs font-medium text-gray-500 mb-2">Quick actions</div>
              <div className="flex flex-wrap gap-2 pb-1">
                {QUICK_ACTIONS.map((action, i) => (
                  <button
                    key={i}
                    onClick={() => handleSend(action.prompt)}
                    disabled={isLoading || !!pendingApproval}
                    className="rounded-full border border-gray-200 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-blue-50 hover:text-blue-600 hover:border-blue-200 transition-colors shadow-sm disabled:opacity-50 whitespace-nowrap"
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="mx-auto max-w-4xl relative flex items-center">"""

text = text.replace(input_area_old, input_area_new)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("UI updated successfully")
