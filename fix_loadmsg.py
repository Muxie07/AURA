with open('frontend/src/app/conversations/page.tsx', 'r') as f:
    text = f.read()

replacement = \"\"\"
      fetchConversations();
      if (activeConv) {
        await loadMessages(activeConv);
        
        // If it was awaiting approval, the db won't have a final assistant message yet
        if (attempts < 120) {
            const statusRes2 = await fetchApi('/agent/runs/' + runId);
            if (statusRes2.ok) {
                const statusData2 = await statusRes2.json();
                if (statusData2.status === 'AWAITING_APPROVAL') {
                    setMessages(prev => [...prev, { id: 'ast_approval', role: 'assistant', content: '?? Action paused. AWAITING HUMAN APPROVAL in the Approvals dashboard.' } as any]);
                }
            }
        }
      }
\"\"\"
text = text.replace(\"\"\"      fetchConversations();
      if (activeConv) {
        await loadMessages(activeConv);
      }\"\"\", replacement.strip())

with open('frontend/src/app/conversations/page.tsx', 'w') as f:
    f.write(text)
