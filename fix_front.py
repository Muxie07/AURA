import re
with open('frontend/src/app/conversations/page.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(\"statusData.status === 'COMPLETED'\", \"statusData.status.toUpperCase() === 'COMPLETED'\")
text = text.replace(\"statusData.status === 'FAILED'\", \"statusData.status.toUpperCase() === 'FAILED'\")
text = text.replace(\"statusData.status === 'AWAITING_APPROVAL'\", \"statusData.status.toUpperCase() === 'AWAITING_APPROVAL'\")
text = text.replace(\"finalStatus.status === 'AWAITING_APPROVAL'\", \"finalStatus.status.toUpperCase() === 'AWAITING_APPROVAL'\")

with open('frontend/src/app/conversations/page.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
