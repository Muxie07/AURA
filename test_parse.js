const content = `
**customer.search result:**
{
  "customers": [
    {
      "id": "cust-001",
      "name": "Acme Technologies",
      "email": "contact@acme.com"
    }
  ]
}

**quotation.create_draft result:**
{
  "quotation_id": "Q-4F1F7159",
  "total": "5000.00",
  "status": "draft"
}
`;
const getJsonAfter = (marker) => {
  const idx = content.indexOf(marker);
  if (idx === -1) {
    console.log('marker not found:', marker);
    return null;
  }
  const sub = content.substring(idx);
  const start = sub.indexOf('{');
  if (start === -1) {
    console.log('{ not found after marker:', marker);
    return null;
  }
  
  let braceCount = 0;
  let inString = false;
  let escapeNext = false;
  let jsonStr = '';
  
  for (let i = start; i < sub.length; i++) {
    const char = sub[i];
    jsonStr += char;
    
    if (!escapeNext && char === '"') inString = !inString;
    
    if (!inString) {
      if (char === '{') braceCount++;
      else if (char === '}') braceCount--;
    }
    
    escapeNext = (!escapeNext && char === '\\');
    
    if (braceCount === 0 && jsonStr.length > 0) {
      try {
        return JSON.parse(jsonStr);
      } catch (e) {
        console.error('Failed to parse:', jsonStr, e);
        return null;
      }
    }
  }
  return null;
};

try {
    const quoteData = getJsonAfter('quotation.create_draft result:');
    const custData = getJsonAfter('customer.search result:');
    console.log('Result:', { quoteData, custData });
} catch (e) {
    console.error(e);
}
