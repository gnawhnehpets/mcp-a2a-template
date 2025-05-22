import os
from google.adk.tools.mcp_tool import MCPToolset
from google.adk.tools.mcp_tool.mcp_toolset import SseServerParams
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

os.environ["GOOGLE_API_KEY"] = os.getenv("API_KEY_GOOGLE")

from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[2]

HEALTH_CHECK_SERVER_URL = os.getenv("HEALTH_CHECK_MCP_URL", "http://localhost:8182/sse")

async def return_sse_mcp_tools_health_check():
    """
    Connects to the Health Check MCP server (SHTTP/SSE) and returns the toolset.
    The actual server (mcp_shttp_health_check.py) should be run as a separate process.
    """
    print(f">> Connecting to MCP server (health_check_sse) at {HEALTH_CHECK_SERVER_URL}...")
    server_params = SseServerParams(url=HEALTH_CHECK_SERVER_URL)
    
    try:
        tools, stack = await MCPToolset.from_server(connection_params=server_params)
        print(">> Health Check MCPToolset created successfully.")
        return tools, stack
    except Exception as e:
        print(f"Error connecting to Health Check MCP server at {HEALTH_CHECK_SERVER_URL}: {e}")
        print("Please ensure the Health Check MCP server (mcp_shttp_health_check.py) is running on the correct port.")
        # Return empty toolset and a no-op stack to prevent crashes, or re-raise
        from contextlib import AsyncExitStack
        return MCPToolset(tools=[]), AsyncExitStack()

if __name__ == '__main__':
    # Example of how to test this connection (requires the server to be running)
    import asyncio
    async def test_connection():
        print("Attempting to connect to Health Check MCP server for testing...")
        health_tools, health_stack = await return_sse_mcp_tools_health_check()
        if health_tools:
            print(f"Successfully connected. Tools available: {[tool.function_declarations[0].name for tool in health_tools]}")
        else:
            print("Connection attempt finished, but no tools were loaded. Check server status and URL.")
        await health_stack.aclose()
        print("Test connection closed.")

    # To run this test:
    # 1. Ensure mcp_shttp_health_check.py is running (e.g., python mcp_server/shttp/mcp_shttp_health_check.py --port 8182)
    # 2. Run this file: python agents/tools/mcp_tool_health_check.py
    # asyncio.run(test_connection())
    pass
