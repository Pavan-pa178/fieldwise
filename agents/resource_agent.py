from __future__ import annotations
from .base_agent import BaseAgent, AgentResult
from mcp_server.mcp_client import MCPClient


class ResourceAgent(BaseAgent):
    name = "resource_agent"

    def __init__(self, mcp_client: MCPClient | None = None):
        self.mcp = mcp_client or MCPClient()

    def run(self, *, diagnosis: str, category: str, region: str) -> AgentResult:
        if category == "needs_human_expert":
            return AgentResult(
                agent_name=self.name,
                success=False,
                data={},
                confidence=0.0,
                notes=[self._log("Skipped — case requires human expert, no resourcing needed.")],
            )

        tool_result = self.mcp.call_tool(
            "find_local_treatment",
            {"diagnosis": diagnosis, "category": category, "region": region},
        )

        if not tool_result.get("options"):
            return AgentResult(
                agent_name=self.name,
                success=True,
                data={"options": [], "message": "No local suppliers found for this region."},
                confidence=0.4,
                notes=[self._log(f"MCP tool returned no options for region '{region}'.")],
            )

        return AgentResult(
            agent_name=self.name,
            success=True,
            data={"options": tool_result["options"]},
            confidence=0.85,
            notes=[self._log(
                f"Retrieved {len(tool_result['options'])} local treatment option(s) "
                f"via MCP for region '{region}'."
            )],
        )
