with open("frontend/src/app/conversations/page.tsx", "r", encoding="utf-8") as f:
    text = f.read()

# Replace the SSE parsing block
old_block = """                if (payload.event_type === 'content_delta') {
                  setStreamContent((prev) => prev + payload.content);
                } else if (payload.event_type === 'STREAM_END') {
                  // Stream naturally ended
                }"""

new_block = """                if (payload.event_type === 'content_delta') {
                  setStreamContent((prev) => prev + payload.content);
                } else if (payload.event_type === 'STREAM_END') {
                  // Stream naturally ended
                } else if (payload.event_type === 'NODE_STARTED') {
                  if (payload.component !== 'DecisionNode') {
                     setStreamContent((prev) => prev + `\n\n[?? Action: ${payload.component} running...]`);
                  }
                } else if (payload.event_type === 'NODE_COMPLETED') {
                  if (payload.component !== 'DecisionNode') {
                     setStreamContent((prev) => prev + `\n[? ${payload.component} completed]`);
                  }
                } else if (payload.event_type === 'plan_created') {
                  setStreamContent((prev) => prev + `\n\n[?? AURA mapped out a plan]`);
                }"""

if old_block in text:
    text = text.replace(old_block, new_block)
    with open("frontend/src/app/conversations/page.tsx", "w", encoding="utf-8") as f:
        f.write(text)
    print("Patched conversations page")
else:
    print("Could not find block")
