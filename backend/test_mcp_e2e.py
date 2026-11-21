import asyncio
import os
import uuid

from sqlalchemy import text

from app.database.base import get_session_factory
from app.tools.mcp.client import MCPClientManager
from app.tools.schemas import ToolContext


async def test_mcp():
    from app.database.base import initialize_database
    await initialize_database()
    factory = get_session_factory()
    async with factory() as db:
        # Get an org ID
        res = await db.execute(text("SELECT id FROM organizations LIMIT 1"))
        org_id = res.scalar()
        if not org_id:
            print("No org found")
            return

        mcp_manager = MCPClientManager()
        try:
            mcp_url = "http://localhost:8000/api/v1/mcp/messages"
            print("Discovering tools via MCP...")
            executors = await mcp_manager.discover_tools(mcp_url, str(org_id))

            customer_search = None
            for e in executors:
                if e.definition.name == "mcp.customer.search":
                    customer_search = e
                    break

            if not customer_search:
                print("mcp.customer.search not found in discovered tools")
                return

            print(f"Found tool: {customer_search.definition.name}")

            ctx = ToolContext(
                organization_id=org_id,
                agent_run_id=(await db.execute(text('SELECT id FROM agent_runs LIMIT 1'))).scalar(),
                execution_id=(await db.execute(text('SELECT id FROM agent_runs LIMIT 1'))).scalar().hex,
                dry_run=False,
                idempotency_key=None
            )

            print("Executing mcp.customer.search...")
            result = await customer_search.execute({"query": "Acme"}, ctx)
            print("Result Status:", result.status)
            print("Result Content:", result.result)

        finally:
            await mcp_manager.close()

if __name__ == "__main__":
    asyncio.run(test_mcp())



