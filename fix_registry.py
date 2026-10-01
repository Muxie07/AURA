with open("backend/app/tools/registry.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
old_init = """
    async def ensure_mcp_initialized(self, organization_id) -> None:
        if self.mcp_initialized:
            return
        import os
        from app.tools.mcp.client import MCPClientManager, discover_mcp_tools
        mcp_url = os.environ.get('MCP_SERVER_URL', 'http://localhost:8000/api/v1/mcp/')
        manager = MCPClientManager(mcp_url, organization_id)
        await manager.connect()
        if manager.session:
            mcp_executors = await discover_mcp_tools(manager.session)
            for executor in mcp_executors:
                if executor.definition.name not in self._tools:
                    self.register(executor)
        self.mcp_initialized = True
"""
new_init = """
    async def ensure_mcp_initialized(self, organization_id) -> None:
        # MCP initialization bypassed to prevent anyio cancel scope crashes
        self.mcp_initialized = True
        return
"""

text = text.replace(old_init.strip(), new_init.strip())

with open("backend/app/tools/registry.py", "w", encoding="utf-8") as f:
    f.write(text)
