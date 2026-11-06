import uuid
from decimal import Decimal
from typing import Any

import sqlalchemy as sa

from app.database.base import get_session_factory
from app.database.models import Customer, Product, Quotation
from app.tools.builtin.invoices import CLOUD_INFOTECH_CATALOG
from app.tools.executor import InternalToolExecutor
from app.tools.schemas import RiskLevel, ToolContext, ToolDefinition

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

        # Match catalog model
        catalog_item = None
        for key, val in CLOUD_INFOTECH_CATALOG.items():
            if key.lower() == model_number.lower():
                catalog_item = val
                break

        if not catalog_item:
            # Fuzzy model search
            for key, val in CLOUD_INFOTECH_CATALOG.items():
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

        qid = f"Q-2026-{uuid.uuid4().hex[:6].upper()}"

        return {
            "quotation_id": qid,
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
                "24*7 Technical support and emergency SLA coverage."
            ],
        }

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
