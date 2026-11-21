import os
page_content = """'use client';

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
      await startStreaming(runId, convId);
    } catch (err: any) {
      setStreamContent(`[System Error: ${err.message}]`);
      setIsLoading(false);
    }
  };

  const startStreaming = async (runId: string, convId: string) => {
    const token = localStorage.getItem('token') || '';
    
    try {
      const response = await fetch(`/api/v1/runs/${runId}/stream`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!response.ok) throw new Error('Stream failed to connect');
      
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      
      if (reader) {
        let buffer = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          
          const lines = buffer.split('\\n');
          buffer = lines.pop() || '';
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.replace('data: ', '').trim();
              if (!dataStr) continue;
              try {
                const payload = JSON.parse(dataStr);
                if (payload.event_type === 'content_delta') {
                  setStreamContent((prev) => prev + payload.content);
                } else if (payload.event_type === 'STREAM_END') {
                  // Stream naturally ended
                }
              } catch (e) {
                // Ignore parse errors on partial chunks
              }
            }
          }
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
          if (statusData.error_message) {
            setStreamContent((prev) => prev + `\\n\\n? Error: ${statusData.error_message}`);
          }
        }
      }
      
      await loadMessages(convId);
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
      await startStreaming(currentRunId, activeId);
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
      await startStreaming(currentRunId, activeId);
    } catch(e) {
      console.error(e);
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-white">
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
                {[
                  "Analyze our recent API performance",
                  "Summarize company knowledge",
                  "Investigate a customer issue",
                  "Create a quotation draft for Acme Corp."
                ].map((prompt, i) => (
                  <button
                    key={i}
                    onClick={() => handleSend(prompt)}
                    className="p-4 text-sm text-gray-700 bg-white border border-gray-200 rounded-xl hover:border-blue-300 hover:shadow-md transition-all text-left shadow-sm"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[80%] rounded-2xl px-5 py-3.5 ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'bg-gray-100 text-gray-900 border border-gray-200 shadow-sm'
                }`}
              >
                <div className="whitespace-pre-wrap leading-relaxed text-[15px]">{msg.content}</div>
              </div>
            </div>
          ))}

          {/* Streaming Bubble */}
          {(isLoading || streamContent) && (
            <div className="flex justify-start">
              <div className="max-w-[80%] rounded-2xl px-5 py-3.5 bg-gray-100 text-gray-900 border border-gray-200 shadow-sm">
                <div className="whitespace-pre-wrap leading-relaxed text-[15px]">
                  {streamContent || (
                    <span className="flex items-center text-gray-500 gap-2">
                      <ArrowPathIcon className="h-4 w-4 animate-spin" />
                      AURA is thinking...
                    </span>
                  )}
                </div>
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
  );
}
"""
with open('frontend/src/app/conversations/page.tsx', 'w', encoding='utf-8') as f:
    f.write(page_content)
