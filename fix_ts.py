with open('frontend/src/app/conversations/page.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('await startStreaming(currentRunId, activeId);', 'await startStreaming(currentRunId, activeId!);')

with open('frontend/src/app/conversations/page.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
