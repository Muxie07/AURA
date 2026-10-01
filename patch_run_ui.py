with open("frontend/src/app/evaluations/runs/[id]/page.tsx", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace(
    "example_id: string; actual_output: string | null; passed: boolean;",
    "example_id: string; input_prompt?: string; expected_tools?: string[]; actual_output: string | null; passed: boolean;"
)

table_header = """                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Example ID</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>"""

new_table_header = """                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Prompt & Expected</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status & Output</th>"""

table_row = """                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{res.example_id.slice(0, 8)}...</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {res.passed ? (
                        <span className="inline-flex items-center gap-1 text-green-700 font-medium"><CheckCircleIcon className="w-5 h-5" /> PASS</span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-red-700 font-medium"><XCircleIcon className="w-5 h-5" /> FAIL</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      <div className="max-h-32 overflow-y-auto whitespace-pre-wrap">{res.actual_output || 'No output'}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {res.tools_used && res.tools_used.length > 0 ? (
                        <div className="flex gap-1 flex-wrap">
                          {res.tools_used.map((t, i) => <span key={i} className="bg-gray-100 text-gray-800 px-2 py-0.5 rounded text-xs">{t}</span>)}
                        </div>
                      ) : '-'}
                    </td>"""

new_table_row = """                    <td className="px-6 py-4 text-sm text-gray-900 w-1/3">
                      <div className="font-medium mb-1">Prompt:</div>
                      <div className="text-gray-600 italic whitespace-pre-wrap mb-3">{res.input_prompt || res.example_id.slice(0,8)}</div>
                      <div className="font-medium text-xs text-gray-500">Expected Tools:</div>
                      <div className="flex gap-1 flex-wrap mt-1">
                        {res.expected_tools && res.expected_tools.length > 0 ? res.expected_tools.map((t, i) => <span key={i} className="bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded text-xs">{t}</span>) : <span className="text-xs text-gray-400">None</span>}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm w-1/3">
                      <div className="mb-2">
                        {res.passed ? (
                          <span className="inline-flex items-center gap-1 text-green-700 font-medium bg-green-50 px-2 py-1 rounded-md"><CheckCircleIcon className="w-5 h-5" /> PASS</span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-red-700 font-medium bg-red-50 px-2 py-1 rounded-md"><XCircleIcon className="w-5 h-5" /> FAIL</span>
                        )}
                      </div>
                      <div className="font-medium text-xs text-gray-500 mt-2">Actual Output:</div>
                      <div className="max-h-32 overflow-y-auto whitespace-pre-wrap text-gray-600 text-sm mt-1 bg-gray-50 p-2 rounded border border-gray-100">{res.actual_output || 'No output'}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <div className="flex gap-1 flex-wrap">
                        {res.tools_used && res.tools_used.length > 0 ? res.tools_used.map((t, i) => <span key={i} className="bg-gray-100 text-gray-800 px-2 py-0.5 rounded text-xs">{t}</span>) : '-'}
                      </div>
                    </td>"""

text = text.replace(table_header, new_table_header)
text = text.replace(table_row, new_table_row)

text = text.replace(
    '<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Output</th>',
    ''
)

with open("frontend/src/app/evaluations/runs/[id]/page.tsx", "w", encoding="utf-8") as f:
    f.write(text)
print("Patched UI!")
