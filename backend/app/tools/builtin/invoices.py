import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from app.tools.executor import InternalToolExecutor
from app.tools.schemas import RiskLevel, ToolContext, ToolDefinition

# Cloud Infotech Catalog based on Distribution Price List
CLOUD_INFOTECH_CATALOG = {
    "UC-2000-VE-2T": {
        "model": "UC-2000-VE-2T",
        "category": "DINSTAR GSM- Volte Gateway",
        "description": "2 Port GSM Volte Gateway with SIP Trunk & Echo Cancellation",
        "msp": 26250.0,
        "retail": 28875.0,
        "end_customer": 31763.0,
        "mrp": 34939.0,
    },
    "UC-2000-VE-4T": {
        "model": "UC-2000-VE-4T",
        "category": "DINSTAR GSM- Volte Gateway",
        "description": "4 Port GSM Volte Gateway with SIP Trunk & Echo Cancellation",
        "msp": 35000.0,
        "retail": 38500.0,
        "end_customer": 42350.0,
        "mrp": 46585.0,
    },
    "UC-2000-VE-8T": {
        "model": "UC-2000-VE-8T",
        "category": "DINSTAR GSM- Volte Gateway",
        "description": "8 Port GSM Volte Gateway with SIP Trunk & Echo Cancellation",
        "msp": 61560.0,
        "retail": 67716.0,
        "end_customer": 74488.0,
        "mrp": 81936.0,
    },
    "UC-2000-VF-16T": {
        "model": "UC-2000-VF-16T",
        "category": "DINSTAR GSM- Volte Gateway",
        "description": "16 Port GSM Volte Gateway Enterprise Rackmount",
        "msp": 112000.0,
        "retail": 123200.0,
        "end_customer": 135520.0,
        "mrp": 149072.0,
    },
    "UC-2000-VG-32T": {
        "model": "UC-2000-VG-32T",
        "category": "DINSTAR GSM- Volte Gateway",
        "description": "32 Port GSM Volte Gateway Enterprise High Density",
        "msp": 150000.0,
        "retail": 165000.0,
        "end_customer": 181500.0,
        "mrp": 199650.0,
    },
    "DAG1000-2S": {
        "model": "DAG1000-2S",
        "category": "DINSTAR FXO/FXS Gateway",
        "description": "2 Port ATA Analog VoIP Gateway",
        "msp": 3500.0,
        "retail": 3850.0,
        "end_customer": 4235.0,
        "mrp": 4659.0,
    },
    "DAG1000-4S": {
        "model": "DAG1000-4S",
        "category": "DINSTAR FXO/FXS Gateway",
        "description": "4 FXS G.711A/U law, G.723.1, Echo cancellation, IPv4/IPv6",
        "msp": 7350.0,
        "retail": 8085.0,
        "end_customer": 8894.0,
        "mrp": 9783.0,
    },
    "DAG1000-8S": {
        "model": "DAG1000-8S",
        "category": "DINSTAR FXO/FXS Gateway",
        "description": "8 FXS Analog Gateway with G.711A/U, Echo Cancellation",
        "msp": 12600.0,
        "retail": 13860.0,
        "end_customer": 15246.0,
        "mrp": 16771.0,
    },
    "DAG2000-16S": {
        "model": "DAG2000-16S",
        "category": "DINSTAR FXO/FXS Gateway",
        "description": "16 FXS Analog VoIP Gateway Rackmount",
        "msp": 21000.0,
        "retail": 23100.0,
        "end_customer": 25410.0,
        "mrp": 27951.0,
    },
    "DAG2000-24S": {
        "model": "DAG2000-24S",
        "category": "DINSTAR FXO/FXS Gateway",
        "description": "24 FXS Analog VoIP Gateway Rackmount",
        "msp": 24000.0,
        "retail": 26400.0,
        "end_customer": 29040.0,
        "mrp": 31944.0,
    },
    "DAG1000-4S4O": {
        "model": "DAG1000-4S4O",
        "category": "DINSTAR FXO/FXS Gateway",
        "description": "4 FXS + 4 FXO Hybrid VoIP Gateway",
        "msp": 15500.0,
        "retail": 17050.0,
        "end_customer": 18755.0,
        "mrp": 20631.0,
    },
    "DAG1000-8S8O": {
        "model": "DAG1000-8S8O",
        "category": "DINSTAR FXO/FXS Gateway",
        "description": "8 FXS + 8 FXO Hybrid VoIP Gateway",
        "msp": 29000.0,
        "retail": 31900.0,
        "end_customer": 35090.0,
        "mrp": 38599.0,
    },
    "UC120 Series": {
        "model": "UC120 Series",
        "category": "IP PBX",
        "description": "Hybrid IPPBX Appliance with 2 FXO Ports",
        "msp": 12600.0,
        "retail": 13860.0,
        "end_customer": 15246.0,
        "mrp": 16771.0,
    },
    "UC200 Series": {
        "model": "UC200 Series",
        "category": "IP PBX",
        "description": "Hybrid IPPBX Appliance with 2 FXS + 2 FXO Ports",
        "msp": 26250.0,
        "retail": 28875.0,
        "end_customer": 31763.0,
        "mrp": 34939.0,
    },
    "SBC300-10": {
        "model": "SBC300-10",
        "category": "Session Border Controller",
        "description": "10 Concurrent Calls and 10 Transcoding Sessions",
        "msp": 36500.0,
        "retail": 40150.0,
        "end_customer": 44165.0,
        "mrp": 48582.0,
    },
    "SBC300-20": {
        "model": "SBC300-20",
        "category": "Session Border Controller",
        "description": "20 Concurrent Calls and 20 Transcoding Sessions",
        "msp": 46800.0,
        "retail": 51480.0,
        "end_customer": 56628.0,
        "mrp": 62291.0,
    },
    "SBC1000-050": {
        "model": "SBC1000-050",
        "category": "Session Border Controller",
        "description": "50 Concurrent Calls and 50 Transcoding Sessions",
        "msp": 183800.0,
        "retail": 202180.0,
        "end_customer": 222398.0,
        "mrp": 244638.0,
    },
    "SBC3000 Chassis": {
        "model": "SBC3000 Chassis",
        "category": "Session Border Controller",
        "description": "SBC3000 Chassis + MCU (Dual MCU Backup)",
        "msp": 272700.0,
        "retail": 299970.0,
        "end_customer": 329967.0,
        "mrp": 362964.0,
    },
}

MOCK_COMPANIES = {
    "acme": {
        "name": "Acme Technologies Pvt. Ltd.",
        "address": "100 Innovation Way, Tech Park Suite 400, Austin, TX 78701",
        "gstin": "07AAACA1234B1ZP",
        "email": "billing@acme.com",
        "contact": "+1 (512) 555-0199",
    },
    "global": {
        "name": "Global Telecom Networks Ltd.",
        "address": "Tower B, 7th Floor, DLF Cyber City, Gurugram, Haryana 122002",
        "gstin": "06AABCG9876C1ZQ",
        "email": "procurement@globaltelecom.com",
        "contact": "+91 (124) 492-8000",
    },
    "nexa": {
        "name": "Nexa Communications Pvt. Ltd.",
        "address": "Plot 14, Electronic City Phase 1, Bengaluru, Karnataka 560100",
        "gstin": "29AABCN5432D1ZR",
        "email": "billing@nexacomms.in",
        "contact": "+91 (80) 6789-1234",
    },
    "apex": {
        "name": "Apex Enterprise Solutions",
        "address": "402 Financial District, Nanakramguda, Hyderabad, Telangana 500032",
        "gstin": "36AABCA8765E1ZS",
        "email": "finance@apexenterprise.com",
        "contact": "+91 (40) 2345-6789",
    },
    "cloud infotech": {
        "name": "Cloud Infotech Distribution Partner",
        "address": "B-42, Sector 63, Noida, Uttar Pradesh 201301",
        "gstin": "07AAAAA0000A1Z5",
        "email": "sales@cloudinfotech.com",
        "contact": "+91 (120) 456-7890",
    },
}


async def invoice_generate_handler(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    company_query = arguments.get("company_name", "Acme Technologies").strip()
    model_query = arguments.get("model_number", "UC-2000-VE-4T").strip()
    qty = max(1, int(arguments.get("quantity", 1)))
    tier = arguments.get("price_tier", "end_customer").lower()

    # Find company
    matched_company = None
    for key, c in MOCK_COMPANIES.items():
        if key in company_query.lower() or company_query.lower() in c["name"].lower():
            matched_company = c
            break
    if not matched_company:
        matched_company = {
            "name": company_query,
            "address": "Corporate Commercial Complex, Suite 100",
            "gstin": "07AAAAA1234Z1ZP",
            "email": f"accounts@{company_query.lower().replace(' ', '')}.com",
            "contact": "+91 98765 43210",
        }

    # Find product in catalog
    matched_product = None
    for key, p in CLOUD_INFOTECH_CATALOG.items():
        if key.lower() in model_query.lower() or model_query.lower() in key.lower():
            matched_product = p
            break
    if not matched_product:
        # Default fallback product from catalog
        matched_product = CLOUD_INFOTECH_CATALOG["UC-2000-VE-4T"]

    # Determine unit rate based on requested tier
    unit_price = matched_product["end_customer"]
    tier_label = "End-Customer Price"
    if "retail" in tier:
        unit_price = matched_product["retail"]
        tier_label = "Retail Price"
    elif "msp" in tier:
        unit_price = matched_product["msp"]
        tier_label = "MSP (Distributor Price)"
    elif "mrp" in tier:
        unit_price = matched_product["mrp"]
        tier_label = "MRP"

    subtotal = float(Decimal(str(unit_price)) * Decimal(str(qty)))
    gst_18 = round(subtotal * 0.18, 2)
    grand_total = round(subtotal + gst_18, 2)

    now = datetime.now(timezone.utc)
    inv_id = f"INV-2026-CI-{uuid.uuid4().hex[:6].upper()}"

    invoice_data = {
        "invoice_id": inv_id,
        "invoice_date": now.strftime("%d.%m.%Y"),
        "due_date": (now + timedelta(days=30)).strftime("%d.%m.%Y"),
        "distributor": {
            "name": "Cloud Infotech Distribution Pvt. Ltd.",
            "subtitle": "Authorized Dinstar National Distributor",
            "address": "B-42, Sector 63, Electronic City, Noida, UP 201301",
            "gstin": "07AAAAA0000A1Z5",
            "email": "invoices@cloudinfotech.com",
            "phone": "+91 (120) 456-7890",
        },
        "billed_to": matched_company,
        "pricing_tier": tier_label,
        "items": [
            {
                "model": matched_product["model"],
                "category": matched_product["category"],
                "description": matched_product["description"],
                "quantity": qty,
                "unit_price": unit_price,
                "gst_rate_percent": 18,
                "gst_amount": gst_18,
                "total": subtotal,
            }
        ],
        "subtotal": subtotal,
        "cgst_9_percent": round(gst_18 / 2, 2),
        "sgst_9_percent": round(gst_18 / 2, 2),
        "gst_18_percent": gst_18,
        "grand_total": grand_total,
        "currency": "INR",
        "currency_symbol": "₹",
        "terms": [
            "Extra @ 18% GST included in final billed calculation.",
            "3 Years comprehensive hardware warranty on all DINSTAR products.",
            "Surface transport charges are Free of Cost (FOC) across India.",
            "Air Freight charges extra on actual billed value.",
            "24*7 Technical support & emergency SLA response.",
            "Payment strictly within 30 days of invoice date.",
        ],
        "status": "APPROVED",
    }
    return invoice_data


invoice_generate_def = ToolDefinition(
    name="invoice.generate",
    description="Generate an official tax invoice according to the Cloud Infotech Distribution Price List.",
    input_schema={
        "type": "object",
        "properties": {
            "company_name": {"type": "string", "description": "Customer company name"},
            "model_number": {"type": "string", "description": "Product model number from Cloud Infotech catalog"},
            "quantity": {"type": "integer", "description": "Quantity to order", "default": 1},
            "price_tier": {
                "type": "string",
                "enum": ["end_customer", "retail", "msp", "mrp"],
                "default": "end_customer",
            },
        },
        "required": ["company_name", "model_number"],
    },
    risk_level=RiskLevel.WRITE,
    idempotent=True,
)

invoice_generate_tool = InternalToolExecutor(invoice_generate_def, invoice_generate_handler)
