import os, json, uuid, logging, httpx
from typing import List, Optional

logger = logging.getLogger("ActionFlow-Tools")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp-server:3000")


class MCPClient:
    def __init__(self, base_url: str = MCP_SERVER_URL):
        self.base_url = base_url
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        return self._http_client

    async def close(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def list_tools(self) -> List[dict]:
        client = await self._get_client()
        response = await client.post("/message", json={
            "jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": str(uuid.uuid4())
        })
        return response.json().get("result", {}).get("tools", [])

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        client = await self._get_client()
        logger.info(f"MCP Call: {tool_name}")
        response = await client.post("/message", json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
            "id": str(uuid.uuid4())
        })
        data = response.json()
        if "error" in data:
            logger.error(f"MCP Error: {data['error']}")
            return {"success": False, "error": data["error"]["message"]}
        content = data.get("result", {}).get("content", [])
        if content and content[0].get("type") == "text":
            try:
                return json.loads(content[0]["text"])
            except json.JSONDecodeError:
                return {"success": True, "text": content[0]["text"]}
        return {"success": False, "error": "Empty response"}


mcp_client = MCPClient()
