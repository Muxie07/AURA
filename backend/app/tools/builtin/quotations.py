import uuid
from decimal import Decimal
from typing import Any
import sqlalchemy as sa
from app.tools.executor import InternalToolExecutor
from app.tools.schemas import RiskLevel, ToolContext, ToolDefinition
from app.database.base import get_session_factory
from app.database.models import Customer, Product, Quotation

async def quotation_create_draft_handler(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    cust_id = arguments.get("customer_id", "")
    items = arguments.get("items", [])

    async with get_session_factory()() as db:
        # Validate customer
        c_stmt = sa.select(Customer).where(Customer.id == cust_id, Customer.organization_id == context.organization_id)
        cust = (await db.execute(c_stmt)).scalar_one_or_none()
        if not cust:
            raise ValueError("Invalid or unauthorized customer.")

        total = Decimal("0.00")
        for item in items:
            prod_id = item.get("product_id")
            p_stmt = sa.select(Product).where(Product.id == prod_id, Product.organization_id == context.organization_id)
            prod = (await db.execute(p_stmt)).scalar_one_or_none()
            if not prod:
                raise ValueError(f"Invalid or unauthorized product: {prod_id}")

            base_price = Decimal(str(prod.base_price))
            qty = Decimal(str(item.get("quantity", 1)))
            total += (base_price * qty)

        qid = f"Q-{uuid.uuid4().hex[:8].upper()}"
        quotation = Quotation(
            id=qid,
            organization_id=context.organization_id,
            customer_id=cust_id,
            items=items,
            total=str(total),
            status="draft",
            idempotency_key=context.idempotency_key
        )
        db.add(quotation)
        await db.commit()
        
        return {"quotation_id": qid, "total": str(total), "status": "draft"}

quotation_create_draft_def = ToolDefinition(
    name="quotation.create_draft",
    description="Create a quotation draft.",
    input_schema={
        "type": "object",
        "properties": {
            "customer_id": {"type": "string"},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string"},
                        "quantity": {"type": "integer"}
                    },
                    "required": ["product_id", "quantity"]
                }
            }
        },
        "required": ["customer_id", "items"]
    },
    risk_level=RiskLevel.WRITE,
    idempotent=True
)

quotation_create_draft_tool = InternalToolExecutor(quotation_create_draft_def, quotation_create_draft_handler)
