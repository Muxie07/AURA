from decimal import Decimal
from typing import Any

import sqlalchemy as sa

from app.database.base import get_session_factory
from app.database.models import Product
from app.tools.executor import InternalToolExecutor
from app.tools.schemas import RiskLevel, ToolContext, ToolDefinition


async def pricing_get_handler(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    prod_id = arguments.get("product_id", "")
    async with get_session_factory()() as db:
        stmt = sa.select(Product).where(
            Product.id == prod_id, Product.organization_id == context.organization_id
        )
        result = await db.execute(stmt)
        p = result.scalar_one_or_none()
        if not p:
            raise ValueError(f"Product {prod_id} not found or access denied.")

        return {"product_id": prod_id, "base_price": f"{p.base_price:.2f}", "currency": "USD"}


pricing_get_def = ToolDefinition(
    name="pricing.get",
    description="Get base pricing for a product.",
    input_schema={
        "type": "object",
        "properties": {"product_id": {"type": "string"}},
        "required": ["product_id"],
    },
    risk_level=RiskLevel.READ,
)


async def pricing_calculate_handler(
    arguments: dict[str, Any], context: ToolContext
) -> dict[str, Any]:
    base_price = Decimal(str(arguments.get("base_price", "0.00")))
    quantity = Decimal(str(arguments.get("quantity", "1")))
    discount_pct = Decimal(str(arguments.get("discount_percent", "0")))
    tax_pct = Decimal(str(arguments.get("tax_percent", "0")))

    subtotal = base_price * quantity
    discount_amt = subtotal * (discount_pct / Decimal("100"))
    after_discount = subtotal - discount_amt
    tax_amt = after_discount * (tax_pct / Decimal("100"))
    total = after_discount + tax_amt

    return {
        "subtotal": f"{subtotal:.4f}",
        "discount_amount": f"{discount_amt:.4f}",
        "after_discount": f"{after_discount:.4f}",
        "tax_amount": f"{tax_amt:.4f}",
        "total": f"{total:.4f}",
        "currency": "USD",
    }


pricing_calculate_def = ToolDefinition(
    name="pricing.calculate",
    description="Calculate exact quotation totals.",
    input_schema={
        "type": "object",
        "properties": {
            "base_price": {"type": "string"},
            "quantity": {"type": "integer"},
            "discount_percent": {"type": "string"},
            "tax_percent": {"type": "string"},
        },
        "required": ["base_price", "quantity"],
    },
    risk_level=RiskLevel.READ,
)

pricing_get_tool = InternalToolExecutor(pricing_get_def, pricing_get_handler)
pricing_calculate_tool = InternalToolExecutor(pricing_calculate_def, pricing_calculate_handler)
