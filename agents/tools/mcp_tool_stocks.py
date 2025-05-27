import os
from google.adk.tools.mcp_tool import MCPToolset
from google.adk.tools.mcp_tool.mcp_toolset import SseServerParams
from mcp import StdioServerParameters
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

os.environ["GOOGLE_API_KEY"] = os.getenv("API_KEY_GOOGLE")

from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[2]
MCP_SERVER_DIR = ROOT_DIR / "mcp_server" / "shttp"
SEARCH_SCRIPT = MCP_SERVER_DIR / "mcp_shttp_lookup_stock.py"
VENV_PYTHON = ROOT_DIR / ".venv" / "bin" / "python3"

print(f">> ROOT_DIR: {ROOT_DIR}")
print(f">> MCP_SERVER_DIR: {MCP_SERVER_DIR}")
print(f">> SEARCH_SCRIPT: {SEARCH_SCRIPT}")


async def return_mcp_tools_stocks():
    print(">> Connecting to MCP server (stock_stdio)...")
    tools, stack = await MCPToolset.from_server(
        connection_params=StdioServerParameters(
            command=str(VENV_PYTHON),
            args=[str(SEARCH_SCRIPT)],
            env={
                "MCP_PORT":"8001",
                "PYTHONPATH": "/Users/tsadoq/gits/a2a-mcp-tutorial:${PYTHONPATH}"
            }
        )
    )
    print(">> MCPToolset created successfully.")
    return tools, stack


async def return_sse_mcp_tools_stocks():
    print(">> Connecting to MCP server (stock_sse)...")
    server_params = SseServerParams(url="http://localhost:8181/sse")
    tools, stack = await MCPToolset.from_server(connection_params=server_params)
    print(">> MCPToolset created successfully.")
    return tools, stack