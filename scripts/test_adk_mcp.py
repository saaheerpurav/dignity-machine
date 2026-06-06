from __future__ import annotations

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams


ROOT = Path(__file__).resolve().parents[1]


async def main() -> int:
    load_dotenv(ROOT / ".env")
    kibana_url = os.environ["KIBANA_URL"].rstrip("/")
    api_key = os.environ["ELASTIC_API_KEY"]

    toolset = MCPToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=f"{kibana_url}/api/agent_builder/mcp",
            headers={
                "Authorization": f"ApiKey {api_key}",
                "kbn-xsrf": "true",
            },
            timeout=30,
            sse_read_timeout=300,
        ),
        tool_filter=[
            "dignity_search_ssa_policy",
            "dignity_search_ssa_forms",
            "dignity_search_case_documents",
            "dignity_search_case_memory",
            "dignity_get_case_documents",
            "dignity_get_advocate_contact",
        ],
    )

    try:
        tools = await toolset.get_tools()
        print(f"adk_mcp_tool_count={len(tools)}")
        for tool in tools:
            print(tool.name)
    finally:
        await toolset.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
