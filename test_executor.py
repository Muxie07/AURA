import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.tools.builtin.quotations import quotation_create_draft_handler
from app.tools.builtin.customers import customer_search_handler
from app.tools.schemas import ToolContext

async def main():
    org_id = "00000000-0000-0000-0000-000000000000" # We need the actual org id
    from app.database.base import get_session_factory, initialize_database
    from sqlalchemy import select
    from app.database.models import Organization, Quotation
    
    await initialize_database()
    factory = get_session_factory()
    
    async with factory() as db:
        org = (await db.execute(select(Organization).where(Organization.slug == "aura-demo-inc"))).scalar_one_or_none()
        if not org:
            print("Org not found!")
            return
        
        ctx = ToolContext(
            organization_id=org.id,
            user_id=org.id,
            idempotency_key="test-key-1"
        )
        
        try:
            cust_res = await customer_search_handler({"query": "Acme Technologies"}, ctx)
            print("Customer Search:", cust_res)
            
            cust_id = cust_res["results"][0]["id"]
            
            q_res = await quotation_create_draft_handler({
                "customer_id": cust_id,
                "items": [{"product_id": "PROD-X", "quantity": 1}]
            }, ctx)
            
            print("Quotation Creation:", q_res)
            
            # Verify in DB
            q = (await db.execute(select(Quotation).where(Quotation.id == q_res["quotation_id"]))).scalar_one_or_none()
            print("Quotation in DB:", q.id if q else None)
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
