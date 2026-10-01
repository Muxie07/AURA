import re

with open('app/agents/services/agent_service.py', 'r') as f:
    text = f.read()

text = text.replace(
    'self.action_registry = ToolRegistry()\n        register_builtin_tools(self.action_registry)\n\n        self.graph = self._build_graph()',
    'self.action_registry = ToolRegistry()\n        self.graph = self._build_graph()'
)

new_init = '''
    async def initialize(self):
        register_builtin_tools(self.action_registry)
        from app.tools.mcp.client import discover_mcp_tools, MCPClientManager
        import os
        mcp_url = os.environ.get("MCP_SERVER_URL", "http://localhost:8000/api/v1/mcp")
        self.mcp_manager = MCPClientManager(mcp_url)
        try:
            await self.mcp_manager.connect()
            mcp_tools = await discover_mcp_tools(self.mcp_manager.session)
            for tool in mcp_tools:
                self.action_registry.register(tool)
        except Exception as e:
            logger.warning("Failed to connect to MCP Server", error=str(e))
'''

text = text.replace('    def _build_graph(self) -> WorkflowGraph:', new_init + '\n    def _build_graph(self) -> WorkflowGraph:')

new_cleanup = '''
            if hasattr(self, "mcp_manager"):
                await self.mcp_manager.close()
            return state

        except Exception as e:
            if hasattr(self, "mcp_manager"):
                await self.mcp_manager.close()
'''
text = text.replace('            return state\n\n        except Exception as e:', new_cleanup)

with open('app/agents/services/agent_service.py', 'w') as f:
    f.write(text)
