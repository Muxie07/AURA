from typing import Any

import sqlalchemy as sa

from app.database.base import get_session_factory
from app.database.models import Customer
from app.tools.executor import InternalToolExecutor
from app.tools.schemas import RiskLevel, ToolContext, ToolDefinition


async def customer_search_handler(
    arguments: dict[str, Any], context: ToolContext
) -> dict[str, Any]:
    query = arguments.get("query", "").lower()
    async with get_session_factory()() as db:
        stmt = sa.select(Customer).where(Customer.organization_id == context.organization_id)
        if query:
            stmt = stmt.where(
                sa.or_(
                    sa.func.lower(Customer.name).like(f"%{query.replace('%', r'\%').replace('_', r'\_')}%", escape="\\"),
                    sa.func.lower(Customer.email).like(f"%{query.replace('%', r'\%').replace('_', r'\_')}%", escape="\\"),
                )
            )
        result = await db.execute(stmt)
        customers = result.scalars().all()
        return {
            "customers": [
                {"id": c.id, "name": c.name, "email": c.email, "org_id": str(c.organization_id)}
                for c in customers
            ]
        }


customer_search_def = ToolDefinition(
    name="customer.search",
    description="Search for customers by name or email.",
    input_schema={
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
    risk_level=RiskLevel.READ,
)


async def customer_get_handler(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    cust_id = arguments.get("customer_id", "")
    async with get_session_factory()() as db:
        stmt = sa.select(Customer).where(
            Customer.id == cust_id, Customer.organization_id == context.organization_id
        )
        result = await db.execute(stmt)
        c = result.scalar_one_or_none()
        if not c:
            raise ValueError(f"Customer {cust_id} not found or access denied.")
        return {"id": c.id, "name": c.name, "email": c.email, "org_id": str(c.organization_id)}


customer_get_def = ToolDefinition(
    name="customer.get",
    description="Get exact customer by ID.",
    input_schema={
        "type": "object",
        "properties": {"customer_id": {"type": "string"}},
        "required": ["customer_id"],
    },
    risk_level=RiskLevel.READ,
)

customer_search_tool = InternalToolExecutor(customer_search_def, customer_search_handler)
customer_get_tool = InternalToolExecutor(customer_get_def, customer_get_handler)
