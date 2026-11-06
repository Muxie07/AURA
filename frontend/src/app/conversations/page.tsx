'use client';

import React, { useState, useEffect, useRef } from 'react';
import { 
  PaperAirplaneIcon, 
  PlusIcon, 
  ChatBubbleLeftIcon, 
  BoltIcon, 
  ArrowPathIcon,
  ShieldCheckIcon,
  XMarkIcon,
  PrinterIcon,
  DocumentTextIcon,
  CheckBadgeIcon,
  BuildingOfficeIcon
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

  // Split into blocks separated by blank lines (capped at 250 lines for instant responsiveness)
  const allLines = text.split('\n');
  const isTruncated = allLines.length > 250;
  const lines = isTruncated ? allLines.slice(0, 250) : allLines;
  const blocks: React.ReactNode[] = [];
  let i = 0;
  let blockKey = 0;

  const nextKey = () => `md-${blockKey++}`;

  // Render inline markdown within a single line of text (non-recursive, linear pass)
  const renderInline = (line: string): React.ReactNode => {
    if (!line) return '';
    // Single-pass linear tokenization without recursion to prevent UI thread lockup
    const parts: React.ReactNode[] = [];
    const pattern = /(`[^`]+`|\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*|_[^_]+_)/g;
    let last = 0;
    let m: RegExpExecArray | null;
    let idx = 0;
    while ((m = pattern.exec(line)) !== null) {
      if (m.index > last) parts.push(<span key={idx++}>{line.slice(last, m.index)}</span>);
      const token = m[0];
      if (token.startsWith('`')) {
        parts.push(<code key={idx++} className="bg-gray-100 text-pink-600 px-1.5 py-0.5 rounded text-sm font-mono">{token.slice(1, -1)}</code>);
      } else if (token.startsWith('**') || token.startsWith('__')) {
        parts.push(<strong key={idx++} className="font-semibold text-inherit">{token.slice(2, -2)}</strong>);
      } else if (token.startsWith('*') || token.startsWith('_')) {
        parts.push(<em key={idx++}>{token.slice(1, -1)}</em>);
      }
      last = m.index + token.length;
    }
    if (last < line.length) parts.push(<span key={idx++}>{line.slice(last)}</span>);
    return parts.length === 0 ? '' : parts.length === 1 && typeof parts[0] === 'string' ? parts[0] : <>{parts}</>;
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
      const allDataRows = tableLines.slice(2); // skip header + separator
      const dataRows = allDataRows.slice(0, 50); // cap preview to 50 rows to keep DOM ultra responsive
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
          {allDataRows.length > 50 && (
            <div className="bg-gray-50 px-4 py-2 border-t border-gray-200 text-xs text-gray-500 italic">
              Showing first 50 of {allDataRows.length} entries.
            </div>
          )}
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

  if (isTruncated) {
    blocks.push(
      <div key={nextKey()} className="text-xs text-gray-500 italic mt-3 bg-gray-50 p-2.5 rounded-lg border border-gray-200">
        [Note: Long document output truncated for responsiveness — showing first 250 lines]
      </div>
    );
  }

  return <>{blocks}</>;
}



interface InvoiceSelectorCardProps {
  data: any;
  onSend?: (text: string) => void;
  isLoading?: boolean;
}

function InvoiceSelectorCard({ data, onSend, isLoading }: InvoiceSelectorCardProps) {
  const defaultCompanies = [
    { name: "Acme Technologies", email: "contact@acme.com", address: "100 Innovation Way, Austin, TX" },
    { name: "Global Telecom Ltd", email: "procurement@globaltelecom.com", address: "Cyber City, Gurugram, HR" },
    { name: "Nexa Communications", email: "billing@nexacomms.in", address: "Electronic City, Bangalore, KA" },
    { name: "Apex Enterprise", email: "finance@apexenterprise.com", address: "Financial District, Hyderabad, TS" },
    { name: "Cloud Infotech Partner", email: "sales@cloudinfotech.com", address: "Sector 63, Noida, UP" },
  ];

  const defaultProducts = [
    { model: "UC-2000-VE-2T", category: "DINSTAR GSM/VoLTE Gateway", desc: "2 Port GSM Volte Gateway", price: 31763 },
    { model: "UC-2000-VE-4T", category: "DINSTAR GSM/VoLTE Gateway", desc: "4 Port GSM Volte Gateway", price: 42350 },
    { model: "UC-2000-VE-8T", category: "DINSTAR GSM/VoLTE Gateway", desc: "8 Port GSM Volte Gateway", price: 74488 },
    { model: "UC-2000-VF-16T", category: "DINSTAR GSM/VoLTE Gateway", desc: "16 Port GSM Volte Gateway Enterprise", price: 135520 },
    { model: "UC-2000-VG-32T", category: "DINSTAR GSM/VoLTE Gateway", desc: "32 Port GSM Volte Gateway High Density", price: 181500 },
    { model: "DAG1000-2S", category: "DINSTAR FXS/FXO Gateway", desc: "2 Port ATA Analog VoIP Gateway", price: 4235 },
    { model: "DAG1000-4S", category: "DINSTAR FXS/FXO Gateway", desc: "4 FXS Gateway (G.711A/U, Echo Cancel)", price: 8894 },
    { model: "DAG1000-8S", category: "DINSTAR FXS/FXO Gateway", desc: "8 FXS Gateway with Echo Cancellation", price: 15246 },
    { model: "DAG2000-16S", category: "DINSTAR FXS/FXO Gateway", desc: "16 FXS Analog VoIP Gateway Rackmount", price: 25410 },
    { model: "DAG2000-24S", category: "DINSTAR FXS/FXO Gateway", desc: "24 FXS Analog VoIP Gateway Rackmount", price: 29040 },
    { model: "DAG1000-4S4O", category: "DINSTAR Hybrid Gateway", desc: "4 FXS + 4 FXO Hybrid Gateway", price: 18755 },
    { model: "DAG1000-8S8O", category: "DINSTAR Hybrid Gateway", desc: "8 FXS + 8 FXO Hybrid Gateway", price: 35090 },
    { model: "UC120 Series", category: "DINSTAR IP PBX", desc: "IPPBX, 2FXO, 60 Concurrent Calls", price: 15246 },
    { model: "UC200 Series", category: "DINSTAR IP PBX", desc: "IPPBX, 2FXS+2FXO, High Capacity", price: 31763 },
    { model: "SBC300-10", category: "Session Border Controller", desc: "10 concurrent calls & 10 transcoding", price: 44165 },
    { model: "SBC300-20", category: "Session Border Controller", desc: "20 concurrent calls & 20 transcoding", price: 56628 },
    { model: "SBC1000-050", category: "Session Border Controller", desc: "50 concurrent calls & 50 transcoding", price: 222398 },
    { model: "SBC3000 Chassis", category: "Session Border Controller", desc: "SBC3000 Chassis + MCU (Dual backup)", price: 329967 }
  ];

  const companies = (data && data.companies && data.companies.length > 0) ? data.companies : defaultCompanies;
  const products = (data && data.products && data.products.length > 0) ? data.products : defaultProducts;

  const [selectedCompany, setSelectedCompany] = useState<string>(companies[0]?.name || "Acme Technologies");
  const [customCompanyName, setCustomCompanyName] = useState<string>("");
  const [selectedModel, setSelectedModel] = useState<string>("UC-2000-VE-4T");
  const [selectedTier, setSelectedTier] = useState<string>("end_customer");
  const [quantity, setQuantity] = useState<number>(1);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  useEffect(() => {
    if (!isLoading) {
      setIsSubmitting(false);
    }
  }, [isLoading]);

  const currentProduct = products.find((p: any) => p.model === selectedModel) || products[0];

  let unitRate = currentProduct?.price || 42350;
  if (selectedTier === "retail") {
    unitRate = Math.round(unitRate * 0.909);
  } else if (selectedTier === "msp") {
    unitRate = Math.round(unitRate * 0.826);
  } else if (selectedTier === "mrp") {
    unitRate = Math.round(unitRate * 1.10);
  }

  const subtotal = unitRate * quantity;
  const gst18 = Math.round(subtotal * 0.18);
  const grandTotal = subtotal + gst18;

  const finalCompanyName = selectedCompany === "__custom__" ? (customCompanyName.trim() || "Client Enterprise") : selectedCompany;

  const handleGenerate = () => {
    if (isSubmitting || isLoading) return;
    setIsSubmitting(true);
    const prompt = `Generate official tax invoice for ${finalCompanyName} for ${quantity} units of ${selectedModel} at ${selectedTier} tier`;
    if (onSend) {
      onSend(prompt);
    }
    setTimeout(() => {
      setIsSubmitting(false);
    }, 2500);
  };

  const formatInr = (n: number) => n.toLocaleString('en-IN');

  return (
    <div className="my-3 w-full max-w-2xl bg-white border border-blue-200 shadow-lg rounded-2xl overflow-hidden font-sans text-gray-800">
      <div className="bg-gradient-to-r from-blue-700 via-indigo-700 to-blue-800 px-5 py-3.5 text-white flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="p-1.5 bg-white/10 rounded-lg">
            <DocumentTextIcon className="w-5 h-5 text-blue-200" />
          </div>
          <div>
            <h3 className="font-bold text-sm tracking-wide">Interactive Invoice Configurator</h3>
            <p className="text-[11px] text-blue-200">Cloud Infotech Distribution • DINSTAR Authorized Catalog</p>
          </div>
        </div>
        <span className="text-[10px] bg-white/20 text-white font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider">
          AI Guided
        </span>
      </div>

      <div className="p-5 space-y-4">
        <p className="text-xs text-gray-600">
          Select client company and product specifications below to generate a compliant Tax Invoice with automatic 18% GST calculation, 3-year warranty, and FOC shipping:
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
          <div className="space-y-1">
            <label className="text-[11px] font-bold text-gray-700 uppercase tracking-wider block">
              1. Billed To (Company)
            </label>
            <select
              value={selectedCompany}
              onChange={(e) => setSelectedCompany(e.target.value)}
              className="w-full text-xs bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-gray-800 font-medium focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:bg-white transition-all cursor-pointer"
            >
              {companies.map((c: any, i: number) => (
                <option key={i} value={c.name}>
                  {c.name} {c.email ? `(${c.email})` : ''}
                </option>
              ))}
              <option value="__custom__">+ Enter Custom Company Name...</option>
            </select>
            {selectedCompany === "__custom__" && (
              <input
                type="text"
                placeholder="Enter client company name..."
                value={customCompanyName}
                onChange={(e) => setCustomCompanyName(e.target.value)}
                className="w-full mt-1.5 text-xs bg-white border border-blue-300 rounded-lg px-3 py-1.5 text-gray-800 placeholder-gray-400 focus:ring-2 focus:ring-blue-500"
              />
            )}
          </div>

          <div className="space-y-1">
            <label className="text-[11px] font-bold text-gray-700 uppercase tracking-wider block">
              2. Hardware Product Model
            </label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full text-xs bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-gray-800 font-medium focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:bg-white transition-all cursor-pointer"
            >
              <optgroup label="GSM / VoLTE Gateways">
                <option value="UC-2000-VE-2T">UC-2000-VE-2T (2 Port Volte)</option>
                <option value="UC-2000-VE-4T">UC-2000-VE-4T (4 Port Volte)</option>
                <option value="UC-2000-VE-8T">UC-2000-VE-8T (8 Port Volte)</option>
                <option value="UC-2000-VF-16T">UC-2000-VF-16T (16 Port Volte Enterprise)</option>
                <option value="UC-2000-VG-32T">UC-2000-VG-32T (32 Port High Density)</option>
              </optgroup>
              <optgroup label="FXS / FXO Analog Gateways">
                <option value="DAG1000-2S">DAG1000-2S (2 Port ATA)</option>
                <option value="DAG1000-4S">DAG1000-4S (4 FXS Gateway)</option>
                <option value="DAG1000-8S">DAG1000-8S (8 FXS Gateway)</option>
                <option value="DAG2000-16S">DAG2000-16S (16 FXS Gateway Rackmount)</option>
                <option value="DAG2000-24S">DAG2000-24S (24 FXS Gateway Rackmount)</option>
                <option value="DAG1000-4S4O">DAG1000-4S4O (4 FXS + 4 FXO)</option>
                <option value="DAG1000-8S8O">DAG1000-8S8O (8 FXS + 8 FXO)</option>
              </optgroup>
              <optgroup label="IP PBX Systems">
                <option value="UC120 Series">UC120 Series (IP PBX 2FXO)</option>
                <option value="UC200 Series">UC200 Series (IP PBX 2FXS+2FXO)</option>
              </optgroup>
              <optgroup label="Session Border Controllers (SBC)">
                <option value="SBC300-10">SBC300-10 (10 Concurrent Calls)</option>
                <option value="SBC300-20">SBC300-20 (20 Concurrent Calls)</option>
                <option value="SBC1000-050">SBC1000-050 (50 Concurrent Calls)</option>
                <option value="SBC3000 Chassis">SBC3000 Chassis (Carrier Dual MCU)</option>
              </optgroup>
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-[11px] font-bold text-gray-700 uppercase tracking-wider block">
              3. Commercial Pricing Tier
            </label>
            <select
              value={selectedTier}
              onChange={(e) => setSelectedTier(e.target.value)}
              className="w-full text-xs bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-gray-800 font-medium focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:bg-white transition-all cursor-pointer"
            >
              <option value="end_customer">End-Customer Price (Standard)</option>
              <option value="retail">Retail Price (Reseller / Dealer)</option>
              <option value="msp">MSP (National Distributor Base)</option>
              <option value="mrp">MRP (Maximum Retail Price)</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-[11px] font-bold text-gray-700 uppercase tracking-wider block">
              4. Order Quantity
            </label>
            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={() => setQuantity(Math.max(1, quantity - 1))}
                className="w-9 h-9 flex items-center justify-center rounded-lg border border-gray-300 bg-gray-50 text-gray-700 hover:bg-gray-100 font-bold text-base cursor-pointer"
              >
                -
              </button>
              <input
                type="number"
                min="1"
                max="100"
                value={quantity}
                onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                className="w-16 text-center text-xs font-bold bg-white border border-gray-300 rounded-lg py-2 text-gray-900"
              />
              <button
                type="button"
                onClick={() => setQuantity(quantity + 1)}
                className="w-9 h-9 flex items-center justify-center rounded-lg border border-gray-300 bg-gray-50 text-gray-700 hover:bg-gray-100 font-bold text-base cursor-pointer"
              >
                +
              </button>
              <span className="text-[11px] text-gray-500 font-medium">units</span>
            </div>
          </div>
        </div>

        <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 space-y-2">
          <div className="flex justify-between items-center text-xs text-gray-600">
            <span>Selected Item: <strong className="text-gray-900">{selectedModel}</strong> ({currentProduct?.desc || ''})</span>
            <span className="font-semibold text-gray-800">Unit: ₹{formatInr(unitRate)}</span>
          </div>
          <div className="flex justify-between items-center text-xs border-t border-slate-200 pt-2">
            <div className="text-slate-600 space-x-3">
              <span>Subtotal: <strong>₹{formatInr(subtotal)}</strong></span>
              <span>•</span>
              <span>18% GST: <strong>₹{formatInr(gst18)}</strong></span>
            </div>
            <div className="text-right">
              <span className="text-[10px] text-slate-500 uppercase tracking-wide block">Estimated Total</span>
              <span className="text-sm font-black text-blue-700">₹{formatInr(grandTotal)}</span>
            </div>
          </div>

          <div className="flex items-center space-x-3 text-[11px] text-slate-500 pt-1">
            <span className="inline-flex items-center text-emerald-700 font-medium">
              <CheckBadgeIcon className="w-3.5 h-3.5 mr-1" /> 3 Yrs Warranty
            </span>
            <span>•</span>
            <span className="text-slate-600 font-medium">🚚 FOC Surface Transport</span>
            <span>•</span>
            <span className="text-slate-600 font-medium">⏱️ 24x7 Support</span>
          </div>
        </div>

        <div className="pt-1">
          <button
            type="button"
            onClick={handleGenerate}
            disabled={isSubmitting || isLoading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs py-2.5 px-4 rounded-xl shadow-md hover:shadow-lg transition-all flex items-center justify-center space-x-2 cursor-pointer disabled:opacity-50"
          >
            {isSubmitting || isLoading ? (
              <>
                <ArrowPathIcon className="w-4 h-4 animate-spin" />
                <span>Generating Official Tax Invoice...</span>
              </>
            ) : (
              <>
                <DocumentTextIcon className="w-4 h-4" />
                <span>Generate Official Tax Invoice</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

interface QuotationSelectorCardProps {
  data: any;
  onSend?: (text: string) => void;
  isLoading?: boolean;
}

function QuotationSelectorCard({ data, onSend, isLoading }: QuotationSelectorCardProps) {
  const defaultCompanies = [
    { name: "Acme Technologies", email: "contact@acme.com", address: "100 Innovation Way, Austin, TX" },
    { name: "Global Telecom Ltd", email: "procurement@globaltelecom.com", address: "Cyber City, Gurugram, HR" },
    { name: "Nexa Communications", email: "billing@nexacomms.in", address: "Electronic City, Bangalore, KA" },
    { name: "Apex Enterprise", email: "finance@apexenterprise.com", address: "Financial District, Hyderabad, TS" },
    { name: "Cloud Infotech Partner", email: "sales@cloudinfotech.com", address: "Sector 63, Noida, UP" },
  ];

  const defaultProducts = [
    { model: "UC-2000-VE-2T", category: "DINSTAR GSM/VoLTE Gateway", desc: "2 Port GSM Volte Gateway with SIP Trunk", price: 31763 },
    { model: "UC-2000-VE-4T", category: "DINSTAR GSM/VoLTE Gateway", desc: "4 Port GSM Volte Gateway with SIP Trunk", price: 42350 },
    { model: "UC-2000-VE-8T", category: "DINSTAR GSM/VoLTE Gateway", desc: "8 Port GSM Volte Gateway with SIP Trunk", price: 74488 },
    { model: "UC-2000-VF-16T", category: "DINSTAR GSM/VoLTE Gateway", desc: "16 Port GSM Volte Gateway Enterprise", price: 135520 },
    { model: "UC-2000-VG-32T", category: "DINSTAR GSM/VoLTE Gateway", desc: "32 Port GSM Volte Gateway High Density", price: 181500 },
    { model: "DAG1000-2S", category: "DINSTAR FXS/FXO Gateway", desc: "2 Port ATA Analog VoIP Gateway", price: 4235 },
    { model: "DAG1000-4S", category: "DINSTAR FXS/FXO Gateway", desc: "4 FXS Gateway (G.711A/U, Echo Cancel)", price: 8894 },
    { model: "DAG1000-8S", category: "DINSTAR FXS/FXO Gateway", desc: "8 FXS Gateway with Echo Cancellation", price: 15246 },
    { model: "DAG2000-16S", category: "DINSTAR FXS/FXO Gateway", desc: "16 FXS Analog VoIP Gateway Rackmount", price: 25410 },
    { model: "DAG2000-24S", category: "DINSTAR FXS/FXO Gateway", desc: "24 FXS Analog VoIP Gateway Rackmount", price: 29040 },
    { model: "DAG1000-4S4O", category: "DINSTAR Hybrid Gateway", desc: "4 FXS + 4 FXO Hybrid Gateway", price: 18755 },
    { model: "DAG1000-8S8O", category: "DINSTAR Hybrid Gateway", desc: "8 FXS + 8 FXO Hybrid Gateway", price: 35090 },
    { model: "UC120 Series", category: "DINSTAR IP PBX", desc: "IPPBX, 2FXO, 60 Concurrent Calls", price: 15246 },
    { model: "UC200 Series", category: "DINSTAR IP PBX", desc: "IPPBX, 2FXS+2FXO, High Capacity", price: 31763 },
    { model: "SBC300-10", category: "Session Border Controller", desc: "10 concurrent calls & 10 transcoding", price: 44165 },
    { model: "SBC300-20", category: "Session Border Controller", desc: "20 concurrent calls & 20 transcoding", price: 56628 },
    { model: "SBC1000-050", category: "Session Border Controller", desc: "50 concurrent calls & 50 transcoding", price: 222398 },
    { model: "SBC3000 Chassis", category: "Session Border Controller", desc: "SBC3000 Chassis + MCU (Dual backup)", price: 329967 },
    { model: "ENT-DB-001", category: "Enterprise Solutions", desc: "Enterprise Clustered Server Instance", price: 125000 }
  ];

  const companies = (data && data.companies && data.companies.length > 0) ? data.companies : defaultCompanies;
  const products = (data && data.products && data.products.length > 0) ? data.products : defaultProducts;

  const [selectedCompany, setSelectedCompany] = useState<string>(companies[2]?.name || "Nexa Communications");
  const [manualClientName, setManualClientName] = useState<string>("");
  const [useManualInput, setUseManualInput] = useState<boolean>(false);
  const [selectedModel, setSelectedModel] = useState<string>("DAG1000-8S");
  const [selectedTier, setSelectedTier] = useState<string>("retail");
  const [quantity, setQuantity] = useState<number>(2);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  useEffect(() => {
    if (!isLoading) {
      setIsSubmitting(false);
    }
  }, [isLoading]);

  const currentProduct = products.find((p: any) => p.model === selectedModel) || products[0];

  let unitRate = currentProduct?.price || 15246;
  if (selectedTier === "retail") {
    unitRate = Math.round(unitRate * 0.909);
  } else if (selectedTier === "msp") {
    unitRate = Math.round(unitRate * 0.826);
  } else if (selectedTier === "mrp") {
    unitRate = Math.round(unitRate * 1.10);
  }

  const subtotal = unitRate * quantity;
  const finalCompanyName = useManualInput
    ? (manualClientName.trim() || "Client Enterprise")
    : (selectedCompany === "__custom__" ? (manualClientName.trim() || "Client Enterprise") : selectedCompany);

  const handleGenerate = () => {
    if (isSubmitting || isLoading) return;
    setIsSubmitting(true);
    const prompt = `Generate official quotation for ${finalCompanyName} for ${quantity} units of ${selectedModel} at ${selectedTier} tier`;
    if (onSend) {
      onSend(prompt);
    }
    setTimeout(() => {
      setIsSubmitting(false);
    }, 2500);
  };

  const formatInr = (n: number) => n.toLocaleString('en-IN');

  return (
    <div className="my-3 w-full max-w-2xl bg-white border border-indigo-200 shadow-lg rounded-2xl overflow-hidden font-sans text-gray-800">
      <div className="bg-gradient-to-r from-indigo-700 via-blue-700 to-indigo-900 px-5 py-3.5 text-white flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="p-1.5 bg-white/10 rounded-lg">
            <BuildingOfficeIcon className="w-5 h-5 text-indigo-200" />
          </div>
          <div>
            <h3 className="font-bold text-sm tracking-wide">Interactive Quotation Configurator</h3>
            <p className="text-[11px] text-indigo-200">Cloud Infotech Distribution • Official Commercial Quotations</p>
          </div>
        </div>
        <span className="text-[10px] bg-emerald-500/80 text-white font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider">
          Commercial Quote
        </span>
      </div>

      <div className="p-5 space-y-4">
        <p className="text-xs text-gray-600">
          Configure product specifications and client company details below. An official printable Commercial Quotation will be generated with 30-day validity guarantee and 3-year warranty:
        </p>

        {/* Client Selection & Manual Entry */}
        <div className="space-y-2 bg-slate-50 border border-slate-200 p-3.5 rounded-xl">
          <div className="flex items-center justify-between">
            <label className="text-[11px] font-bold text-gray-700 uppercase tracking-wider">
              1. Client / Company Name
            </label>
            <button
              type="button"
              onClick={() => setUseManualInput(!useManualInput)}
              className="text-[11px] text-blue-600 hover:text-blue-800 font-semibold cursor-pointer underline"
            >
              {useManualInput ? "← Select from existing list" : "+ Enter company manually"}
            </button>
          </div>

          {!useManualInput ? (
            <select
              value={selectedCompany}
              onChange={(e) => {
                if (e.target.value === "__custom__") {
                  setUseManualInput(true);
                } else {
                  setSelectedCompany(e.target.value);
                }
              }}
              className="w-full text-xs bg-white border border-gray-300 rounded-lg px-3 py-2 text-gray-800 font-medium focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all cursor-pointer"
            >
              {companies.map((c: any, i: number) => (
                <option key={i} value={c.name}>
                  {c.name} {c.email ? `(${c.email})` : ''}
                </option>
              ))}
              <option value="__custom__">+ Enter Custom Company Name...</option>
            </select>
          ) : (
            <div className="space-y-1">
              <input
                type="text"
                placeholder="Enter client company name (e.g. Nexa Communications, Reliance, Tata)..."
                value={manualClientName}
                onChange={(e) => setManualClientName(e.target.value)}
                autoFocus
                className="w-full text-xs bg-white border border-indigo-400 rounded-lg px-3 py-2 text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 shadow-sm"
              />
              <p className="text-[10px] text-slate-500 italic">Enter the exact legal or trade name for the quotation.</p>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
          {/* Product Model Dropdown */}
          <div className="space-y-1">
            <label className="text-[11px] font-bold text-gray-700 uppercase tracking-wider block">
              2. Hardware Product Catalog
            </label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full text-xs bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-gray-800 font-medium focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 focus:bg-white transition-all cursor-pointer"
            >
              <optgroup label="FXS / FXO Analog Gateways">
                <option value="DAG1000-8S">DAG1000-8S (8 FXS Gateway)</option>
                <option value="DAG1000-4S">DAG1000-4S (4 FXS Gateway)</option>
                <option value="DAG1000-2S">DAG1000-2S (2 Port ATA Gateway)</option>
                <option value="DAG2000-16S">DAG2000-16S (16 FXS Rackmount)</option>
                <option value="DAG2000-24S">DAG2000-24S (24 FXS Rackmount)</option>
                <option value="DAG1000-4S4O">DAG1000-4S4O (4 FXS + 4 FXO)</option>
                <option value="DAG1000-8S8O">DAG1000-8S8O (8 FXS + 8 FXO)</option>
              </optgroup>
              <optgroup label="GSM / VoLTE Gateways">
                <option value="UC-2000-VE-2T">UC-2000-VE-2T (2 Port Volte)</option>
                <option value="UC-2000-VE-4T">UC-2000-VE-4T (4 Port Volte)</option>
                <option value="UC-2000-VE-8T">UC-2000-VE-8T (8 Port Volte)</option>
                <option value="UC-2000-VF-16T">UC-2000-VF-16T (16 Port Enterprise)</option>
                <option value="UC-2000-VG-32T">UC-2000-VG-32T (32 Port High Density)</option>
              </optgroup>
              <optgroup label="IP PBX Systems">
                <option value="UC120 Series">UC120 Series (IP PBX 2FXO)</option>
                <option value="UC200 Series">UC200 Series (IP PBX 2FXS+2FXO)</option>
              </optgroup>
              <optgroup label="Session Border Controllers (SBC)">
                <option value="SBC300-10">SBC300-10 (10 Concurrent Calls)</option>
                <option value="SBC300-20">SBC300-20 (20 Concurrent Calls)</option>
                <option value="SBC1000-050">SBC1000-050 (50 Concurrent Calls)</option>
                <option value="SBC3000 Chassis">SBC3000 Chassis (Carrier Backup)</option>
              </optgroup>
              <optgroup label="Enterprise Solutions">
                <option value="ENT-DB-001">Enterprise Clustered Server Instance</option>
              </optgroup>
            </select>
          </div>

          {/* Pricing Tier Dropdown */}
          <div className="space-y-1">
            <label className="text-[11px] font-bold text-gray-700 uppercase tracking-wider block">
              3. Pricing Tier
            </label>
            <select
              value={selectedTier}
              onChange={(e) => setSelectedTier(e.target.value)}
              className="w-full text-xs bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-gray-800 font-medium focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 focus:bg-white transition-all cursor-pointer"
            >
              <option value="retail">Retail Price (Reseller / Dealer)</option>
              <option value="end_customer">End-Customer Price (Standard)</option>
              <option value="msp">MSP (National Distributor Base)</option>
              <option value="mrp">MRP (Maximum Retail Price)</option>
            </select>
          </div>

          {/* Order Quantity */}
          <div className="space-y-1 sm:col-span-2">
            <label className="text-[11px] font-bold text-gray-700 uppercase tracking-wider block">
              4. Order Quantity
            </label>
            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={() => setQuantity(Math.max(1, quantity - 1))}
                className="w-9 h-9 flex items-center justify-center rounded-lg border border-gray-300 bg-gray-50 text-gray-700 hover:bg-gray-100 font-bold text-base cursor-pointer"
              >
                -
              </button>
              <input
                type="number"
                min="1"
                max="500"
                value={quantity}
                onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                className="w-20 text-center text-xs font-bold bg-white border border-gray-300 rounded-lg py-2 text-gray-900"
              />
              <button
                type="button"
                onClick={() => setQuantity(quantity + 1)}
                className="w-9 h-9 flex items-center justify-center rounded-lg border border-gray-300 bg-gray-50 text-gray-700 hover:bg-gray-100 font-bold text-base cursor-pointer"
              >
                +
              </button>
              <span className="text-[11px] text-gray-500 font-medium">units</span>
            </div>
          </div>
        </div>

        {/* Summary Card */}
        <div className="bg-indigo-50/60 border border-indigo-200 rounded-xl p-3.5 space-y-2">
          <div className="flex justify-between items-center text-xs text-gray-700">
            <span>Selected Model: <strong className="text-gray-900">{selectedModel}</strong> ({currentProduct?.desc || ''})</span>
            <span className="font-semibold text-gray-900">Rate: ₹{formatInr(unitRate)}</span>
          </div>
          <div className="flex justify-between items-center text-xs border-t border-indigo-200/60 pt-2">
            <div className="text-slate-600 space-x-2">
              <span>Client: <strong className="text-gray-800">{finalCompanyName}</strong></span>
              <span>•</span>
              <span>Qty: <strong>{quantity} units</strong></span>
            </div>
            <div className="text-right">
              <span className="text-[10px] text-slate-500 uppercase tracking-wide block">Quotation Total</span>
              <span className="text-base font-black text-indigo-700">₹{formatInr(subtotal)}</span>
            </div>
          </div>

          <div className="flex items-center space-x-3 text-[11px] text-slate-600 pt-1">
            <span className="inline-flex items-center text-emerald-700 font-medium">
              <CheckBadgeIcon className="w-3.5 h-3.5 mr-1" /> 30-Day Price Lock
            </span>
            <span>•</span>
            <span className="text-slate-600 font-medium">🛡️ 3 Years Warranty</span>
            <span>•</span>
            <span className="text-slate-600 font-medium">🚚 Free Surface Transport</span>
          </div>
        </div>

        <div className="pt-1">
          <button
            type="button"
            onClick={handleGenerate}
            disabled={isSubmitting || isLoading}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs py-2.5 px-4 rounded-xl shadow-md hover:shadow-lg transition-all flex items-center justify-center space-x-2 cursor-pointer disabled:opacity-50"
          >
            {isSubmitting || isLoading ? (
              <>
                <ArrowPathIcon className="w-4 h-4 animate-spin" />
                <span>Preparing Official Commercial Quotation...</span>
              </>
            ) : (
              <>
                <BuildingOfficeIcon className="w-4 h-4" />
                <span>Generate Official Quotation</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

interface InvoiceCardProps {
  data: any;
}

function InvoiceCard({ data }: InvoiceCardProps) {
  if (!data) return null;

  const distributor = data.distributor || {
    name: "Cloud Infotech Distribution Pvt. Ltd.",
    subtitle: "Authorized Dinstar National Distributor",
    address: "B-42, Sector 63, Electronic City, Noida, UP 201301",
    gstin: "07AAAAA0000A1Z5",
    email: "invoices@cloudinfotech.com",
    phone: "+91 (120) 456-7890",
  };

  const billedTo = data.billed_to || {
    name: "Acme Technologies",
    address: "100 Innovation Way, Austin, TX",
    gstin: "07AAAAA1234Z1ZP",
    email: "contact@acme.com",
    contact: "+91 98765 43210"
  };

  const items = data.items || [];
  const subtotal = data.subtotal || 0;
  const cgst = data.cgst_9_percent || Math.round((data.gst_18_percent || subtotal * 0.18) / 2);
  const sgst = data.sgst_9_percent || Math.round((data.gst_18_percent || subtotal * 0.18) / 2);
  const totalTax = data.gst_18_percent || (cgst + sgst);
  const grandTotal = data.grand_total || (subtotal + totalTax);

  const formatInr = (num: number) => {
    return Number(num).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  return (
    <div id="printable-invoice" className="mt-4 mb-6 w-full max-w-3xl bg-white border border-gray-300 shadow-xl rounded-xl overflow-hidden font-sans text-gray-800">
      <div className="bg-slate-900 px-6 py-3.5 flex justify-between items-center text-white print:hidden">
        <div className="flex items-center space-x-2.5">
          <span className="bg-emerald-600 text-white font-bold text-[11px] px-2.5 py-0.5 rounded tracking-wider uppercase">
            Official Tax Invoice
          </span>
          <span className="text-gray-300 text-xs">Cloud Infotech Distribution • Verified Document</span>
        </div>
        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={() => window.print()}
            className="inline-flex items-center space-x-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-3.5 py-1.5 rounded-lg transition-colors shadow-sm cursor-pointer"
            title="Print or Save as PDF"
          >
            <PrinterIcon className="w-4 h-4" />
            <span>Print / Save PDF</span>
          </button>
        </div>
      </div>

      <div className="p-8 space-y-6">
        <div className="flex justify-between items-start border-b-2 border-slate-800 pb-5">
          <div>
            <h1 className="text-2xl font-black tracking-tight text-slate-900 uppercase">
              {distributor.name}
            </h1>
            <p className="text-xs font-bold text-blue-600 uppercase tracking-wide mt-0.5">
              {distributor.subtitle || "Authorized National Distributor for DINSTAR"}
            </p>
            <div className="text-xs text-gray-600 mt-2 space-y-0.5 leading-relaxed">
              <p>{distributor.address}</p>
              <p className="font-semibold text-gray-800">
                GSTIN/UIN: <span className="font-mono text-blue-700">{distributor.gstin}</span> | State: Uttar Pradesh (Code 07)
              </p>
              <p>Email: {distributor.email} | Tel: {distributor.phone}</p>
            </div>
          </div>

          <div className="text-right">
            <h2 className="text-2xl font-black tracking-wider text-blue-700 uppercase">
              TAX INVOICE
            </h2>
            <div className="mt-2 text-xs space-y-1">
              <p className="font-semibold text-gray-900">
                <span className="text-gray-500 uppercase tracking-wider text-[10px]">INVOICE NO:</span>{' '}
                <span className="font-mono text-slate-900 font-bold">{data.invoice_id}</span>
              </p>
              <p className="text-gray-600">
                <span className="text-gray-500 uppercase tracking-wider text-[10px]">INVOICE DATE:</span>{' '}
                <span className="font-medium text-gray-800">{data.invoice_date || new Date().toLocaleDateString('en-GB')}</span>
              </p>
              <p className="text-gray-600">
                <span className="text-gray-500 uppercase tracking-wider text-[10px]">DUE DATE:</span>{' '}
                <span className="font-medium text-gray-800">{data.due_date || 'Net 30 Days'}</span>
              </p>
              <div className="pt-1">
                <span className="inline-block bg-emerald-50 text-emerald-700 border border-emerald-300 font-bold text-[11px] px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                  {data.status || 'APPROVED & OFFICIAL'}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-xs">
            <span className="font-bold uppercase tracking-wider text-slate-500 text-[10px] block mb-1">
              BILLED TO / BUYER DETAILS:
            </span>
            <p className="text-sm font-bold text-slate-900">{billedTo.name}</p>
            <p className="text-slate-600 mt-1">{billedTo.address}</p>
            <p className="text-slate-700 mt-1">
              <span className="font-semibold text-gray-800">GSTIN:</span>{' '}
              <span className="font-mono text-slate-900">{billedTo.gstin || '07AAAAA1234Z1ZP'}</span>
            </p>
            <p className="text-slate-600 mt-0.5">
              <span className="font-medium">Contact:</span> {billedTo.email || 'finance@client.com'} {billedTo.contact ? `| ${billedTo.contact}` : ''}
            </p>
          </div>

          <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-xs">
            <span className="font-bold uppercase tracking-wider text-slate-500 text-[10px] block mb-1">
              DISPATCH & COMMERCIAL TERMS:
            </span>
            <div className="space-y-1 text-slate-700">
              <p><span className="font-semibold text-gray-800">Pricing Tier:</span> {data.pricing_tier || "End-Customer Price"}</p>
              <p><span className="font-semibold text-gray-800">Dispatch Mode:</span> Surface Transport (FOC Free of Cost)</p>
              <p><span className="font-semibold text-gray-800">Standard Warranty:</span> 3 Years Hardware Replacement</p>
              <p><span className="font-semibold text-gray-800">Payment Terms:</span> 30 Days Credit Period</p>
            </div>
          </div>
        </div>

        <div>
          <div className="border border-slate-300 rounded-lg overflow-hidden">
            <table className="w-full text-xs text-left border-collapse">
              <thead className="bg-slate-100 text-slate-800 font-bold border-b border-slate-300 uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="px-3 py-2.5 text-center w-10 border-r border-slate-300">#</th>
                  <th className="px-3.5 py-2.5 border-r border-slate-300">Model & Technical Description</th>
                  <th className="px-3 py-2.5 text-center w-16 border-r border-slate-300">Qty</th>
                  <th className="px-3.5 py-2.5 text-right w-24 border-r border-slate-300">Rate (₹)</th>
                  <th className="px-3.5 py-2.5 text-right w-24 border-r border-slate-300">Taxable (₹)</th>
                  <th className="px-3.5 py-2.5 text-center w-16 border-r border-slate-300">GST</th>
                  <th className="px-3.5 py-2.5 text-right w-24">Total (₹)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white">
                {items.map((item: any, idx: number) => (
                  <tr key={idx} className="hover:bg-slate-50 transition-colors">
                    <td className="px-3 py-3 text-center font-semibold text-slate-600 border-r border-slate-200">{idx + 1}</td>
                    <td className="px-3.5 py-3 border-r border-slate-200">
                      <p className="font-bold text-slate-900">{item.model}</p>
                      <p className="text-[11px] text-slate-500 mt-0.5">{item.description}</p>
                      <span className="inline-block mt-1 bg-slate-100 text-slate-600 text-[10px] px-1.5 py-0.5 rounded border border-slate-200 font-medium">
                        {item.category}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-center font-bold text-slate-900 border-r border-slate-200">{item.quantity}</td>
                    <td className="px-3.5 py-3 text-right font-medium text-slate-700 border-r border-slate-200">{formatInr(item.unit_price)}</td>
                    <td className="px-3.5 py-3 text-right font-semibold text-slate-800 border-r border-slate-200">{formatInr(item.total)}</td>
                    <td className="px-3.5 py-3 text-center font-medium text-slate-600 border-r border-slate-200">{item.gst_rate_percent || 18}%</td>
                    <td className="px-3.5 py-3 text-right font-bold text-slate-900">{formatInr(item.total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
          <div className="text-[11px] text-slate-600 bg-slate-50 p-4 rounded-lg border border-slate-200 space-y-1.5">
            <p className="font-bold text-slate-800 uppercase tracking-wide text-[10px]">Commercial Terms & Conditions:</p>
            <p>• Extra @ 18% GST included in final billed calculation.</p>
            <p>• <strong>3 Years Standard Replacement Warranty</strong> on all DINSTAR hardware.</p>
            <p>• <strong>Surface transport charges: Free of Cost (FOC)</strong> across India.</p>
            <p>• Air Freight charges extra on actual billed value.</p>
            <p>• 24*7 Technical support & emergency SLA response.</p>
            <p>• Payment strictly within 30 days of invoice date.</p>
          </div>

          <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 space-y-2 text-xs">
            <div className="flex justify-between text-slate-600">
              <span>Subtotal (Taxable Value):</span>
              <span className="font-semibold text-slate-900">₹{formatInr(subtotal)}</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>CGST (9.0%):</span>
              <span className="font-medium text-slate-800">₹{formatInr(cgst)}</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>SGST (9.0%):</span>
              <span className="font-medium text-slate-800">₹{formatInr(sgst)}</span>
            </div>
            <div className="flex justify-between text-slate-600 font-medium">
              <span>Total Tax (18% GST):</span>
              <span className="text-slate-800">₹{formatInr(totalTax)}</span>
            </div>
            <div className="flex justify-between text-sm font-black text-slate-900 border-t-2 border-slate-300 pt-2.5 mt-1">
              <span>GRAND TOTAL DUE:</span>
              <span className="text-blue-700 text-base">₹{formatInr(grandTotal)}</span>
            </div>
          </div>
        </div>

        <div className="border-t border-slate-200 pt-4 flex justify-between items-end text-xs text-slate-500">
          <div>
            <p className="font-bold text-slate-700 text-[11px] uppercase">Bank Account Details:</p>
            <p>Bank: HDFC Bank Ltd | A/C No: 50200012345678</p>
            <p>IFSC: HDFC0000123 | Branch: Sector 63, Noida</p>
          </div>
          <div className="text-right">
            <p className="font-bold text-slate-800 text-xs uppercase">For Cloud Infotech Distribution Pvt. Ltd.</p>
            <div className="h-10 flex items-center justify-end">
              <span className="text-[10px] text-emerald-600 border border-emerald-300 bg-emerald-50 px-2 py-0.5 rounded font-mono font-bold">
                ✓ DIGITALLY VERIFIED SIGNATURE
              </span>
            </div>
            <p className="text-[10px] text-slate-400">Authorized Signatory</p>
          </div>
        </div>
      </div>
    </div>
  );
}

const QUICK_ACTIONS = [
  {
    label: "Create Quotation",
    prompt: "I need to create a commercial Quotation"
  },
  {
    label: "Create Invoice",
    prompt: "I need to generate a Tax Invoice"
  },
  {
    label: "API Latency",
    prompt: "Investigate our recent API latency."
  },
  {
    label: "Indian Govt Holidays",
    prompt: "What are the official Indian Government Gazetted holidays?"
  },
  {
    label: "Current Day & Time",
    prompt: "What day is today and what is the current time?"
  },
  {
    label: "Python API Script",
    prompt: "Write a production Python script to fetch an API with retries."
  }
];

const renderMessageContent = (content: string, onSend?: (text: string) => void, isLoading?: boolean) => {
  if (!content) return null;

  try {
    // 0. Check for interactive quotation selector payload
    if (content.includes('<!-- QUOTATION_SELECTOR_START -->')) {
      const startMarker = '<!-- QUOTATION_SELECTOR_START -->';
      const endMarker = '<!-- QUOTATION_SELECTOR_END -->';
      const startIdx = content.indexOf(startMarker);
      const endIdx = content.indexOf(endMarker);
      let selectorData: any = null;
      if (startIdx !== -1 && endIdx !== -1) {
        const jsonStr = content.substring(startIdx + startMarker.length, endIdx).trim();
        try {
          selectorData = JSON.parse(jsonStr);
        } catch (e) {
          console.error('Failed to parse quotation selector payload', e);
        }
      }
      return <QuotationSelectorCard data={selectorData} onSend={onSend} isLoading={isLoading} />;
    }

    // 1. Check for interactive invoice selector payload
    if (content.includes('<!-- INVOICE_SELECTOR_START -->')) {
      const startMarker = '<!-- INVOICE_SELECTOR_START -->';
      const endMarker = '<!-- INVOICE_SELECTOR_END -->';
      const startIdx = content.indexOf(startMarker);
      const endIdx = content.indexOf(endMarker);
      let selectorData: any = null;
      if (startIdx !== -1 && endIdx !== -1) {
        const jsonStr = content.substring(startIdx + startMarker.length, endIdx).trim();
        try {
          selectorData = JSON.parse(jsonStr);
        } catch (e) {
          console.error('Failed to parse invoice selector payload', e);
        }
      }
      return <InvoiceSelectorCard data={selectorData} onSend={onSend} isLoading={isLoading} />;
    }

    // 2. Check for official Tax Invoice
    if (content.includes('invoice_id')) {
      let invoiceData: any = null;
      const jsonBlockMatch = content.match(/```json\s*([\s\S]*?)\s*```/);
      if (jsonBlockMatch) {
        try {
          const parsed = JSON.parse(jsonBlockMatch[1]);
          if (parsed && parsed.invoice_id) invoiceData = parsed;
        } catch (e) {}
      }

      const extractJsonFromKeyword = (keyword: string) => {
        const idx = content.indexOf(keyword);
        if (idx === -1) return null;
        const sub = content.substring(idx, Math.min(content.length, idx + 3500));
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

      if (!invoiceData) {
        invoiceData = extractJsonFromKeyword('invoice.generate') || extractJsonFromKeyword('invoice_id');
      }

      if (invoiceData && invoiceData.invoice_id) {
        return <InvoiceCard data={invoiceData} />;
      }
    }

    let quoteData: any = null;
    let custData: any = null;

    if (content.includes('quotation_id')) {
      const extractJsonBraces = (keyword: string) => {
        const idx = content.indexOf(keyword);
        if (idx === -1) return null;
        const sub = content.substring(idx, Math.min(content.length, idx + 3500));
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
        // Fast markdown json code block extraction
        const codeBlockMatch = content.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
        if (codeBlockMatch) {
          try {
            const parsed = JSON.parse(codeBlockMatch[1]);
            if (parsed && parsed.quotation_id) q = parsed;
            if (parsed && (parsed.customers || parsed.name)) c = parsed;
          } catch (e) {}
        }
        // Direct quotation_id JSON object match without scanning entire content repeatedly
        if (!q) {
          const directMatch = content.match(/\{[^{}]*?"quotation_id"\s*:\s*"[^"]+"[^{}]*?\}/);
          if (directMatch) {
            try {
              const parsed = JSON.parse(directMatch[0]);
              if (parsed && parsed.quotation_id) q = parsed;
            } catch (e) {}
          }
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

      const customerName = quoteData.company_name || (quoteData.customer && quoteData.customer.name) || customer.name || 'Acme Technologies';
      const customerEmail = (quoteData.customer && quoteData.customer.email) || customer.email || 'billing@client.com';
      const customerAddress = (quoteData.customer && quoteData.customer.address) || 'Corporate Tower, Electronic City';

      const itemsList = (quoteData.items && Array.isArray(quoteData.items) && quoteData.items.length > 0)
        ? quoteData.items
        : [
            {
              quantity: quoteData.quantity || 1,
              model: quoteData.model || 'DINSTAR Solution',
              description: quoteData.product_name || 'Commercial Telephony Hardware Solution',
              category: 'DINSTAR Telephony',
              unit_price: quoteData.unit_price || total,
              total: quoteData.total || total,
            }
          ];

      return (
        <div id="printable-quotation" className="mt-4 mb-4 w-full max-w-2xl bg-white border border-gray-300 shadow-md rounded-xl overflow-hidden font-sans text-gray-800">
          {/* Header Action Bar */}
          <div className="bg-slate-900 px-6 py-3.5 flex justify-between items-center text-white print:hidden">
            <div className="flex items-center space-x-2">
              <span className="bg-blue-600 text-white font-bold text-[11px] px-2.5 py-0.5 rounded tracking-wider uppercase">Official Commercial Quotation</span>
              <span className="text-gray-300 text-xs">Cloud Infotech Distribution • Ready for Print / PDF</span>
            </div>
            <button
              type="button"
              onClick={() => window.print()}
              className="inline-flex items-center space-x-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors shadow-sm cursor-pointer"
              title="Print or Save as PDF"
            >
              <PrinterIcon className="w-3.5 h-3.5" />
              <span>Print Quotation</span>
            </button>
          </div>

          <div className="p-7 space-y-6">
            {/* Top Company & Quotation Metadata Section */}
            <div className="flex justify-between items-start border-b border-gray-200 pb-5">
              <div>
                <h2 className="text-xl font-black tracking-tight text-blue-700 uppercase">Cloud Infotech Distribution Pvt. Ltd.</h2>
                <p className="text-xs text-blue-600 font-bold mt-0.5">Authorized National Distributor for DINSTAR</p>
                <div className="text-xs text-gray-600 mt-2 space-y-0.5">
                  <p>B-42, Sector 63, Electronic City, Noida, UP 201301</p>
                  <p>GSTIN: 07AAAAA0000A1Z5 | PAN: AABCC1234D</p>
                  <p>Phone: +91 (120) 456-7890 | Email: sales@cloudinfotech.com</p>
                </div>
              </div>

              <div className="text-right">
                <h1 className="text-2xl font-black tracking-wider text-slate-800 uppercase">QUOTATION</h1>
                <div className="mt-2 text-xs space-y-1">
                  <p className="font-semibold text-gray-900">
                    <span className="text-gray-500 uppercase tracking-wider text-[10px]">QUOTE NO:</span>{' '}
                    <span className="font-mono text-blue-700 font-bold">{quoteData.quotation_id}</span>
                  </p>
                  <p className="text-gray-600">
                    <span className="text-gray-500 uppercase tracking-wider text-[10px]">ISSUE DATE:</span>{' '}
                    {new Date().toLocaleDateString('en-US', { day: '2-digit', month: 'short', year: 'numeric' })}
                  </p>
                  <p className="text-gray-600">
                    <span className="text-gray-500 uppercase tracking-wider text-[10px]">VALID UNTIL:</span>{' '}
                    {new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toLocaleDateString('en-US', { day: '2-digit', month: 'short', year: 'numeric' })}
                  </p>
                  <div className="pt-1">
                    <span className="inline-block bg-emerald-50 text-emerald-700 border border-emerald-300 font-bold text-[11px] px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                      {quoteData.status ? quoteData.status.toUpperCase() : 'OFFICIAL DRAFT'}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Client "TO" Section */}
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5 text-xs">
              <span className="font-bold uppercase tracking-wider text-slate-500 text-[10px] block mb-1">PROSPECTIVE CLIENT / PROPOSED TO:</span>
              <p className="text-sm font-bold text-slate-900">{customerName}</p>
              <p className="text-slate-600 mt-0.5">{customerAddress}</p>
              <p className="text-slate-600 mt-1"><span className="font-medium text-slate-700">Contact:</span> {customerEmail}</p>
            </div>

            {/* Scope / Description Section Header */}
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-2">Scope of Supply & Proposed Bill of Materials</p>
              <div className="border border-slate-300 rounded-lg overflow-hidden">
                <table className="w-full text-xs text-left border-collapse">
                  <thead className="bg-slate-100 text-slate-800 font-bold border-b border-slate-300 uppercase text-[10px] tracking-wider">
                    <tr>
                      <th className="px-3.5 py-2.5 text-center w-16 border-r border-slate-300">Quantity</th>
                      <th className="px-3.5 py-2.5 border-r border-slate-300">Model & Technical Description</th>
                      <th className="px-3.5 py-2.5 text-right w-24 border-r border-slate-300">Unit Price</th>
                      <th className="px-3.5 py-2.5 text-right w-20 border-r border-slate-300">GST</th>
                      <th className="px-3.5 py-2.5 text-right w-24">Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 bg-white">
                    {itemsList.map((item: any, idx: number) => (
                      <tr key={idx} className="hover:bg-slate-50 transition-colors">
                        <td className="px-3.5 py-3 text-center font-semibold text-slate-900 border-r border-slate-200">{item.quantity}</td>
                        <td className="px-3.5 py-3 border-r border-slate-200">
                          <p className="font-bold text-slate-900">{item.model || quoteData.model || 'DINSTAR Hardware'}</p>
                          <p className="text-[11px] text-slate-500 mt-0.5">{item.description || quoteData.product_name || 'Standard Distribution Unit'}</p>
                          {item.category && (
                            <span className="inline-block mt-1 bg-slate-100 text-slate-600 text-[10px] px-1.5 py-0.5 rounded border border-slate-200 font-medium">
                              {item.category}
                            </span>
                          )}
                        </td>
                        <td className="px-3.5 py-3 text-right font-medium text-slate-700 border-r border-slate-200">₹{item.unit_price || total}</td>
                        <td className="px-3.5 py-3 text-right text-slate-600 border-r border-slate-200">18% extra</td>
                        <td className="px-3.5 py-3 text-right font-bold text-slate-900">₹{item.total || total}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Financial Summary & Terms */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
              <div className="text-[11px] text-slate-600 bg-slate-50 p-3.5 rounded-lg border border-slate-200 space-y-1">
                <p className="font-bold text-slate-800 uppercase tracking-wide text-[10px]">Commercial Terms & Conditions:</p>
                <p>• Prices valid for <strong>30 calendar days</strong> from issue date.</p>
                <p>• <strong>3 Years Standard Replacement Warranty</strong> on all products.</p>
                <p>• <strong>Surface transport across India: Free of Cost (FOC)</strong>.</p>
                <p>• GST @ 18% extra as applicable on final invoice billing.</p>
                <p>• 24x7 Technical support and enterprise SLA coverage.</p>
              </div>

              <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-200 space-y-1.5 text-xs">
                <div className="flex justify-between text-slate-600">
                  <span>Subtotal (Commercial Rate):</span>
                  <span className="font-medium text-slate-900">₹{quoteData.subtotal || total}</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Price Validity:</span>
                  <span className="font-medium text-emerald-700">30 Days</span>
                </div>
                <div className="flex justify-between text-sm font-black text-slate-900 border-t border-slate-300 pt-2 mt-1">
                  <span>ESTIMATED TOTAL:</span>
                  <span className="text-blue-700">₹{quoteData.total || total}</span>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="border-t border-slate-200 pt-3.5 text-center text-[11px] text-slate-500 space-y-0.5">
              <p>For questions regarding this quotation, contact Cloud Infotech Distribution: <span className="text-blue-600 font-medium">sales@cloudinfotech.com</span></p>
              <p className="font-bold text-slate-800 tracking-wider uppercase text-xs pt-0.5">THANK YOU FOR CHOOSING CLOUD INFOTECH!</p>
            </div>
          </div>
        </div>
      );
    }
  } catch (e) {
    console.error('Error rendering quotation component', e);
  }

  
  let displayContent = content;
  if (displayContent.includes('result:**')) {
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
        
        for (let j = jsonStart; j < Math.min(displayContent.length, jsonStart + 8000); j++) {
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
  }

  return (
    <div className="text-[15px] max-w-none break-words">
      {renderMarkdown(displayContent)}
    </div>
  );

};

interface ChatMessageItemProps {
  msg: Message;
  onSend?: (text: string) => void;
  isLoading?: boolean;
}

const ChatMessageItem = React.memo(
  function ChatMessageItem({ msg, onSend, isLoading }: ChatMessageItemProps) {
    const isFullWidthMsg =
      msg.role === 'assistant' &&
      (
        (msg.content.includes('quotation.create_draft') && msg.content.includes('quotation_id')) ||
        msg.content.includes('<!-- INVOICE_SELECTOR_START -->') ||
        msg.content.includes('<!-- QUOTATION_SELECTOR_START -->') ||
        msg.content.includes('invoice_id')
      );

    const contentNode = renderMessageContent(msg.content, onSend, isLoading);

    if (isFullWidthMsg) {
      return (
        <div className="flex justify-start w-full">
          {contentNode}
        </div>
      );
    }

    return (
      <div className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
        <div
          className={`max-w-[80%] rounded-2xl px-5 py-3.5 ${
            msg.role === 'user'
              ? 'bg-blue-600 text-white shadow-md'
              : 'bg-gray-100 text-gray-900 border border-gray-200 shadow-sm'
          }`}
        >
          {contentNode}
        </div>
      </div>
    );
  },
  (prev, next) => {
    if (prev.msg.id !== next.msg.id) return false;
    if (prev.msg.content !== next.msg.content) return false;
    if (prev.msg.role !== next.msg.role) return false;
    const hasInteractiveCard =
      prev.msg.content.includes('<!-- QUOTATION_SELECTOR_START -->') ||
      prev.msg.content.includes('<!-- INVOICE_SELECTOR_START -->');
    if (hasInteractiveCard && prev.isLoading !== next.isLoading) return false;
    return true;
  }
);

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
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
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

  const handleSend = async (forcedText?: string) => {
    const text = forcedText || input;
    if (!text.trim()) return;

    setInput('');
    setIsLoading(true);
    setStreamContent('');
    setPendingApproval(null);

    // Optimistic UI for user message
    const tempMsg: Message = { id: (typeof crypto !== 'undefined' && crypto.randomUUID) ? crypto.randomUUID() : 'msg-temp', role: 'user', content: text };
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
        try {
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
                      setStreamContent((prev) => prev + `\n\n[⚙️ Action: ${payload.component} running...]`);
                    }
                  } else if (payload.event_type === 'NODE_COMPLETED') {
                    if (payload.component !== 'DecisionNode') {
                      setStreamContent((prev) => prev + `\n[✓ ${payload.component} completed]`);
                    }
                  } else if (payload.event_type === 'plan_created') {
                    setStreamContent((prev) => prev + `\n\n[📋 AURA mapped out a plan]`);
                  }
                } catch (e) {
                  // Ignore parse errors on partial chunks
                }
              }
            }
            if (streamEnded) break;
          }
        } finally {
          reader.cancel().catch(() => {});
        }
      }
    } catch (e) {
      console.error("Stream error", e);
    }

    // Polling loop: Ensure run has actually completed or failed before loading final messages
    try {
      let attempts = 0;
      while (attempts < 25) {
        const statusRes = await fetchApi(`/runs/${runId}`);
        if (statusRes.ok) {
          const statusData = await statusRes.json();
          const st = (statusData.status || '').toLowerCase();
          
          if (st === 'awaiting_approval') {
            const appRes = await fetchApi('/approvals');
            if (appRes.ok) {
              const appData = await appRes.json();
              const items = appData.approvals || appData.items || [];
              const approval = items.find(
                (a: any) =>
                  (a.agent_run_id === runId || a.run_id === runId) &&
                  (a.status === 'pending' || a.status === 'PENDING' || a.status === 'pending_approval')
              );
              if (approval) setPendingApproval(approval);
            }
            break;
          } else if (st === 'completed') {
            break;
          } else if (st === 'failed') {
            let errorMsg = statusData.error_message || 'Unknown error';
            setStreamContent((prev) => prev + '\n\n❌ Error: ' + errorMsg);
            break;
          }
        }
        await new Promise((r) => setTimeout(r, 600));
        attempts++;
      }
      
      await loadMessages(convId);
      setStreamContent('');
    } catch(e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
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
    <div className="flex flex-col h-full min-h-0 overflow-hidden">
      <div className="mb-2 shrink-0">
        <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Conversations</h1>
        <p className="text-xs sm:text-sm text-gray-500 mt-0.5">Interact with AURA or review past AI task threads.</p>
      </div>
      <div className="flex flex-1 min-h-0 overflow-hidden border border-gray-200 rounded-xl bg-white shadow-sm">
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
        <div ref={messagesContainerRef} className="flex-1 min-h-0 overflow-y-auto p-6 space-y-6">
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

          {messages.map((msg) => (
            <ChatMessageItem
              key={msg.id}
              msg={msg}
              onSend={handleSend}
              isLoading={isLoading}
            />
          ))}

          {/* Streaming Bubble */}
          {(isLoading || streamContent) && (
            <div className={`flex justify-start ${streamContent && (streamContent.includes('quotation_id') || streamContent.includes('<!-- INVOICE_SELECTOR_START -->') || streamContent.includes('<!-- QUOTATION_SELECTOR_START -->') || streamContent.includes('invoice_id')) ? 'w-full' : ''}`}>
              <div
                className={`${
                  streamContent && (streamContent.includes('quotation_id') || streamContent.includes('<!-- INVOICE_SELECTOR_START -->') || streamContent.includes('<!-- QUOTATION_SELECTOR_START -->') || streamContent.includes('invoice_id'))
                    ? 'w-full max-w-3xl'
                    : 'max-w-[80%] rounded-2xl px-5 py-3.5 bg-gray-100 text-gray-900 border border-gray-200 shadow-sm'
                }`}
              >
                {streamContent ? renderMessageContent(streamContent, handleSend, isLoading) : (
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
        <div className="p-4 border-t border-gray-200 bg-white shrink-0">
          {/* Active Conversation Quick Actions */}
          {activeId && (
            <div className="mx-auto max-w-4xl mb-2.5">
              <div className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Quick actions</div>
              <div className="flex flex-wrap gap-1.5 pb-0.5">
                {QUICK_ACTIONS.map((action, i) => (
                  <button
                    key={i}
                    onClick={() => handleSend(action.prompt)}
                    disabled={isLoading || !!pendingApproval}
                    className="rounded-full border border-gray-200 bg-white px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-blue-50 hover:text-blue-600 hover:border-blue-200 transition-colors shadow-xs disabled:opacity-50 whitespace-nowrap cursor-pointer"
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
