import os
import asyncio
from google.adk.tools.mcp_tool import MCPTool
from fastmcp import Client as FastMcpClient # Renamed to avoid confusion if ADK also has Client
from fastmcp.client.transports import StreamableHttpTransport
# StdioServerParameters would also come from fastmcp if needed for the stdio function
from contextlib import AsyncExitStack
# import asyncio # Duplicate, already imported above

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

os.environ["GOOGLE_API_KEY"] = os.getenv("API_KEY_GOOGLE")

from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[2]
# MCP_SERVER_DIR and other stdio related paths might not be relevant for StreamableHttpTransport


async def return_mcp_tools_search(): # This is for STDOUT/STDIN
    print(">> Connecting to MCP server (search_stdio)...")
    # This function will need a complete refactor if STDIN/STDOUT is still required
    # and if fastmcp provides a StdioClient equivalent.
    raise NotImplementedError("Stdio MCP tool loading needs review with fastmcp library.")


async def return_streamed_http_mcp_tools_search(): # Renamed function
    # Assuming the server will run on a new endpoint, e.g., /mcp
    search_service_url = "http://google_search:8080/mcp" # New endpoint
    print(f">> Connecting to FastMCP server (search_streamed_http) at {search_service_url}...")
    stack = AsyncExitStack()
    try:
        transport = StreamableHttpTransport(url=search_service_url)
        # fastmcp.Client is an async context manager itself
        f_client = FastMcpClient(transport)
        
        # Enter the client's context using the stack
        # The f_client itself is what __aenter__ returns for fastmcp.Client
        await stack.enter_async_context(f_client)

        # list_tools() should be available after client connection
        # The client should be connected here due to stack.enter_async_context(f_client)
        # which calls f_client.__aenter__()
        
        # A small delay might still be prudent if there's any async initialization inside the client
        # after connection is established but before tools are fully populated.
        # However, let's try without it first, assuming connect() populates tools.
        # await asyncio.sleep(0.1) 

        tool_infos = await f_client.list_tools() # Returns list of fastmcp.ToolInfo or similar

        if tool_infos is None: # list_tools might return None on error or if no tools
            print(">> No tool information received from FastMCP server (search_streamed_http).")
            tool_infos = []

        adk_tools = []
        for tool_info in tool_infos:
            # MCPTool.from_mcp_tool expects an mcp_sdk.Tool and an mcp_sdk.Client.
            # We need to ensure tool_info is compatible with mcp_sdk.Tool,
            # and f_client is compatible with mcp_sdk.Client for this ADK wrapper.
            # Assuming fastmcp.Tool (which tool_info should represent) and fastmcp.Client are compatible.
            adk_tools.append(MCPTool.from_mcp_tool(mcp_tool=tool_info, mcp_client=f_client))
        
        if not adk_tools:
            print(">> Warning: No ADK tools created from FastMCP server (search_streamed_http).")

        print(f">> ADK MCPTools (search_streamed_http) created successfully: {len(adk_tools)} tools.")
        return adk_tools, stack
    except Exception as e:
        print(f">> Error connecting to or getting tools from FastMCP server (search_streamed_http): {e}")
        await stack.aclose() # Ensure stack is closed on error
        raise
