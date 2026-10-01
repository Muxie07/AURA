with open('frontend/src/app/conversations/page.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('await startStreaming(runId, convId);', 'await startStreaming(runId, convId!);')

with open('frontend/src/app/conversations/page.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
