import os
import asyncio
from google.adk.tools.mcp_tool import MCPTool
from fastmcp import Client as FastMcpClient
from fastmcp.client.transports import StreamableHttpTransport
from contextlib import AsyncExitStack

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

os.environ["GOOGLE_API_KEY"] = os.getenv("API_KEY_GOOGLE") # This seems unrelated to stocks but is in original

from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[2]


async def return_mcp_tools_stocks(): # This is for STDOUT/STDIN
    print(">> Connecting to MCP server (stock_stdio)...")
    raise NotImplementedError("Stdio MCP tool loading for stocks needs review with fastmcp library.")


async def return_streamed_http_mcp_tools_stocks(): # Renamed function
    stocks_service_url = "http://stock_lookup:8181/mcp" # New endpoint
    print(f">> Connecting to FastMCP server (stocks_streamed_http) at {stocks_service_url}...")
    stack = AsyncExitStack()
    try:
        transport = StreamableHttpTransport(url=stocks_service_url)
        f_client = FastMcpClient(transport)
        await stack.enter_async_context(f_client)

        tool_infos = await f_client.list_tools()

        if tool_infos is None:
            print(">> No tool information received from FastMCP server (stocks_streamed_http).")
            tool_infos = []

        adk_tools = []
        for tool_info in tool_infos:
            adk_tools.append(MCPTool.from_mcp_tool(mcp_tool=tool_info, mcp_client=f_client))
        
        if not adk_tools:
            print(">> Warning: No ADK tools created from FastMCP server (stocks_streamed_http).")

        print(f">> ADK MCPTools (stocks_streamed_http) created successfully: {len(adk_tools)} tools.")
        return adk_tools, stack
    except Exception as e:
        print(f">> Error connecting to or getting tools from FastMCP server (stocks_streamed_http): {e}")
        await stack.aclose()
        raise
