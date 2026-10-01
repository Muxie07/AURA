import re

with open('frontend/src/app/conversations/page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

start_idx = content.find('const renderMessageContent = (content: string) => {')
end_idx = content.find('export default function ConversationsPage')

if start_idx != -1 and end_idx != -1:
    new_func = """const renderMessageContent = (content: string) => {
  if (!content) return null;

  try {
    let quoteData: any = null;
    let custData: any = null;

    const extractJsonBraces = (keyword: string) => {
      const idx = content.indexOf(keyword);
      if (idx === -1) return null;
      const sub = content.substring(idx);
      const start = sub.indexOf('{');
      if (start === -1) return null;
      let braceCount = 0, inString = false, escapeNext = false, jsonStr = '';
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
          try { return JSON.parse(jsonStr); } catch (e) { return null; }
        }
      }
      return null;
    };

    const tryExtractFromBlocks = () => {
      let q = null, c = null;
      // Robust JSON extraction using matching braces (simplified logic for blocks)
      let currentStart = content.indexOf('{');
      while (currentStart !== -1) {
        let braceCount = 0, inString = false, escapeNext = false, jsonStr = '';
        for (let i = currentStart; i < content.length; i++) {
          const char = content[i];
          jsonStr += char;
          if (!escapeNext && char === '"') inString = !inString;
          if (!inString) {
            if (char === '{') braceCount++;
            else if (char === '}') braceCount--;
          }
          escapeNext = (!escapeNext && char === '\\\\');
          if (braceCount === 0 && jsonStr.length > 0) {
            try {
              const parsed = JSON.parse(jsonStr);
              if (parsed && parsed.quotation_id) q = parsed;
              if (parsed && (parsed.customers || parsed.name)) c = parsed;
            } catch(e) {}
            break;
          }
        }
        currentStart = content.indexOf('{', currentStart + 1);
      }
      return { q, c };
    };

    quoteData = extractJsonBraces('quotation.create_draft');
    custData = extractJsonBraces('customer.search');

    if (!quoteData || !quoteData.quotation_id) {
      const alt = tryExtractFromBlocks();
      if (alt.q && alt.q.quotation_id) quoteData = alt.q;
      if (!custData && alt.c) custData = alt.c;
    }

    if (quoteData && quoteData.quotation_id) {
      let customer = { name: 'Unknown Customer', email: 'No email' };
      if (custData) {
        if (Array.isArray(custData.customers) && custData.customers.length > 0) {
          customer = custData.customers[0];
        } else if (custData.name) {
          customer = custData;
        }
      }

      const totalNum = parseFloat(quoteData.total || '0');
      const total = totalNum.toLocaleString('en-IN', {minimumFractionDigits: 2});
      
      return (
        <div className="mt-4 mb-4 w-full max-w-2xl bg-white border border-gray-200 shadow-md rounded-xl overflow-hidden font-sans">
          <div className="bg-blue-600 px-6 py-5 flex justify-between items-center text-white">
            <h3 className="font-bold text-xl tracking-wide flex flex-col">
              <span className="text-blue-200 text-xs uppercase tracking-widest font-semibold">AURA</span>
              QUOTATION
            </h3>
            <span className="bg-blue-500 text-white px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider shadow-sm border border-blue-400">
              {quoteData.status ? quoteData.status.toUpperCase() : 'DRAFT'}
            </span>
          </div>
          <div className="p-6">
            <div className="flex justify-between items-start mb-8">
              <div>
                <p className="text-xs text-gray-400 font-semibold uppercase tracking-widest mb-1">Customer</p>
                <p className="text-gray-900 font-bold text-lg">{customer.name}</p>
                <p className="text-gray-500 text-sm mt-1">{customer.email}</p>
              </div>
              <div className="text-right">
                <p className="text-xs text-gray-400 font-semibold uppercase tracking-widest mb-1">Quotation ID</p>
                <p className="text-gray-900 font-mono font-medium text-lg">{quoteData.quotation_id}</p>
              </div>
            </div>
            
            <div className="border border-gray-200 rounded-lg overflow-hidden shadow-sm">
              <table className="w-full text-sm text-left">
                <thead className="bg-gray-50 text-gray-600 font-semibold border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-3 uppercase text-xs tracking-wider">Product</th>
                    <th className="px-4 py-3 text-center uppercase text-xs tracking-wider">Qty</th>
                    <th className="px-4 py-3 text-right uppercase text-xs tracking-wider">Unit Price</th>
                    <th className="px-4 py-3 text-right uppercase text-xs tracking-wider">Amount</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white">
                  <tr className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-4 text-gray-900 font-medium">Enterprise Database Server</td>
                    <td className="px-4 py-4 text-center text-gray-700">1</td>
                    <td className="px-4 py-4 text-right text-gray-700">₹{total}</td>
                    <td className="px-4 py-4 text-right text-gray-900 font-semibold">₹{total}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            
            <div className="mt-6 flex justify-end">
              <div className="w-72 space-y-2 bg-gray-50 p-4 rounded-lg border border-gray-100">
                <div className="flex justify-between text-sm text-gray-600">
                  <span>Subtotal:</span>
                  <span className="font-medium">₹{total}</span>
                </div>
                <div className="flex justify-between text-sm text-gray-500">
                  <span>Discount:</span>
                  <span>₹0.00</span>
                </div>
                <div className="flex justify-between text-sm text-gray-500 pb-2">
                  <span>Tax:</span>
                  <span>₹0.00</span>
                </div>
                <div className="flex justify-between text-lg font-bold text-gray-900 border-t border-gray-200 pt-3">
                  <span>TOTAL:</span>
                  <span>₹{total}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      );
    }
  } catch (e) {
    console.error('Error rendering quotation component', e);
  }

  return <div className="whitespace-pre-wrap leading-relaxed text-[15px]">{content}</div>;
};

"""
    
    content = content[:start_idx] + new_func + content[end_idx:]
    with open('frontend/src/app/conversations/page.tsx', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Replaced renderMessageContent successfully.")
else:
    print("Could not find start or end index.")
