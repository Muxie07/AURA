let displayContent = `Some text
**customer.search result:**
\`\`\`json
{
  "customers": [
    { "id": "cust-001" }
  ]
}
\`\`\`
Some more text.
`;

const regex = /\*\*([a-zA-Z0-9_.]+)\s+result:\*\*/g;
let match;
const matches = [];
while ((match = regex.exec(displayContent)) !== null) {
  matches.push({ full: match[0], name: match[1], index: match.index });
}

for (let i = matches.length - 1; i >= 0; i--) {
  const m = matches[i];
  const startIdx = m.index;
  const jsonStart = displayContent.indexOf('{', startIdx);
  if (jsonStart !== -1 && jsonStart < startIdx + 100) {
    let braceCount = 0;
    let inString = false;
    let escapeNext = false;
    let jsonEnd = -1;
    
    for (let j = jsonStart; j < displayContent.length; j++) {
      const char = displayContent[j];
      if (!escapeNext && char === '"') inString = !inString;
      if (!inString) {
        if (char === '{') braceCount++;
        else if (char === '}') braceCount--;
      }
      escapeNext = (!escapeNext && char === '\\');
      
      if (braceCount === 0) {
        jsonEnd = j;
        break;
      }
    }
    
    if (jsonEnd !== -1) {
      const before = displayContent.substring(0, startIdx);
      const after = displayContent.substring(jsonEnd + 1);
      
      let cleanedAfter = after.replace(/^\s*```\n?/, '');
      let cleanedBefore = before.replace(/```json\s*$/, '');
      
      displayContent = cleanedBefore + `\n> ⚙️ _Executed internal tool: ${m.name}_\n` + cleanedAfter;
    }
  }
}
console.log(displayContent);
