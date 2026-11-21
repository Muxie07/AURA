const content = '**customer.search result:**\n{\n  "customers": [\n    {\n      "id": "cust-001",\n      "name": "Acme Technologies",\n      "email": "contact@acme.com",\n      "org_id": "1c06ade7-cb6b-4cc3-b86e-d2e6a5d96d44"\n    },\n    {\n      "id": "CUST-001-1c06ade7",\n      "name": "Acme Technologies (Fallback)",\n      "email": "contact2@acme.com",\n      "org_id": "1c06ade7-cb6b-4cc3-b86e-d2e6a5d96d44"\n    }\n  ]\n}\n**quotation.create_draft result:**\n{\n  "quotation_id": "Q-0E198C2E",\n  "total": "5000.00",\n  "status": "draft"\n}';

const renderMessageContent = (content) => {
  if (!content) return null;

  if (content.includes('quotation.create_draft') && content.includes('{')) {
    try {
      const extractJson = (keyword) => {
        const keywordIdx = content.indexOf(keyword);
        if (keywordIdx === -1) return null;
        const sub = content.substring(keywordIdx);
        const start = sub.indexOf('{');
        if (start === -1) return null;
        
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
          
          escapeNext = (!escapeNext && char === '\\\\');
          
          if (braceCount === 0 && jsonStr.length > 0) {
            return JSON.parse(jsonStr);
          }
        }
        return null;
      };

      const quoteData = extractJson('quotation.create_draft');
      const custData = extractJson('customer.search');
      
      console.log('quoteData:', quoteData);
      console.log('custData:', custData);

      if (quoteData && quoteData.quotation_id) {
        console.log('CONDITION PASSED');
        return true;
      } else {
        console.log('CONDITION FAILED');
      }
    } catch (e) {
      console.error('Error rendering quotation component', e);
    }
  } else {
    console.log('NOT INCLUDED');
  }

  return false;
};

renderMessageContent(content);
