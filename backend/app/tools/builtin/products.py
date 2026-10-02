from typing import Any

import sqlalchemy as sa

from app.database.base import get_session_factory
from app.database.models import Product
from app.tools.executor import InternalToolExecutor
from app.tools.schemas import RiskLevel, ToolContext, ToolDefinition


async def product_search_handler(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    query = arguments.get("query", "").lower()
    async with get_session_factory()() as db:
        stmt = sa.select(Product).where(Product.organization_id == context.organization_id)
        if query:
            stmt = stmt.where(
                sa.or_(
                    sa.func.lower(Product.name).like(f"%{query.replace('%', r'\%').replace('_', r'\_')}%", escape="\\"),
                    sa.func.lower(Product.sku).like(f"%{query.replace('%', r'\%').replace('_', r'\_')}%", escape="\\"),
                )
            )
        result = await db.execute(stmt)
        products = result.scalars().all()
        return {
            "products": [
                {
                    "id": p.id,
                    "name": p.name,
                    "sku": p.sku,
                    "availability": p.availability,
                    "base_price": float(p.base_price),
                    "org_id": str(p.organization_id),
                }
                for p in products
            ]
        }


product_search_def = ToolDefinition(
    name="product.search",
    description="Search for products by name or SKU.",
    input_schema={
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
    risk_level=RiskLevel.READ,
)


async def product_get_handler(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    prod_id = arguments.get("product_id", "")
    async with get_session_factory()() as db:
        stmt = sa.select(Product).where(
            Product.id == prod_id, Product.organization_id == context.organization_id
        )
        result = await db.execute(stmt)
        p = result.scalar_one_or_none()
        if not p:
            raise ValueError(f"Product {prod_id} not found or access denied.")
        return {
            "id": p.id,
            "name": p.name,
            "sku": p.sku,
            "availability": p.availability,
            "base_price": float(p.base_price),
            "org_id": str(p.organization_id),
        }


product_get_def = ToolDefinition(
    name="product.get",
    description="Get exact product by ID.",
    input_schema={
        "type": "object",
        "properties": {"product_id": {"type": "string"}},
        "required": ["product_id"],
    },
    risk_level=RiskLevel.READ,
)

product_search_tool = InternalToolExecutor(product_search_def, product_search_handler)
product_get_tool = InternalToolExecutor(product_get_def, product_get_handler)
