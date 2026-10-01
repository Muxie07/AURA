import re

with open('frontend/src/app/conversations/page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Add imports
if 'import ReactMarkdown' not in content:
    content = content.replace(
        "import { fetchApi } from '../lib/api';",
        "import { fetchApi } from '../lib/api';\nimport ReactMarkdown from 'react-markdown';\nimport remarkGfm from 'remark-gfm';"
    )

# Add MarkdownComponents
components_str = """
const MarkdownComponents = {
  h1: ({node, ...props}: any) => <h1 className="text-xl font-bold mt-5 mb-3" {...props} />,
  h2: ({node, ...props}: any) => <h2 className="text-lg font-bold mt-5 mb-3" {...props} />,
  h3: ({node, ...props}: any) => <h3 className="text-base font-bold mt-4 mb-2" {...props} />,
  p: ({node, ...props}: any) => <p className="mb-4 leading-relaxed last:mb-0" {...props} />,
  ul: ({node, ...props}: any) => <ul className="list-disc pl-5 mb-4 space-y-1.5" {...props} />,
  ol: ({node, ...props}: any) => <ol className="list-decimal pl-5 mb-4 space-y-1.5" {...props} />,
  li: ({node, ...props}: any) => <li className="leading-relaxed" {...props} />,
  strong: ({node, ...props}: any) => <strong className="font-semibold text-gray-900" {...props} />,
  a: ({node, ...props}: any) => <a className="text-blue-600 hover:underline" {...props} />,
  blockquote: ({node, ...props}: any) => <blockquote className="border-l-4 border-gray-300 pl-4 py-1 text-gray-600 bg-gray-50 rounded-r-lg my-4 italic" {...props} />,
  code: ({node, inline, className, ...props}: any) => 
    inline ? (
      <code className="bg-gray-100 text-pink-600 px-1.5 py-0.5 rounded text-sm font-mono" {...props} />
    ) : (
      <div className="bg-gray-800 text-gray-100 p-4 rounded-lg overflow-x-auto mb-4 text-sm font-mono leading-relaxed">
        <code className={className} {...props} />
      </div>
    ),
  table: ({node, ...props}: any) => (
    <div className="overflow-x-auto mb-4 border border-gray-200 rounded-lg shadow-sm">
      <table className="w-full text-sm text-left" {...props} />
    </div>
  ),
  thead: ({node, ...props}: any) => <thead className="bg-gray-50 text-gray-600 font-semibold border-b border-gray-200" {...props} />,
  tbody: ({node, ...props}: any) => <tbody className="divide-y divide-gray-100 bg-white" {...props} />,
  tr: ({node, ...props}: any) => <tr className="hover:bg-gray-50 transition-colors" {...props} />,
  th: ({node, ...props}: any) => <th className="px-4 py-3" {...props} />,
  td: ({node, ...props}: any) => <td className="px-4 py-3" {...props} />,
};
"""
if 'const MarkdownComponents =' not in content:
    content = content.replace(
        "const QUICK_ACTIONS =",
        components_str + "\nconst QUICK_ACTIONS ="
    )

# Replace the fallback rendering
old_fallback = "return <div className=\"whitespace-pre-wrap leading-relaxed text-[15px]\">{content}</div>;"
new_fallback = """
  let displayContent = content;
  const regex = /\\*\\*([a-zA-Z0-9_.]+)\\s+result:\\*\\*/g;
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
        escapeNext = (!escapeNext && char === '\\\\');
        
        if (braceCount === 0) {
          jsonEnd = j;
          break;
        }
      }
      
      if (jsonEnd !== -1) {
        const before = displayContent.substring(0, startIdx);
        const after = displayContent.substring(jsonEnd + 1);
        
        let cleanedAfter = after.replace(/^\\s*```\\n?/, '');
        let cleanedBefore = before.replace(/```json\\s*$/, '');
        
        displayContent = cleanedBefore + `\\n> ⚙️ _Executed internal tool: ${m.name}_\\n` + cleanedAfter;
      }
    }
  }

  return (
    <div className="text-[15px] max-w-none break-words">
      <ReactMarkdown 
        remarkPlugins={[remarkGfm]} 
        components={MarkdownComponents}
      >
        {displayContent}
      </ReactMarkdown>
    </div>
  );
"""

content = content.replace(old_fallback, new_fallback)

with open('frontend/src/app/conversations/page.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated page.tsx with ReactMarkdown!")
