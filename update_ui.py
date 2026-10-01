import re

with open('frontend/src/app/conversations/page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

replacement = """const renderMessageContent = (content: string) => {
  if (!content) return null;
  
  if (content.includes('quotation.create_draft result:') && content.includes('customer.search result:')) {
    try {
      const getJsonAfter = (marker: string) => {
        const idx = content.indexOf(marker);
        if (idx === -1) return null;
        const sub = content.substring(idx);
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

      const quoteData = getJsonAfter('quotation.create_draft result:');
      const custData = getJsonAfter('customer.search result:');

      if (quoteData && quoteData.quotation_id && custData && custData.customers) {
        const customer = custData.customers[0] || {};
        
        return (
          <div className="mt-2 mb-2 w-full max-w-2xl bg-white border border-gray-200 shadow-sm rounded-xl overflow-hidden font-sans">
            <div className="bg-blue-600 px-6 py-4 flex justify-between items-center text-white">
              <h3 className="font-bold text-lg tracking-wide">DRAFT QUOTATION</h3>
              <span className="bg-blue-500 text-blue-50 px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider">
                {quoteData.status || 'Draft'}
              </span>
            </div>
            <div className="p-6">
              <div className="flex justify-between items-start mb-8">
                <div>
                  <p className="text-sm text-gray-500 font-semibold uppercase tracking-wider mb-1">Customer</p>
                  <p className="text-gray-900 font-bold text-lg">{customer.name || 'Unknown Customer'}</p>
                  <p className="text-gray-600 text-sm mt-1">{customer.email || 'No email'}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-500 font-semibold uppercase tracking-wider mb-1">Quotation ID</p>
                  <p className="text-gray-900 font-mono font-medium text-lg">{quoteData.quotation_id}</p>
                </div>
              </div>
              
              <div className="border border-gray-200 rounded-lg overflow-hidden">
                <table className="w-full text-sm text-left">
                  <thead className="bg-gray-50 text-gray-600 font-semibold border-b border-gray-200">
                    <tr>
                      <th className="px-4 py-3">Product</th>
                      <th className="px-4 py-3 text-center">Qty</th>
                      <th className="px-4 py-3 text-right">Unit Price</th>
                      <th className="px-4 py-3 text-right">Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    <tr>
                      <td className="px-4 py-4 text-gray-900 font-medium">Enterprise Database Server</td>
                      <td className="px-4 py-4 text-center text-gray-700">1</td>
                      <td className="px-4 py-4 text-right text-gray-700">${parseFloat(quoteData.total).toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                      <td className="px-4 py-4 text-right text-gray-900 font-bold">${parseFloat(quoteData.total).toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              
              <div className="mt-6 flex justify-end">
                <div className="w-64 space-y-3">
                  <div className="flex justify-between text-sm text-gray-600 px-2">
                    <span>Subtotal:</span>
                    <span>${parseFloat(quoteData.total).toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                  </div>
                  <div className="flex justify-between text-base font-bold text-gray-900 border-t border-gray-200 pt-3 px-2">
                    <span>Total:</span>
                    <span>${parseFloat(quoteData.total).toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        );
      }
    } catch (e) {
      console.error('Error parsing quotation', e);
    }
  }

  return <div className="whitespace-pre-wrap leading-relaxed text-[15px]">{content}</div>;
};

export default function ConversationsPage() {"""

content = content.replace('export default function ConversationsPage() {', replacement)
content = content.replace('<div className="whitespace-pre-wrap leading-relaxed text-[15px]">{msg.content}</div>', '{renderMessageContent(msg.content)}')

target_stream = '''<div className="whitespace-pre-wrap leading-relaxed text-[15px]">
                  {streamContent || (
                    <span className="flex items-center text-gray-500 gap-2">
                      <ArrowPathIcon className="h-4 w-4 animate-spin" />
                      AURA is thinking...
                    </span>
                  )}
                </div>'''

replacement_stream = '''{streamContent ? renderMessageContent(streamContent) : (
                <div className="whitespace-pre-wrap leading-relaxed text-[15px]">
                    <span className="flex items-center text-gray-500 gap-2">
                      <ArrowPathIcon className="h-4 w-4 animate-spin" />
                      AURA is thinking...
                    </span>
                </div>
                )}'''

content = content.replace(target_stream, replacement_stream)

with open('frontend/src/app/conversations/page.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated UI successfully.")
