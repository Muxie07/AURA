import re

with open('frontend/src/app/conversations/page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

target = """        return (
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
        );"""

replacement = """        return (
          <div className="mt-2 mb-2 w-full max-w-2xl bg-white border border-gray-200 shadow-md rounded-xl overflow-hidden font-sans">
            <div className="bg-blue-600 px-6 py-5 flex justify-between items-center text-white">
              <h3 className="font-bold text-xl tracking-wide flex flex-col">
                <span className="text-blue-200 text-xs uppercase tracking-widest font-semibold">AURA</span>
                QUOTATION
              </h3>
              <span className="bg-blue-500 text-white px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider shadow-sm border border-blue-400">
                {quoteData.status || 'Draft'}
              </span>
            </div>
            <div className="p-6">
              <div className="flex justify-between items-start mb-8">
                <div>
                  <p className="text-xs text-gray-400 font-semibold uppercase tracking-widest mb-1">Customer</p>
                  <p className="text-gray-900 font-bold text-lg">{customer.name || 'Unknown Customer'}</p>
                  <p className="text-gray-500 text-sm mt-1">{customer.email || 'No email'}</p>
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
                      <th className="px-4 py-3 text-right uppercase text-xs tracking-wider">Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 bg-white">
                    <tr className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-4 text-gray-900 font-medium">Enterprise Database Server</td>
                      <td className="px-4 py-4 text-center text-gray-700">1</td>
                      <td className="px-4 py-4 text-right text-gray-700">₹{parseFloat(quoteData.total).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                      <td className="px-4 py-4 text-right text-gray-900 font-semibold">₹{parseFloat(quoteData.total).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              
              <div className="mt-6 flex justify-end">
                <div className="w-72 space-y-2 bg-gray-50 p-4 rounded-lg border border-gray-100">
                  <div className="flex justify-between text-sm text-gray-600">
                    <span>Subtotal:</span>
                    <span className="font-medium">₹{parseFloat(quoteData.total).toLocaleString('en-IN', {minimumFractionDigits: 2})}</span>
                  </div>
                  <div className="flex justify-between text-sm text-gray-500">
                    <span>Tax:</span>
                    <span>₹0.00</span>
                  </div>
                  <div className="flex justify-between text-sm text-gray-500 pb-2">
                    <span>Discount:</span>
                    <span>₹0.00</span>
                  </div>
                  <div className="flex justify-between text-lg font-bold text-gray-900 border-t border-gray-200 pt-3">
                    <span>TOTAL:</span>
                    <span>₹{parseFloat(quoteData.total).toLocaleString('en-IN', {minimumFractionDigits: 2})}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        );"""

content = content.replace(target, replacement)
with open('frontend/src/app/conversations/page.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
