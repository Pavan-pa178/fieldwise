from __future__ import annotations
import asyncio
import os
from typing import Any


class MCPClient:
    def __init__(self):
        self._mode = "subprocess"
        try:
            import mcp  # noqa: F401
        except ImportError:
            self._mode = "inprocess"

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if self._mode == "inprocess":
            return self._call_inprocess(tool_name, arguments)
        try:
            return asyncio.run(self._call_subprocess(tool_name, arguments))
        except Exception:
            return self._call_inprocess(tool_name, arguments)

    @staticmethod
    def _call_inprocess(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        from mcp_server import market_server
        tool_fn = getattr(market_server, tool_name)
        return tool_fn(**arguments)

    @staticmethod
    async def _call_subprocess(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        server_script = os.path.join(os.path.dirname(__file__), "market_server.py")
        server_params = StdioServerParameters(
            command="python",
            args=[server_script],
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)
                
                if hasattr(result, "structuredContent") and result.structuredContent:
                    return result.structuredContent
                
                import json
                text = result.content[0].text
                return json.loads(text)
