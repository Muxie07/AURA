'use client';

import React, { useState, useEffect, useRef } from 'react';
import { 
  PaperAirplaneIcon, 
  PlusIcon, 
  ChatBubbleLeftIcon, 
  BoltIcon, 
  ArrowPathIcon,
  ShieldCheckIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';
import { fetchApi } from '../lib/api';

interface Conversation {
  id: string;
  title: string;
  created_at: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at?: string;
}

interface Approval {
  id: string;
  agent_run_id: string;
  action_summary: string;
  status: string;
}




// Self-contained inline Markdown renderer — no external packages required.
// Handles: headings, bold, italic, inline code, code blocks, bullet/numbered lists,
// blockquotes, tables (GFM), and plain paragraphs.
function renderMarkdown(text: string): React.ReactNode {
  if (!text) return null;

  // Split into blocks separated by blank lines
  const lines = text.split('\n');
  const blocks: React.ReactNode[] = [];
  let i = 0;
  let blockKey = 0;

  const nextKey = () => `md-${blockKey++}`;

  // Render inline markdown within a single line of text
  const renderInline = (line: string): React.ReactNode => {
    // Regex to match bold, italic, inline code in order
    const parts: React.ReactNode[] = [];
    const pattern = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|__[^_]+__)/g;
    let last = 0;
    let m: RegExpExecArray | null;
    let idx = 0;
    while ((m = pattern.exec(line)) !== null) {
      if (m.index > last) parts.push(<span key={idx++}>{line.slice(last, m.index)}</span>);
      const token = m[0];
      if (token.startsWith('`')) {
        parts.push(<code key={idx++} className="bg-gray-100 text-pink-600 px-1.5 py-0.5 rounded text-sm font-mono">{token.slice(1, -1)}</code>);
      } else if (token.startsWith('**') || token.startsWith('__')) {
        parts.push(<strong key={idx++} className="font-semibold text-inherit">{renderInline(token.slice(2, -2))}</strong>);
      } else if (token.startsWith('*') || token.startsWith('_')) {
        parts.push(<em key={idx++}>{renderInline(token.slice(1, -1))}</em>);
      }
      last = m.index + token.length;
    }
    if (last < line.length) parts.push(<span key={idx++}>{line.slice(last)}</span>);
    return parts.length === 1 && typeof parts[0] === 'string' ? parts[0] : <>{parts}</>;
  };

  while (i < lines.length) {
    const line = lines[i];

    // Fenced code block
    if (line.startsWith('```')) {
      const lang = line.slice(3).trim();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // skip closing ```
      blocks.push(
        <div key={nextKey()} className="bg-gray-800 text-gray-100 rounded-lg overflow-x-auto mb-4 text-sm font-mono leading-relaxed">
          <div className="px-3 py-1.5 border-b border-gray-700 text-gray-400 text-xs">{lang || 'code'}</div>
          <pre className="p-4 overflow-x-auto"><code>{codeLines.join('\n')}</code></pre>
        </div>
      );
      continue;
    }

    // ATX Headings
    const headingMatch = line.match(/^(#{1,6})\s+(.+)/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const headingText = headingMatch[2];
      const cls = [
        'text-xl font-bold mt-5 mb-2 text-gray-900',
        'text-lg font-bold mt-5 mb-2 text-gray-900',
        'text-base font-bold mt-4 mb-2 text-gray-900',
        'text-sm font-bold mt-3 mb-1 text-gray-900',
        'text-sm font-semibold mt-3 mb-1 text-gray-900',
        'text-sm font-semibold mt-2 mb-1 text-gray-700',
      ][level - 1] || 'font-bold';
      const headingTagMap: Record<number, React.ElementType> = { 1: 'h1', 2: 'h2', 3: 'h3', 4: 'h4', 5: 'h5', 6: 'h6' };
      const Tag = headingTagMap[level] || 'h3';
      blocks.push(React.createElement(Tag, { key: nextKey(), className: cls }, renderInline(headingText)));
      i++;
      continue;
    }

    // Blockquote
    if (line.startsWith('> ')) {
      const quoteLines: string[] = [];
      while (i < lines.length && lines[i].startsWith('> ')) {
        quoteLines.push(lines[i].slice(2));
        i++;
      }
      blocks.push(
        <blockquote key={nextKey()} className="border-l-4 border-blue-300 pl-4 py-1 bg-blue-50 rounded-r-lg my-3 text-gray-600 italic">
          {quoteLines.map((ql, qi) => <p key={qi} className="leading-relaxed">{renderInline(ql)}</p>)}
        </blockquote>
      );
      continue;
    }

    // Unordered list
    if (/^[-*+]\s/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^[-*+]\s/.test(lines[i])) {
        items.push(lines[i].slice(2));
        i++;
      }
      blocks.push(
        <ul key={nextKey()} className="list-disc pl-6 mb-4 space-y-1.5 text-gray-800">
          {items.map((item, ii) => <li key={ii} className="leading-relaxed">{renderInline(item)}</li>)}
        </ul>
      );
      continue;
    }

    // Ordered list
    if (/^\d+\.\s/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\d+\.\s/.test(lines[i])) {
        items.push(lines[i].replace(/^\d+\.\s/, ''));
        i++;
      }
      blocks.push(
        <ol key={nextKey()} className="list-decimal pl-6 mb-4 space-y-1.5 text-gray-800">
          {items.map((item, ii) => <li key={ii} className="leading-relaxed">{renderInline(item)}</li>)}
        </ol>
      );
      continue;
    }

    // GFM Table: rows starting with |
    if (line.startsWith('|')) {
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].startsWith('|')) {
        tableLines.push(lines[i]);
        i++;
      }
      // Filter out separator rows (---|---|---)
      const headerRow = tableLines[0];
      const dataRows = tableLines.slice(2); // skip header + separator
      const parseRow = (row: string) =>
        row.split('|').slice(1, -1).map(cell => cell.trim());
      const headers = parseRow(headerRow);
      blocks.push(
        <div key={nextKey()} className="overflow-x-auto mb-4 border border-gray-200 rounded-lg shadow-sm">
          <table className="w-full text-sm text-left">
            <thead className="bg-gray-50 text-gray-600 font-semibold border-b border-gray-200">
              <tr>{headers.map((h, hi) => <th key={hi} className="px-4 py-3">{renderInline(h)}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {dataRows.map((row, ri) => (
                <tr key={ri} className="hover:bg-gray-50 transition-colors">
                  {parseRow(row).map((cell, ci) => <td key={ci} className="px-4 py-3">{renderInline(cell)}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    // Horizontal rule
    if (/^[-*_]{3,}$/.test(line.trim())) {
      blocks.push(<hr key={nextKey()} className="border-gray-200 my-4" />);
      i++;
      continue;
    }

    // Blank line — skip
    if (line.trim() === '') {
      i++;
      continue;
    }

    // Paragraph: accumulate non-blank, non-special lines
    const paraLines: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() !== '' &&
      !lines[i].startsWith('#') &&
      !lines[i].startsWith('```') &&
      !lines[i].startsWith('> ') &&
      !/^[-*+]\s/.test(lines[i]) &&
      !/^\d+\.\s/.test(lines[i]) &&
      !lines[i].startsWith('|') &&
      !/^[-*_]{3,}$/.test(lines[i].trim())
    ) {
      paraLines.push(lines[i]);
      i++;
    }
    if (paraLines.length > 0) {
      blocks.push(
        <p key={nextKey()} className="mb-3 leading-relaxed last:mb-0 text-gray-800">
          {paraLines.map((pl, pli) => (
            <React.Fragment key={pli}>
              {pli > 0 && <br />}
              {renderInline(pl)}
            </React.Fragment>
          ))}
        </p>
      );
    }
  }

  return <>{blocks}</>;
}



const QUICK_ACTIONS = [
  {
    label: "API Latency",
    prompt: "Investigate our recent API latency."
  },
  {
    label: "Support Policy",
    prompt: "Summarize our customer support policy."
  },
  {
    label: "P1 Incident",
    prompt: "Find the procedure for handling a P1 incident."
  },
  {
    label: "Create Quotation",
    prompt: "Create a draft quotation for Acme Technologies."
  }
];

const renderMessageContent = (content: string) => {
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
        escapeNext = (!escapeNext && char === '\\');
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
          escapeNext = (!escapeNext && char === '\\');
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

  
  let displayContent = content;
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

  return (
    <div className="text-[15px] max-w-none break-words">
      {renderMarkdown(displayContent)}
    </div>
  );

};

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [streamContent, setStreamContent] = useState('');
  const [pendingApproval, setPendingApproval] = useState<Approval | null>(null);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    if (activeId) {
      loadMessages(activeId);
      setStreamContent('');
      setPendingApproval(null);
    } else {
      setMessages([]);
    }
  }, [activeId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamContent, isLoading, pendingApproval]);

  const scrollToBottom = () => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadConversations = async () => {
    try {
      const res = await fetchApi('/conversations');
      if (res.ok) {
        const data = await res.json();
        setConversations(data.items || []);
      }
    } catch (e) {
      console.error('Failed to load conversations', e);
    }
  };

  const loadMessages = async (id: string) => {
    try {
      const res = await fetchApi(`/conversations/${id}/messages`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data.items || []);
      }
    } catch (e) {
      console.error('Failed to load messages', e);
    }
  };

  const handleSend = async (forcedText?: string) => {
    const text = forcedText || input;
    if (!text.trim()) return;

    setInput('');
    setIsLoading(true);
    setStreamContent('');
    setPendingApproval(null);

    // Optimistic UI for user message
    const tempMsg: Message = { id: Date.now().toString(), role: 'user', content: text };
    setMessages((prev) => [...prev, tempMsg]);

    let convId = activeId;
    
    try {
      // 1. Create conversation if new
      if (!convId) {
        const title = text.slice(0, 40) + '...';
        const cRes = await fetchApi('/conversations', { 
          method: 'POST', 
          body: JSON.stringify({ title }) 
        });
        if (cRes.ok) {
          const cData = await cRes.json();
          convId = cData.id;
          setActiveId(convId);
          await loadConversations();
        } else {
          throw new Error('Failed to create conversation');
        }
      }

      // 2. Start Agent Run
      const rRes = await fetchApi('/runs', { 
        method: 'POST', 
        body: JSON.stringify({ conversation_id: convId, request: text }) 
      });
      if (!rRes.ok) throw new Error('Failed to start agent execution');
      
      const rData = await rRes.json();
      const runId = rData.run_id;
      setCurrentRunId(runId);

      // 3. Connect to Stream
      await startStreaming(runId, convId!);
    } catch (err: any) {
      setStreamContent(`[System Error: ${err.message}]`);
      setIsLoading(false);
    }
  };


  const startStreaming = async (runId: string, convId: string) => {
    const token = localStorage.getItem('token') || '';
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    
    try {
      const response = await fetch(`${API_URL}/runs/${runId}/stream`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!response.ok) {
        throw new Error(`Stream failed to connect: ${response.status}`);
      }
      
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      
      if (reader) {
        let buffer = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          
          const chunks = buffer.split('\n\n');
          buffer = chunks.pop() || '';
          
          let streamEnded = false;
          for (const chunk of chunks) {
            const lines = chunk.split('\n');
            let dataStr = '';
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                dataStr += line.slice(6);
              }
            }
            if (dataStr) {
              try {
                const payload = JSON.parse(dataStr);
                if (payload.event_type === 'content_delta') {
                  setStreamContent((prev) => prev + payload.content);
                } else if (payload.event_type === 'STREAM_END') {
                  streamEnded = true;
                  break;
                } else if (payload.event_type === 'NODE_STARTED') {
                  if (payload.component !== 'DecisionNode') {
                     setStreamContent((prev) => prev + `

[?? Action: ${payload.component} running...]`);
                  }
                } else if (payload.event_type === 'NODE_COMPLETED') {
                  if (payload.component !== 'DecisionNode') {
                     setStreamContent((prev) => prev + `
[? ${payload.component} completed]`);
                  }
                } else if (payload.event_type === 'plan_created') {
                  setStreamContent((prev) => prev + `

[?? AURA mapped out a plan]`);
                }
              } catch (e) {
                // Ignore parse errors on partial chunks
              }
            }
          }
          if (streamEnded) break;
        }
      }
    } catch (e) {
      console.error("Stream error", e);
    }

    // After stream closes, determine final state
    try {
      const statusRes = await fetchApi(`/runs/${runId}`);
      if (statusRes.ok) {
        const statusData = await statusRes.json();
        const st = statusData.status.toLowerCase();
        
        if (st === 'awaiting_approval') {
          const appRes = await fetchApi('/approvals');
          if (appRes.ok) {
            const appData = await appRes.json();
            const approval = appData.items.find((a: any) => a.agent_run_id === runId && a.status === 'pending');
            if (approval) setPendingApproval(approval);
          }
        } else if (st === 'failed') {
          let errorMsg = statusData.error_message || 'Unknown error';
          setStreamContent((prev) => prev + '\n\n❌ Error: ' + errorMsg);
          await loadMessages(convId);
          return;
        }
      }
      
      await loadMessages(convId);
      setStreamContent('');
    } catch(e) {

      console.error(e);
    }
    
    setIsLoading(false);
  };

  const handleApprove = async () => {
    if (!pendingApproval || !currentRunId || !activeId) return;
    setIsLoading(true);
    const appId = pendingApproval.id;
    setPendingApproval(null);
    try {
      await fetchApi(`/approvals/${appId}/approve`, { method: 'POST', body: JSON.stringify({}) });
      await startStreaming(currentRunId, activeId!);
    } catch(e) {
      console.error(e);
      setIsLoading(false);
    }
  };

  const handleReject = async () => {
    if (!pendingApproval || !currentRunId || !activeId) return;
    setIsLoading(true);
    const appId = pendingApproval.id;
    setPendingApproval(null);
    try {
      await fetchApi(`/approvals/${appId}/reject`, { method: 'POST', body: JSON.stringify({ reason: "User rejected" }) });
      await startStreaming(currentRunId, activeId!);
    } catch(e) {
      console.error(e);
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      <div className="mb-6 shrink-0">
        <h1 className="text-2xl font-bold text-gray-900">Conversations</h1>
        <p className="text-sm text-gray-500 mt-1">Interact with AURA or review past AI task threads.</p>
      </div>
      <div className="flex flex-1 overflow-hidden border border-gray-200 rounded-xl bg-white shadow-sm">
      {/* Left Sidebar */}
      <div className="w-80 border-r border-gray-200 flex flex-col bg-gray-50/50">
        <div className="p-4 border-b border-gray-200">
          <button
            onClick={() => setActiveId(null)}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 shadow-sm transition-colors"
          >
            <PlusIcon className="h-5 w-5" />
            New Conversation
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {conversations.map((conv) => (
            <button
              key={conv.id}
              onClick={() => setActiveId(conv.id)}
              className={`flex w-full flex-col items-start gap-1 rounded-lg p-3 text-left transition-colors ${
                activeId === conv.id ? 'bg-blue-50 border border-blue-100 shadow-sm' : 'hover:bg-gray-100 border border-transparent'
              }`}
            >
              <div className="flex w-full items-center gap-2">
                <ChatBubbleLeftIcon className={`h-4 w-4 ${activeId === conv.id ? 'text-blue-600' : 'text-gray-500'}`} />
                <span className={`truncate text-sm font-medium ${activeId === conv.id ? 'text-blue-900' : 'text-gray-700'}`}>
                  {conv.title || 'New Conversation'}
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Right Panel - Chat */}
      <div className="flex-1 flex flex-col min-w-0 bg-white">
        {/* Header */}
        {activeId && (
          <div className="flex items-center px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-800">
              {conversations.find((c) => c.id === activeId)?.title || 'Conversation'}
            </h2>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {!activeId && messages.length === 0 && !isLoading && (
            <div className="flex h-full flex-col items-center justify-center space-y-8 max-w-2xl mx-auto text-center">
              <div className="h-16 w-16 bg-blue-100 text-blue-600 rounded-2xl flex items-center justify-center shadow-inner">
                <BoltIcon className="h-8 w-8" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-gray-900">How can AURA help?</h2>
                <p className="mt-2 text-gray-500">Select a prompt below to get started or type your own request.</p>
              </div>
              <div className="grid grid-cols-2 gap-4 w-full">
                {QUICK_ACTIONS.map((action, i) => (
                  <button
                    key={i}
                    onClick={() => handleSend(action.prompt)}
                    className="p-4 text-sm text-gray-700 bg-white border border-gray-200 rounded-xl hover:border-blue-300 hover:shadow-md transition-all text-left shadow-sm"
                  >
                    {action.prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => {
            const isQuotationMsg =
              msg.role === 'assistant' &&
              msg.content.includes('quotation.create_draft') &&
              msg.content.includes('quotation_id');

            if (isQuotationMsg) {
              return (
                <div key={msg.id} className="flex justify-start w-full">
                  {renderMessageContent(msg.content)}
                </div>
              );
            }

            return (
              <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[80%] rounded-2xl px-5 py-3.5 ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white shadow-md'
                      : 'bg-gray-100 text-gray-900 border border-gray-200 shadow-sm'
                  }`}
                >
                  {renderMessageContent(msg.content)}
                </div>
              </div>
            );
          })}

          {/* Streaming Bubble */}
          {(isLoading || streamContent) && (
            <div className="flex justify-start">
              <div className="max-w-[80%] rounded-2xl px-5 py-3.5 bg-gray-100 text-gray-900 border border-gray-200 shadow-sm">
                {streamContent ? renderMessageContent(streamContent) : (
                <div className="whitespace-pre-wrap leading-relaxed text-[15px]">
                    <span className="flex items-center text-gray-500 gap-2">
                      <ArrowPathIcon className="h-4 w-4 animate-spin" />
                      AURA is thinking...
                    </span>
                </div>
                )}
              </div>
            </div>
          )}

          {/* Approval Inline UI */}
          {pendingApproval && (
            <div className="flex justify-start">
               <div className="max-w-[80%] rounded-xl px-5 py-4 bg-amber-50 border border-amber-200 shadow-sm">
                  <div className="flex items-center gap-2 text-amber-800 font-semibold mb-2">
                     <ShieldCheckIcon className="h-5 w-5" />
                     AURA needs your approval before continuing.
                  </div>
                  <p className="text-amber-700 text-sm mb-4">
                     Action: <strong>{pendingApproval.action_summary}</strong>
                  </p>
                  <div className="flex gap-3">
                     <button onClick={handleApprove} className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-sm font-medium shadow-sm transition-colors">
                        Approve Action
                     </button>
                     <button onClick={handleReject} className="px-4 py-2 bg-white hover:bg-gray-50 text-gray-700 border border-gray-300 rounded-lg text-sm font-medium shadow-sm transition-colors">
                        Reject
                     </button>
                  </div>
               </div>
            </div>
          )}

          <div ref={scrollRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-gray-200 bg-white">
          {/* Active Conversation Quick Actions */}
          {activeId && (
            <div className="mx-auto max-w-4xl mb-3">
              <div className="text-xs font-medium text-gray-500 mb-2">Quick actions</div>
              <div className="flex flex-wrap gap-2 pb-1">
                {QUICK_ACTIONS.map((action, i) => (
                  <button
                    key={i}
                    onClick={() => handleSend(action.prompt)}
                    disabled={isLoading || !!pendingApproval}
                    className="rounded-full border border-gray-200 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-blue-50 hover:text-blue-600 hover:border-blue-200 transition-colors shadow-sm disabled:opacity-50 whitespace-nowrap"
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="mx-auto max-w-4xl relative flex items-center">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  if (!isLoading && !pendingApproval) handleSend();
                }
              }}
              placeholder="Ask AURA anything..."
              disabled={isLoading || !!pendingApproval}
              className="w-full resize-none rounded-2xl border-0 bg-gray-100 py-4 pl-5 pr-14 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-200 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm sm:leading-6"
              rows={1}
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || isLoading || !!pendingApproval}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded-xl p-2 text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 transition-colors shadow-sm"
            >
              <PaperAirplaneIcon className="h-5 w-5" />
            </button>
          </div>
          <div className="text-center mt-2">
            <span className="text-xs text-gray-400">AURA can execute actions and retrieve internal knowledge. Verify important information.</span>
          </div>
        </div>
      </div>
    </div>
  </div>
  );
}
