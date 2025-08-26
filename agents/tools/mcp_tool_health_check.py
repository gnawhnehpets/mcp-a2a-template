import os
import asyncio
from google.adk.tools.mcp_tool import MCPTool
from fastmcp import Client as FastMcpClient
from fastmcp.client.transports import StreamableHttpTransport
from contextlib import AsyncExitStack

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

os.environ["GOOGLE_API_KEY"] = os.getenv("API_KEY_GOOGLE") # This seems unrelated but is in original

# Default URL for Docker environment, can be overridden by HEALTH_CHECK_MCP_URL env var
# Assuming the new endpoint for streamable http is /mcp
DEFAULT_HEALTH_CHECK_URL = "http://health_check:8182/mcp"
HEALTH_CHECK_SERVER_URL = os.getenv("HEALTH_CHECK_MCP_URL", DEFAULT_HEALTH_CHECK_URL)

async def return_streamed_http_mcp_tools_health_check(): # Renamed function
    """
    Connects to the Health Check FastMCP server (Streamable HTTP) and returns the ADK tools.
    The actual server (mcp_shttp_health_check.py) should be run as a separate process
    and configured for streamable HTTP mode.
    """
    print(f">> Connecting to FastMCP server (health_check_streamed_http) at {HEALTH_CHECK_SERVER_URL}...")
    stack = AsyncExitStack()
    try:
        transport = StreamableHttpTransport(url=HEALTH_CHECK_SERVER_URL)
        f_client = FastMcpClient(transport)
        await stack.enter_async_context(f_client)

        tool_infos = await f_client.list_tools()

        if tool_infos is None:
            print(f">> No tool information received from FastMCP server (health_check_streamed_http) at {HEALTH_CHECK_SERVER_URL}.")
            tool_infos = []
            
        adk_tools = []
        for tool_info in tool_infos:
            adk_tools.append(MCPTool.from_mcp_tool(mcp_tool=tool_info, mcp_client=f_client))
        
        if not adk_tools:
            print(f">> Warning: No ADK tools created from FastMCP server (health_check_streamed_http) at {HEALTH_CHECK_SERVER_URL}.")

        print(f">> ADK MCPTools (health_check_streamed_http) created successfully: {len(adk_tools)} tools.")
        return adk_tools, stack
    except Exception as e:
        print(f">> Error connecting to or getting tools from FastMCP server (health_check_streamed_http) at {HEALTH_CHECK_SERVER_URL}: {e}")
        await stack.aclose()
        raise

if __name__ == '__main__':
    import asyncio
    # Note: The test_connection logic below would need to be updated.
    # HEALTH_CHECK_SERVER_URL would default to the Docker service name and /mcp endpoint.
    # The server mcp_shttp_health_check.py would need to be running in streamable_http mode.
    async def test_connection():
        print(">> Attempting to connect to Health Check FastMCP server for testing...")
        health_tools, health_stack = await return_streamed_http_mcp_tools_health_check()
        if health_tools:
            print(f">> Successfully connected. Tools available: {[tool.function_declarations[0].name for tool in health_tools]}")
        else:
            print(">> Connection attempt finished, but no tools were loaded. Check server status and URL.")
        await health_stack.aclose()
        print(">> Test connection closed.")

    # To run this test:
    # 1. Ensure mcp_shttp_health_check.py is running (e.g., python mcp_server/shttp/mcp_shttp_health_check.py --port 8182)
    # 2. Run this file: python agents/tools/mcp_tool_health_check.py
    # asyncio.run(test_connection())
    pass
