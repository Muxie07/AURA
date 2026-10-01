import asyncio
import os
import sys

# Set up Django/FastAPI environment
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

async def test_mcp():
    from app.tools.mcp.client import MCPClientManager
    import uuid
    org_id = uuid.uuid4()
    mgr = MCPClientManager('http://localhost:8000/api/v1/mcp/', org_id)
    try:
        print("Connecting to MCP...")
        await mgr.connect()
        print("Connected!")
        await mgr.close()
    except BaseException as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp())
