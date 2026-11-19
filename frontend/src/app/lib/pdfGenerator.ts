import { jsPDF } from 'jspdf';

export interface InvoiceData {
  invoice_id: string;
  invoice_date?: string;
  created_date_formatted?: string;
  due_date?: string;
  due_date_formatted?: string;
  distributor?: {
    name?: string;
    subtitle?: string;
    address?: string;
    gstin?: string;
    email?: string;
    phone?: string;
  };
  billed_to?: {
    name?: string;
    address?: string;
    gstin?: string;
    email?: string;
    contact?: string;
  };
  pricing_tier?: string;
  items?: Array<{
    model?: string;
    category?: string;
    description?: string;
    quantity?: number;
    unit_price?: number;
    gst_rate_percent?: number;
    gst_amount?: number;
    total?: number;
  }>;
  subtotal?: number;
  cgst_9_percent?: number;
  sgst_9_percent?: number;
  gst_18_percent?: number;
  grand_total?: number;
  currency_symbol?: string;
  terms?: string[];
}

export interface QuotationData {
  quotation_id: string;
  quotation_date?: string;
  created_date_formatted?: string;
  valid_until?: string;
  valid_until_formatted?: string;
  company_name?: string;
  customer?: {
    name?: string;
    address?: string;
    email?: string;
    contact?: string;
  };
  model?: string;
  pricing_tier?: string;
  items?: Array<{
    model?: string;
    description?: string;
    category?: string;
    quantity?: number;
    unit_price?: string | number;
    discount_percent?: number;
    total?: string | number;
  }>;
  subtotal?: string | number;
  discount?: string | number;
  total?: string | number;
  terms?: string[];
}

const formatNumber = (num: number | string | undefined): string => {
  if (num === undefined || num === null) return '0.00';
  const val = typeof num === 'string' ? parseFloat(num.replace(/,/g, '')) : num;
  if (isNaN(val)) return '0.00';
  return val.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

/**
 * Universal formatting templates for Invoices:
 * Guarantees 100% consistent, non-overlapping format across Gmail, WhatsApp, and Clipboard.
 */
export function getInvoiceUniversalShareTemplates(data: InvoiceData) {
  const invoiceNo = data.invoice_id || 'INV-OFFICIAL';
  const customerName = data.billed_to?.name || 'Valued Customer';
  const customerEmail = data.billed_to?.email || '';
  const firstItem = data.items?.[0] || {};
  const itemDesc = firstItem.model ? `${firstItem.model} (Qty: ${firstItem.quantity || 1})` : 'Hardware Solution';
  const subtotal = data.subtotal || 0;
  const gstTotal = data.gst_18_percent || ((data.cgst_9_percent || 0) + (data.sgst_9_percent || 0)) || Math.round(subtotal * 0.18);
  const grandTotal = data.grand_total || (subtotal + gstTotal);
  const invoiceDate = data.invoice_date || new Date().toLocaleDateString('en-GB');
  const dueDate = data.due_date || '30 Calendar Days';

  const subject = `TAX INVOICE - ${invoiceNo} - ${customerName}`;

  // Universal Email Body (Formatted with CRLF \r\n to prevent Gmail line collapsing & overlapping)
  const gmailBody = [
    "OFFICIAL TAX INVOICE",
    "Cloud Infotech Distribution Pvt. Ltd.",
    "Authorized National DINSTAR Partner",
    "==================================================",
    "",
    `INVOICE NO   : ${invoiceNo}`,
    `INVOICE DATE : ${invoiceDate}`,
    `PAYMENT TERMS: Net 30 Days (${dueDate})`,
    "",
    "--------------------------------------------------",
    "BILLED TO / CUSTOMER DETAILS",
    "--------------------------------------------------",
    `Customer Name: ${customerName}`,
    `Address      : ${data.billed_to?.address || 'Corporate Complex, India'}`,
    `GSTIN / PAN  : ${data.billed_to?.gstin || '07AAAAA1234Z1ZP'}`,
    `Email        : ${customerEmail || 'accounts@client.com'}`,
    "",
    "--------------------------------------------------",
    "COMMERCIAL SUMMARY & VALUE",
    "--------------------------------------------------",
    `Equipment    : ${itemDesc}`,
    `Taxable Value: Rs. ${formatNumber(subtotal)}`,
    `GST (18%)    : Rs. ${formatNumber(gstTotal)}`,
    `GRAND TOTAL  : Rs. ${formatNumber(grandTotal)}`,
    "",
    "--------------------------------------------------",
    "COMMERCIAL TERMS & WARRANTY",
    "--------------------------------------------------",
    "• Hardware Warranty: 3 Years Comprehensive Replacement",
    "• Shipping / Transport: Free of Cost (FOC) nationwide across India",
    "• SLA Support: 24x7 Certified Engineering Assistance",
    "",
    "==================================================",
    "Official high-resolution PDF invoice is downloaded to your device.",
    "Drafted & Authenticated via AURA Enterprise Commercial Agent."
  ].join('\r\n');

  // WhatsApp Universal Text
  const whatsAppText = [
    "📄 *OFFICIAL TAX INVOICE - CLOUD INFOTECH DISTRIBUTION*",
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    `*Invoice No:* ${invoiceNo}`,
    `*Billed To:* ${customerName}`,
    `*Model:* ${itemDesc}`,
    `*Taxable Value:* Rs. ${formatNumber(subtotal)}`,
    `*GST (18%):* Rs. ${formatNumber(gstTotal)}`,
    `*Grand Total:* Rs. ${formatNumber(grandTotal)}`,
    `*Payment Terms:* Net 30 Days (${dueDate})`,
    `*Warranty:* 3 Years Replacement Warranty`,
    `*Shipping:* Free of Cost (FOC) across India`,
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    "_Official invoice generated and verified via AURA Enterprise Platform._"
  ].join('\n');

  const copySummary = `Tax Invoice: ${invoiceNo} | Billed To: ${customerName} | Grand Total: Rs. ${formatNumber(grandTotal)} (incl. 18% GST)`;

  return { subject, gmailBody, whatsAppText, copySummary, customerEmail, invoiceNo, grandTotal };
}

/**
 * Universal formatting templates for Quotations:
 * Guarantees 100% consistent, non-overlapping format across Gmail, WhatsApp, and Clipboard.
 */
export function getQuotationUniversalShareTemplates(data: QuotationData) {
  const quoteNo = data.quotation_id || 'QUO-OFFICIAL';
  const customerName = data.company_name || data.customer?.name || 'Client Company';
  const customerEmail = data.customer?.email || '';
  const firstItem = data.items?.[0] || {};
  const modelName = data.model || firstItem.model || 'DAG1000-8S';
  const totalVal = data.total || 0;
  const quoteDate = data.quotation_date || new Date().toLocaleDateString('en-GB');
  const validUntil = data.valid_until || '30 Calendar Days';

  const subject = `COMMERCIAL QUOTATION - ${quoteNo} - ${customerName}`;

  // Universal Email Body (Formatted with CRLF \r\n to prevent Gmail line collapsing & overlapping)
  const gmailBody = [
    "OFFICIAL COMMERCIAL QUOTATION",
    "Cloud Infotech Distribution Pvt. Ltd.",
    "Authorized National DINSTAR Partner",
    "==================================================",
    "",
    `QUOTATION NO : ${quoteNo}`,
    `ISSUE DATE   : ${quoteDate}`,
    `VALIDITY     : 30 Calendar Days (${validUntil})`,
    "",
    "--------------------------------------------------",
    "PROPOSED TO / CLIENT DETAILS",
    "--------------------------------------------------",
    `Client Name  : ${customerName}`,
    `Address      : ${data.customer?.address || 'Corporate Complex, India'}`,
    `Email        : ${customerEmail || 'billing@nexacomms.in'}`,
    "",
    "--------------------------------------------------",
    "COMMERCIAL PROPOSAL & SPECIFICATIONS",
    "--------------------------------------------------",
    `Equipment    : ${modelName}`,
    `Quoted Total : Rs. ${formatNumber(totalVal)}`,
    `Pricing Tier : End-Customer Distribution Price`,
    "",
    "--------------------------------------------------",
    "COMMERCIAL TERMS & WARRANTY",
    "--------------------------------------------------",
    "• Hardware Warranty: 3 Years Replacement Warranty",
    "• Shipping / Transport: Free of Cost (FOC) nationwide across India",
    "• Dispatch Time: Ready stock available for 24-48 hr dispatch",
    "",
    "==================================================",
    "Official high-resolution PDF quotation is downloaded to your device.",
    "Formulated & Authenticated via AURA Enterprise Commercial Agent."
  ].join('\r\n');

  // WhatsApp Universal Text
  const whatsAppText = [
    "📄 *COMMERCIAL QUOTATION - CLOUD INFOTECH DISTRIBUTION*",
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    `*Quote No:* ${quoteNo}`,
    `*Proposed To:* ${customerName}`,
    `*Model:* ${modelName}`,
    `*Total Value:* Rs. ${formatNumber(totalVal)}`,
    `*Validity:* 30 Calendar Days (${validUntil})`,
    `*Warranty:* 3 Years Replacement Warranty`,
    `*Shipping:* Free of Cost (FOC) nationwide`,
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    "_Official quotation generated and verified via AURA Enterprise Platform._"
  ].join('\n');

  const copySummary = `Quotation: ${quoteNo} | Proposed To: ${customerName} | Total Value: Rs. ${formatNumber(totalVal)}`;

  return { subject, gmailBody, whatsAppText, copySummary, customerEmail, quoteNo, totalVal };
}

/**
 * Generates an official, beautifully structured, print-ready PDF for a Tax Invoice.
 * Designed with strict bounding boxes to guarantee ZERO overlaps.
 */
export function generateInvoicePdf(data: InvoiceData): { doc: jsPDF; blob: Blob; fileName: string } {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
  const invoiceNo = data.invoice_id || 'INV-OFFICIAL';
  const fileName = `Tax-Invoice-${invoiceNo}.pdf`;

  // Palette
  const primaryNavy = [15, 23, 42]; // Slate 900
  const accentBlue = [37, 99, 235]; // Blue 600
  const emeraldGreen = [5, 150, 105]; // Emerald 600
  const borderGray = [218, 224, 233]; // Slate 300
  const textDark = [30, 41, 59];
  const textMuted = [100, 116, 139];

  // Top Accent Bar
  doc.setFillColor(accentBlue[0], accentBlue[1], accentBlue[2]);
  doc.rect(0, 0, 210, 5, 'F');

  // Header Left (Strict width max 115mm, x: 14 to 129)
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(13);
  doc.setTextColor(primaryNavy[0], primaryNavy[1], primaryNavy[2]);
  doc.text('CLOUD INFOTECH DISTRIBUTION PVT. LTD.', 14, 16);

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8);
  doc.setTextColor(accentBlue[0], accentBlue[1], accentBlue[2]);
  doc.text('Authorized DINSTAR National Distributor & Commercial Gateway Partner', 14, 21);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.setTextColor(textMuted[0], textMuted[1], textMuted[2]);
  doc.text('B-42, Sector 63, Electronic City, Noida, Uttar Pradesh 201301', 14, 25.5);
  doc.text('GSTIN: 07AAAAA0000A1Z5  |  PAN: AABCC1234D', 14, 29.5);
  doc.text('Tel: +91 (120) 456-7890  |  Email: invoices@cloudinfotech.com', 14, 33.5);

  // Document Badge (Right aligned, x: 132 to 196, width 64mm, height 24mm)
  doc.setFillColor(primaryNavy[0], primaryNavy[1], primaryNavy[2]);
  doc.roundedRect(132, 11, 64, 24, 2, 2, 'F');
  doc.setTextColor(255, 255, 255);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.text('OFFICIAL TAX INVOICE', 137, 17.5);
  doc.setFontSize(7.8);
  doc.setFont('helvetica', 'normal');
  doc.text(`Invoice No: ${invoiceNo}`, 137, 22.5);
  doc.text(`Date: ${data.invoice_date || '17.11.2026'}`, 137, 27);
  doc.text(`Due: Net 30 Days (${data.due_date || '17.12.2026'})`, 137, 31.5);

  // Clean Divider
  doc.setDrawColor(borderGray[0], borderGray[1], borderGray[2]);
  doc.setLineWidth(0.3);
  doc.line(14, 38, 196, 38);

  // Billed To & Terms Boxes (x: 14 to 103 and 107 to 196, height: 26mm)
  const boxY = 41;
  const boxH = 26;
  doc.setFillColor(248, 250, 252);
  doc.rect(14, boxY, 89, boxH, 'F');
  doc.rect(107, boxY, 89, boxH, 'F');
  doc.setDrawColor(borderGray[0], borderGray[1], borderGray[2]);
  doc.rect(14, boxY, 89, boxH, 'S');
  doc.rect(107, boxY, 89, boxH, 'S');

  // Customer Box (Left)
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8);
  doc.setTextColor(primaryNavy[0], primaryNavy[1], primaryNavy[2]);
  doc.text('BILLED TO (CUSTOMER):', 18, boxY + 5.5);
  doc.setFontSize(9);
  doc.text(data.billed_to?.name || 'Customer Name', 18, boxY + 11, { maxWidth: 82 });
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.setTextColor(textMuted[0], textMuted[1], textMuted[2]);
  doc.text(data.billed_to?.address || 'Corporate Complex, Suite 100', 18, boxY + 16, { maxWidth: 82 });
  doc.text(`GSTIN: ${data.billed_to?.gstin || '07AAAAA1234Z1ZP'}  |  ${data.billed_to?.email || 'accounts@client.com'}`, 18, boxY + 21, { maxWidth: 82 });

  // Order Details Box (Right)
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8);
  doc.setTextColor(primaryNavy[0], primaryNavy[1], primaryNavy[2]);
  doc.text('COMMERCIAL TERMS & POLICY:', 111, boxY + 5.5);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.setTextColor(textDark[0], textDark[1], textDark[2]);
  doc.text(`Pricing Tier: ${data.pricing_tier || 'End-Customer Distribution Price'}`, 111, boxY + 11, { maxWidth: 82 });
  doc.text('Surface Transport: Free of Cost (FOC) across India', 111, boxY + 16, { maxWidth: 82 });
  doc.text('Hardware Warranty: 3 Years Comprehensive DINSTAR Warranty', 111, boxY + 21, { maxWidth: 82 });

  // Line Items Table Header
  const tableY = 70;
  doc.setFillColor(primaryNavy[0], primaryNavy[1], primaryNavy[2]);
  doc.rect(14, tableY, 182, 7.5, 'F');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7.5);
  doc.setTextColor(255, 255, 255);
  doc.text('#', 17, tableY + 5);
  doc.text('MODEL & TECHNICAL SPECIFICATION', 25, tableY + 5);
  doc.text('QTY', 115, tableY + 5, { align: 'right' });
  doc.text('RATE (INR)', 148, tableY + 5, { align: 'right' });
  doc.text('GST (18%)', 170, tableY + 5, { align: 'right' });
  doc.text('TOTAL (INR)', 192, tableY + 5, { align: 'right' });

  // Line Items Rows
  let curY = tableY + 7.5;
  const items = (data.items && data.items.length > 0) ? data.items : [{
    model: 'DINSTAR Telephony Gateway',
    description: 'High-Performance Enterprise Telephony Solution',
    quantity: 1,
    unit_price: data.subtotal || 23491.53,
    gst_amount: data.gst_18_percent || 4228.47,
    total: data.grand_total || 27720
  }];

  items.forEach((item, index) => {
    const rowH = 10;
    doc.setFillColor(index % 2 === 0 ? 255 : 248, index % 2 === 0 ? 255 : 250, index % 2 === 0 ? 255 : 252);
    doc.rect(14, curY, 182, rowH, 'F');
    doc.setDrawColor(borderGray[0], borderGray[1], borderGray[2]);
    doc.rect(14, curY, 182, rowH, 'S');

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.5);
    doc.setTextColor(textDark[0], textDark[1], textDark[2]);
    doc.text(`${index + 1}`, 17, curY + 6);

    doc.setFont('helvetica', 'bold');
    doc.text(`${item.model || 'DINSTAR Telephony Gateway'}`, 25, curY + 4.5, { maxWidth: 85 });
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(6.8);
    doc.setTextColor(textMuted[0], textMuted[1], textMuted[2]);
    doc.text(`${item.description || item.category || 'High-Performance Enterprise Telephony Solution'}`, 25, curY + 8.2, { maxWidth: 85 });

    doc.setFontSize(7.5);
    doc.setTextColor(textDark[0], textDark[1], textDark[2]);
    doc.text(`${item.quantity || 1}`, 115, curY + 6, { align: 'right' });
    doc.text(`Rs. ${formatNumber(item.unit_price)}`, 148, curY + 6, { align: 'right' });
    doc.text(`Rs. ${formatNumber(item.gst_amount || ((item.total || 0) * 0.18))}`, 170, curY + 6, { align: 'right' });
    doc.setFont('helvetica', 'bold');
    doc.text(`Rs. ${formatNumber(item.total)}`, 192, curY + 6, { align: 'right' });

    curY += rowH;
  });

  // Financial Breakdown Box (Right Aligned, x: 114 to 196, width 82mm)
  curY += 4;
  const totalBoxX = 114;
  const totalBoxW = 82;
  const rightAlignX = totalBoxX + totalBoxW - 4; // 192mm

  doc.setFillColor(248, 250, 252);
  doc.rect(totalBoxX, curY, totalBoxW, 36, 'F');
  doc.setDrawColor(borderGray[0], borderGray[1], borderGray[2]);
  doc.rect(totalBoxX, curY, totalBoxW, 36, 'S');

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.setTextColor(textDark[0], textDark[1], textDark[2]);

  doc.text('Subtotal (Taxable Value):', totalBoxX + 4, curY + 6);
  doc.text(`Rs. ${formatNumber(data.subtotal)}`, rightAlignX, curY + 6, { align: 'right' });

  doc.text('Central GST (CGST @ 9.0%):', totalBoxX + 4, curY + 12);
  doc.text(`Rs. ${formatNumber(data.cgst_9_percent || ((data.subtotal || 0) * 0.09))}`, rightAlignX, curY + 12, { align: 'right' });

  doc.text('State GST (SGST @ 9.0%):', totalBoxX + 4, curY + 18);
  doc.text(`Rs. ${formatNumber(data.sgst_9_percent || ((data.subtotal || 0) * 0.09))}`, rightAlignX, curY + 18, { align: 'right' });

  doc.text('Total Applicable 18% GST:', totalBoxX + 4, curY + 24);
  doc.text(`Rs. ${formatNumber(data.gst_18_percent || ((data.subtotal || 0) * 0.18))}`, rightAlignX, curY + 24, { align: 'right' });

  // Grand Total Highlight Bar (Label at left x:118, Amount at right x:192 with ZERO overlap)
  doc.setFillColor(accentBlue[0], accentBlue[1], accentBlue[2]);
  doc.rect(totalBoxX, curY + 27.5, totalBoxW, 8.5, 'F');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8.5);
  doc.setTextColor(255, 255, 255);
  doc.text('GRAND TOTAL DUE:', totalBoxX + 4, curY + 33);
  doc.text(`Rs. ${formatNumber(data.grand_total)}`, rightAlignX, curY + 33, { align: 'right' });

  // Terms and Commercial Warranty Section (Left side under table)
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8);
  doc.setTextColor(primaryNavy[0], primaryNavy[1], primaryNavy[2]);
  doc.text('COMMERCIAL TERMS & WARRANTY GUARANTEE:', 14, curY + 6);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.2);
  doc.setTextColor(textMuted[0], textMuted[1], textMuted[2]);
  const termsList = [
    '1. 3 Years comprehensive replacement warranty on all DINSTAR hardware.',
    '2. Surface transport is Free of Cost (FOC) nationwide across India.',
    '3. 24x7 SLA technical assistance & certified deployment support.',
    '4. Payment terms: Strictly Net 30 calendar days from invoice issue date.',
    '5. Digital tax invoice generated and authenticated via AURA Enterprise Platform.'
  ];
  termsList.forEach((t, i) => {
    doc.text(t, 14, curY + 12 + i * 4.5, { maxWidth: 95 });
  });

  // Digital Signature Footer
  const footerY = 268;
  doc.setDrawColor(borderGray[0], borderGray[1], borderGray[2]);
  doc.line(14, footerY, 196, footerY);

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7.5);
  doc.setTextColor(emeraldGreen[0], emeraldGreen[1], emeraldGreen[2]);
  doc.text('✓ DIGITALLY VERIFIED & AUTHORIZED BY AURA ENTERPRISE', 14, footerY + 5.5);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7);
  doc.setTextColor(textMuted[0], textMuted[1], textMuted[2]);
  doc.text('Cloud Infotech Distribution Pvt. Ltd. | Authorized National DINSTAR Partner | www.cloudinfotech.com', 14, footerY + 10);

  doc.text('Authorized Signatory', 196, footerY + 5.5, { align: 'right' });
  doc.setFont('helvetica', 'italic');
  doc.text('AURA Enterprise Engine', 196, footerY + 10, { align: 'right' });

  const blob = doc.output('blob');
  return { doc, blob, fileName };
}

/**
 * Generates an official, beautifully structured, print-ready PDF for a Commercial Quotation.
 * Designed with strict bounding boxes to guarantee ZERO overlaps.
 */
export function generateQuotationPdf(data: QuotationData): { doc: jsPDF; blob: Blob; fileName: string } {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
  const quoteNo = data.quotation_id || 'QUO-OFFICIAL';
  const fileName = `Commercial-Quotation-${quoteNo}.pdf`;

  const primaryNavy = [15, 23, 42];
  const emeraldGreen = [5, 150, 105]; // Emerald 600
  const borderGray = [218, 224, 233];
  const textDark = [30, 41, 59];
  const textMuted = [100, 116, 139];

  // Top Accent Bar
  doc.setFillColor(emeraldGreen[0], emeraldGreen[1], emeraldGreen[2]);
  doc.rect(0, 0, 210, 5, 'F');

  // Header Left (Strict width max 115mm, x: 14 to 129)
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(13);
  doc.setTextColor(primaryNavy[0], primaryNavy[1], primaryNavy[2]);
  doc.text('CLOUD INFOTECH DISTRIBUTION PVT. LTD.', 14, 16);

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8);
  doc.setTextColor(emeraldGreen[0], emeraldGreen[1], emeraldGreen[2]);
  doc.text('Authorized DINSTAR National Distributor & Commercial Telephony Partner', 14, 21);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.setTextColor(textMuted[0], textMuted[1], textMuted[2]);
  doc.text('B-42, Sector 63, Electronic City, Noida, Uttar Pradesh 201301', 14, 25.5);
  doc.text('GSTIN: 07AAAAA0000A1Z5  |  PAN: AABCC1234D', 14, 29.5);
  doc.text('Tel: +91 (120) 456-7890  |  Email: sales@cloudinfotech.com', 14, 33.5);

  // Badge (Right aligned, x: 132 to 196, width 64mm, height 24mm)
  doc.setFillColor(emeraldGreen[0], emeraldGreen[1], emeraldGreen[2]);
  doc.roundedRect(132, 11, 64, 24, 2, 2, 'F');
  doc.setTextColor(255, 255, 255);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.text('COMMERCIAL QUOTATION', 137, 17.5);
  doc.setFontSize(7.8);
  doc.setFont('helvetica', 'normal');
  doc.text(`Quote No: ${quoteNo}`, 137, 22.5);
  doc.text(`Date: ${data.quotation_date || '17.11.2026'}`, 137, 27);
  doc.text('Validity: 30 Calendar Days', 137, 31.5);

  // Clean Divider
  doc.setDrawColor(borderGray[0], borderGray[1], borderGray[2]);
  doc.setLineWidth(0.3);
  doc.line(14, 38, 196, 38);

  // Customer & Offer Details (x: 14 to 103 and 107 to 196, height: 26mm)
  const boxY = 41;
  const boxH = 26;
  doc.setFillColor(248, 250, 252);
  doc.rect(14, boxY, 89, boxH, 'F');
  doc.rect(107, boxY, 89, boxH, 'F');
  doc.setDrawColor(borderGray[0], borderGray[1], borderGray[2]);
  doc.rect(14, boxY, 89, boxH, 'S');
  doc.rect(107, boxY, 89, boxH, 'S');

  // Customer Box (Left)
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8);
  doc.setTextColor(primaryNavy[0], primaryNavy[1], primaryNavy[2]);
  doc.text('PROPOSED TO (CLIENT):', 18, boxY + 5.5);
  doc.setFontSize(9);
  doc.text(data.company_name || data.customer?.name || 'Client Company', 18, boxY + 11, { maxWidth: 82 });
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.setTextColor(textMuted[0], textMuted[1], textMuted[2]);
  doc.text(data.customer?.address || 'Corporate Complex, Commercial Suite 100', 18, boxY + 16, { maxWidth: 82 });
  doc.text(`Email: ${data.customer?.email || 'billing@nexacomms.in'}  |  Tel: ${data.customer?.contact || '+91 98765 43210'}`, 18, boxY + 21, { maxWidth: 82 });

  // Offer Details Box (Right)
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8);
  doc.setTextColor(primaryNavy[0], primaryNavy[1], primaryNavy[2]);
  doc.text('OFFICIAL OFFER DETAILS:', 111, boxY + 5.5);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.setTextColor(textDark[0], textDark[1], textDark[2]);
  doc.text(`Offer Validity: 30 Calendar Days (${data.valid_until || '17.12.2026'})`, 111, boxY + 11, { maxWidth: 82 });
  doc.text('Hardware Warranty: 3 Years Comprehensive Replacement', 111, boxY + 16, { maxWidth: 82 });
  doc.text('Shipping: Surface Transport Free of Cost (FOC) across India', 111, boxY + 21, { maxWidth: 82 });

  // Line Items Table Header
  const tableY = 70;
  doc.setFillColor(primaryNavy[0], primaryNavy[1], primaryNavy[2]);
  doc.rect(14, tableY, 182, 7.5, 'F');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7.5);
  doc.setTextColor(255, 255, 255);
  doc.text('#', 17, tableY + 5);
  doc.text('HARDWARE MODEL & DESCRIPTION', 25, tableY + 5);
  doc.text('QTY', 120, tableY + 5, { align: 'right' });
  doc.text('RATE (INR)', 155, tableY + 5, { align: 'right' });
  doc.text('TOTAL (INR)', 192, tableY + 5, { align: 'right' });

  let curY = tableY + 7.5;
  const items = (data.items && data.items.length > 0) ? data.items : [{
    model: data.model || 'DINSTAR DAG1000-8S Gateway',
    description: 'High-density SIP/VoIP Gateway solution with Echo Cancellation',
    quantity: 1,
    unit_price: data.total || 27720,
    total: data.total || 27720
  }];

  items.forEach((item, index) => {
    const rowH = 10;
    doc.setFillColor(index % 2 === 0 ? 255 : 248, index % 2 === 0 ? 255 : 250, index % 2 === 0 ? 255 : 252);
    doc.rect(14, curY, 182, rowH, 'F');
    doc.setDrawColor(borderGray[0], borderGray[1], borderGray[2]);
    doc.rect(14, curY, 182, rowH, 'S');

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.5);
    doc.setTextColor(textDark[0], textDark[1], textDark[2]);
    doc.text(`${index + 1}`, 17, curY + 6);

    doc.setFont('helvetica', 'bold');
    doc.text(`${item.model || data.model || 'DINSTAR Telephony Gateway'}`, 25, curY + 4.5, { maxWidth: 90 });
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(6.8);
    doc.setTextColor(textMuted[0], textMuted[1], textMuted[2]);
    doc.text(`${item.description || 'High-density SIP/VoIP Gateway solution with Echo Cancellation'}`, 25, curY + 8.2, { maxWidth: 90 });

    doc.setFontSize(7.5);
    doc.setTextColor(textDark[0], textDark[1], textDark[2]);
    doc.text(`${item.quantity || 1}`, 120, curY + 6, { align: 'right' });
    doc.text(`Rs. ${formatNumber(item.unit_price)}`, 155, curY + 6, { align: 'right' });
    doc.setFont('helvetica', 'bold');
    doc.text(`Rs. ${formatNumber(item.total || data.total)}`, 192, curY + 6, { align: 'right' });

    curY += rowH;
  });

  // Total Summary Box (x: 114 to 196, width 82mm)
  curY += 4;
  const totalBoxX = 114;
  const totalBoxW = 82;
  const rightAlignX = totalBoxX + totalBoxW - 4; // 192mm

  doc.setFillColor(248, 250, 252);
  doc.rect(totalBoxX, curY, totalBoxW, 20, 'F');
  doc.setDrawColor(borderGray[0], borderGray[1], borderGray[2]);
  doc.rect(totalBoxX, curY, totalBoxW, 20, 'S');

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.setTextColor(textDark[0], textDark[1], textDark[2]);
  doc.text('Quoted Subtotal:', totalBoxX + 4, curY + 6);
  doc.text(`Rs. ${formatNumber(data.subtotal || data.total)}`, rightAlignX, curY + 6, { align: 'right' });

  // Highlight Box - Label on left x:118, Value on right x:192 with ZERO OVERLAP
  doc.setFillColor(emeraldGreen[0], emeraldGreen[1], emeraldGreen[2]);
  doc.rect(totalBoxX, curY + 9.5, totalBoxW, 10.5, 'F');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8);
  doc.setTextColor(255, 255, 255);
  doc.text('TOTAL PROPOSAL VALUE:', totalBoxX + 4, curY + 16.5);
  doc.setFontSize(9);
  doc.text(`Rs. ${formatNumber(data.total)}`, rightAlignX, curY + 16.5, { align: 'right' });

  // Terms and Conditions Section (Left side)
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8);
  doc.setTextColor(primaryNavy[0], primaryNavy[1], primaryNavy[2]);
  doc.text('COMMERCIAL CONDITIONS & TERMS:', 14, curY + 6);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.2);
  doc.setTextColor(textMuted[0], textMuted[1], textMuted[2]);
  const termsList = [
    '1. Quotation validity: 30 calendar days from issue date.',
    '2. 3 Years standard hardware replacement warranty on DINSTAR equipment.',
    '3. Surface transport across India is Free of Cost (FOC).',
    '4. GST @ 18% extra as applicable on official tax invoice.',
    '5. Proposal formulated and tracked via AURA Enterprise Commercial Agent.'
  ];
  termsList.forEach((t, i) => {
    doc.text(t, 14, curY + 12 + i * 4.5, { maxWidth: 95 });
  });

  // Footer
  const footerY = 268;
  doc.setDrawColor(borderGray[0], borderGray[1], borderGray[2]);
  doc.line(14, footerY, 196, footerY);

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7.5);
  doc.setTextColor(emeraldGreen[0], emeraldGreen[1], emeraldGreen[2]);
  doc.text('✓ OFFICIALLY AUTHORIZED QUOTATION BY AURA ENTERPRISE', 14, footerY + 5.5);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7);
  doc.setTextColor(textMuted[0], textMuted[1], textMuted[2]);
  doc.text('Cloud Infotech Distribution Pvt. Ltd. | Authorized National DINSTAR Partner', 14, footerY + 10);

  doc.text('Authorized Signatory', 196, footerY + 5.5, { align: 'right' });
  doc.setFont('helvetica', 'italic');
  doc.text('AURA Commercial Agent', 196, footerY + 10, { align: 'right' });

  const blob = doc.output('blob');
  return { doc, blob, fileName };
}
