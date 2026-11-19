import json
import os
import tempfile
import uuid
from datetime import UTC
from decimal import Decimal
from typing import Any

import sqlalchemy as sa

from app.database.base import get_session_factory
from app.database.models import Customer, Product, Quotation
from app.tools.builtin.invoices import CLOUD_INFOTECH_CATALOG
from app.tools.executor import InternalToolExecutor
from app.tools.schemas import RiskLevel, ToolContext, ToolDefinition

QUOTATIONS_STORE_FILE = os.path.join(tempfile.gettempdir(), "aura_quotations_store.json")


def _get_redis_sync():
    try:
        import redis

        from app.config.settings import get_settings

        return redis.from_url(get_settings().redis_url, socket_timeout=1.0)
    except Exception:
        return None


def _load_stored_quotations() -> list[dict[str, Any]]:
    # Try Redis first
    r = _get_redis_sync()
    if r:
        try:
            raw = r.get("aura:stored_quotations")
            if raw:
                loaded = json.loads(raw)
                if isinstance(loaded, list) and len(loaded) > 0:
                    return loaded
        except Exception:
            pass
    # Fallback to local file
    if os.path.exists(QUOTATIONS_STORE_FILE):
        try:
            with open(QUOTATIONS_STORE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _write_stored_quotations(quotes: list[dict[str, Any]]) -> None:
    # Save to Redis
    r = _get_redis_sync()
    if r:
        try:
            r.set("aura:stored_quotations", json.dumps(quotes))
        except Exception:
            pass
    # Save to local file
    try:
        with open(QUOTATIONS_STORE_FILE, "w", encoding="utf-8") as f:
            json.dump(quotes, f, indent=2)
    except Exception:
        pass


def save_generated_quotation(quotation: dict[str, Any]) -> None:
    try:
        quotes = _load_stored_quotations()
        quotes = [q for q in quotes if q.get("quotation_id") != quotation.get("quotation_id")]
        quotes.insert(0, quotation)
        _write_stored_quotations(quotes[:100])
    except Exception:
        pass
    try:
        from app.tools.builtin.commercial_kb import sync_ingest_quotation

        sync_ingest_quotation(quotation)
    except Exception:
        pass


def find_stored_quotation(query: str = "") -> dict[str, Any] | None:
    quotes = _load_stored_quotations()
    if not quotes:
        return None
    q = (query or "").strip().lower()
    if not q or q in ("current", "latest", "recent", "last", "quotation", "quote"):
        return quotes[0]

    noise = [
        "show",
        "me",
        "the",
        "current",
        "quotation",
        "quote",
        "for",
        "please",
        "get",
        "fetch",
        "view",
        "what",
        "is",
        "where",
    ]
    clean_parts = [w for w in q.split() if w not in noise]
    clean_q = " ".join(clean_parts).strip() if clean_parts else q

    for quote in quotes:
        comp_name = quote.get("company_name", quote.get("customer", {}).get("name", "")).lower()
        qid = quote.get("quotation_id", "").lower()
        if (
            (clean_q and clean_q in comp_name)
            or (comp_name and comp_name in clean_q)
            or clean_q in qid
        ):
            return quote

    for quote in quotes:
        comp_name = quote.get("company_name", quote.get("customer", {}).get("name", "")).lower()
        if any(part in comp_name for part in clean_parts if len(part) > 1):
            return quote

    if any(k in q for k in ["current", "latest", "recent", "last", "today"]) or len(quotes) == 1:
        return quotes[0]

    return quotes[0]


# Default enterprise mock clients
MOCK_COMPANIES = {
    "acme": {
        "name": "Acme Technologies",
        "email": "contact@acme.com",
        "address": "100 Innovation Way, Austin, TX",
    },
    "global telecom": {
        "name": "Global Telecom Ltd",
        "email": "procurement@globaltelecom.com",
        "address": "Cyber City, Gurugram, HR",
    },
    "nexa": {
        "name": "Nexa Communications",
        "email": "billing@nexacomms.in",
        "address": "Electronic City, Bangalore, KA",
    },
    "apex": {
        "name": "Apex Enterprise",
        "email": "finance@apexenterprise.com",
        "address": "Financial District, Hyderabad, TS",
    },
    "cloud infotech": {
        "name": "Cloud Infotech Partner",
        "email": "sales@cloudinfotech.com",
        "address": "Sector 63, Noida, UP",
    },
}


async def quotation_create_draft_handler(
    arguments: dict[str, Any], context: ToolContext
) -> dict[str, Any]:
    """
    Creates an official quotation draft.
    Supports both flexible commercial configuration (company_name, model_number,
    quantity, tier) and database UUID lookups.
    """
    company_name = arguments.get("company_name", "").strip()
    model_number = arguments.get("model_number", "") or arguments.get("model", "")
    quantity = int(arguments.get("quantity", 1))
    price_tier = arguments.get("price_tier", "end_customer").lower()
    discount_pct = float(arguments.get("discount_percent", 0.0))

    cust_id = arguments.get("customer_id", "")
    items = arguments.get("items", [])

    # Path A: Flexible commercial quotation generation
    if company_name or model_number or not cust_id:
        # Match company
        matched_comp = None
        lower_comp = company_name.lower()
        for key, val in MOCK_COMPANIES.items():
            if key in lower_comp or lower_comp in key:
                matched_comp = val
                break

        if not matched_comp:
            matched_comp = {
                "name": company_name if company_name else "Client Enterprise",
                "email": arguments.get("email", "billing@cliententerprise.com"),
                "address": arguments.get("address", "Corporate Tower, Suite 400"),
            }

        # Match catalog model (exact match first, then longest matching key)
        catalog_item = None
        for key, val in CLOUD_INFOTECH_CATALOG.items():
            if key.lower() == model_number.lower():
                catalog_item = val
                break

        if not catalog_item:
            for key in sorted(CLOUD_INFOTECH_CATALOG.keys(), key=len, reverse=True):
                if model_number.lower() in key.lower() or key.lower() in model_number.lower():
                    catalog_item = val
                    break

        if not catalog_item:
            # Fallback to standard enterprise product or default
            catalog_item = {
                "model": model_number if model_number else "Enterprise Server (ENT-DB-001)",
                "category": "Enterprise Communications Solution",
                "description": "Enterprise High-Availability Instance with 24/7 Monitoring & Backups",
                "end_customer": 42350.0,
                "retail": 38500.0,
                "msp": 35000.0,
                "mrp": 46585.0,
            }

        unit_price = float(catalog_item.get(price_tier, catalog_item.get("end_customer", 42350.0)))
        subtotal = unit_price * quantity
        discount_val = subtotal * (discount_pct / 100.0)
        taxable_value = subtotal - discount_val

        from datetime import datetime, timedelta

        now_utc = datetime.now(UTC)
        now_ist = now_utc + timedelta(hours=5, minutes=30)
        created_at = now_ist.isoformat()
        created_date_formatted = now_ist.strftime("%A, %d %B %Y, %I:%M %p") + " IST"
        q_date = now_ist.strftime("%d.%m.%Y")
        valid_until = (now_ist + timedelta(days=30)).strftime("%d.%m.%Y")
        valid_until_formatted = (now_ist + timedelta(days=30)).strftime("%d %B %Y")

        qid = f"Q-2026-{uuid.uuid4().hex[:6].upper()}"

        quote_res = {
            "quotation_id": qid,
            "created_at": created_at,
            "created_date_formatted": created_date_formatted,
            "quotation_date": q_date,
            "valid_until": valid_until,
            "valid_until_formatted": valid_until_formatted,
            "status": "draft",
            "company_name": matched_comp["name"],
            "customer": matched_comp,
            "model": catalog_item["model"],
            "product_name": f"{catalog_item['model']} - {catalog_item['description']}",
            "quantity": quantity,
            "unit_price": f"{unit_price:,.2f}",
            "items": [
                {
                    "model": catalog_item["model"],
                    "description": catalog_item["description"],
                    "category": catalog_item.get("category", "Hardware & Telecom"),
                    "quantity": quantity,
                    "unit_price": f"{unit_price:,.2f}",
                    "discount_percent": discount_pct,
                    "total": f"{taxable_value:,.2f}",
                }
            ],
            "subtotal": f"{subtotal:,.2f}",
            "discount": f"{discount_val:,.2f}",
            "total": f"{taxable_value:,.2f}",
            "currency": "INR",
            "validity": "30 Calendar Days",
            "terms": [
                "Strictly 30 days upon invoice issuance.",
                "Valid for 30 calendar days from issue date.",
                "Prices based on official Cloud Infotech commercial distribution rate card.",
                "Hardware includes 3 Years standard replacement warranty.",
                "Surface transport across India is Free of Cost (FOC).",
                "24*7 Technical support and emergency SLA coverage.",
            ],
        }
        save_generated_quotation(quote_res)
        return quote_res

    # Path B: Database UUID lookup
    async with get_session_factory()() as db:
        c_stmt = sa.select(Customer).where(
            Customer.id == cust_id, Customer.organization_id == context.organization_id
        )
        cust = (await db.execute(c_stmt)).scalar_one_or_none()
        if not cust:
            raise ValueError("Invalid or unauthorized customer.")

        total = Decimal("0.00")
        for item in items:
            prod_id = item.get("product_id")
            p_stmt = sa.select(Product).where(
                Product.id == prod_id, Product.organization_id == context.organization_id
            )
            prod = (await db.execute(p_stmt)).scalar_one_or_none()
            if not prod:
                raise ValueError(f"Invalid or unauthorized product: {prod_id}")

            base_price = Decimal(str(prod.base_price))
            qty = Decimal(str(item.get("quantity", 1)))
            total += base_price * qty

        qid = f"Q-2026-{uuid.uuid4().hex[:6].upper()}"
        from app.database.models import QuotationItem

        quotation = Quotation(
            code=qid,
            organization_id=context.organization_id,
            customer_id=cust_id,
            total=str(total),
            status="draft",
            idempotency_key=context.idempotency_key,
        )

        for item in items:
            quotation.items.append(
                QuotationItem(
                    product_id=item["product_id"],
                    qty=item.get("qty", 1),
                    unit_price=item.get("unit_price", 0.0),
                    discount=item.get("discount", 0.0),
                )
            )

        db.add(quotation)
        await db.commit()

        return {
            "quotation_id": qid,
            "total": str(total),
            "status": "draft",
            "customer": {"name": cust.name, "email": cust.email or ""},
            "company_name": cust.name,
        }


quotation_create_draft_def = ToolDefinition(
    name="quotation.create_draft",
    description="Create a quotation draft with itemized pricing, company details, and commercial terms.",
    input_schema={
        "type": "object",
        "properties": {
            "company_name": {"type": "string"},
            "model_number": {"type": "string"},
            "quantity": {"type": "integer"},
            "price_tier": {"type": "string"},
            "discount_percent": {"type": "number"},
            "customer_id": {"type": "string"},
            "items": {"type": "array"},
        },
        "required": [],
    },
    risk_level=RiskLevel.WRITE,
    idempotent=True,
)

quotation_create_draft_tool = InternalToolExecutor(
    quotation_create_draft_def, quotation_create_draft_handler
)
