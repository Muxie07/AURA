import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools.builtin.customers import customer_get_handler, customer_search_handler
from app.tools.builtin.pricing import pricing_calculate_handler
from app.tools.builtin.products import product_get_handler, product_search_handler
from app.tools.builtin.quotations import quotation_create_draft_handler
from app.tools.schemas import ToolContext


async def main():
    from sqlalchemy import select

    from app.database.base import get_session_factory, initialize_database
    from app.database.models import Organization, Quotation

    await initialize_database()
    factory = get_session_factory()

    async with factory() as db:
        org = (
            await db.execute(select(Organization).where(Organization.slug == "aura-demo-inc"))
        ).scalar_one_or_none()
        if not org:
            print("Org not found!")
            return

        ctx = ToolContext(
            organization_id=org.id,
            user_id=org.id,
            idempotency_key="test-key-2",
            agent_run_id=uuid.uuid4(),
            execution_id=str(uuid.uuid4()),
        )

        try:
            print("\n--- a. Search for Acme Technologies")
            cust_res = await customer_search_handler({"query": "Acme Technologies"}, ctx)
            print("Customer Search:", cust_res)
            cust_id = cust_res["customers"][0]["id"]

            print("\n--- c. Get Acme Technologies")
            get_cust = await customer_get_handler({"customer_id": cust_id}, ctx)
            print("Customer Get:", get_cust)

            print("\n--- b. Find products related to industrial systems")
            prod_search = await product_search_handler({"query": "Server"}, ctx)
            print("Product Search:", prod_search)

            print("\n--- d. Get PROD-X")
            get_prod = await product_get_handler({"product_id": "PROD-X"}, ctx)
            print("Product Get:", get_prod)

            print("\n--- e. Calculate pricing for PROD-X")
            price = await pricing_calculate_handler(
                {"base_price": "5000", "quantity": 1, "discount_percent": "0", "tax_percent": "0"},
                ctx,
            )
            print("Calculate Pricing:", price)

            print("\n--- f. Create a draft quotation for Acme Technologies using PROD-X")
            q_res = await quotation_create_draft_handler(
                {"customer_id": cust_id, "items": [{"product_id": "PROD-X", "quantity": 1}]}, ctx
            )
            print("Quotation Creation:", q_res)

            # Verify in DB
            q = (
                await db.execute(select(Quotation).where(Quotation.id == q_res["quotation_id"]))
            ).scalar_one_or_none()
            print("\nQuotation in DB ID:", q.id if q else None)
            print("Quotation in DB Total:", q.total if q else None)
            print("Quotation in DB Status:", q.status if q else None)

        except Exception as e:
            print("Error:", e)


if __name__ == "__main__":
    asyncio.run(main())
