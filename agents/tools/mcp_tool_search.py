import os

from google.adk.tools.mcp_tool import MCPToolset
from google.adk.tools.mcp_tool.mcp_toolset import SseServerParams
from mcp import StdioServerParameters

from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[1]

MCP_SERVER_DIR = ROOT_DIR / "mcp" / "stdio"
SEARCH_SCRIPT = MCP_SERVER_DIR / "mcp_stdio_search_google.py"
VENV_PYTHON = ROOT_DIR / ".venv" / "bin" / "python3"
os.environ["GOOGLE_API_KEY"] = os.getenv("API_KEY_GOOGLE")

print(f">> ROOT_DIR: {ROOT_DIR}")
print(f">> MCP_SERVER_DIR: {MCP_SERVER_DIR}")
print(f">> SEARCH_SCRIPT: {SEARCH_SCRIPT}")

async def return_mcp_tools_search():
    print(">> Attempting to connect to MCP server for search and page read...")
    tools, stack = await MCPToolset.from_server(
        connection_params=StdioServerParameters(
            command=str(VENV_PYTHON),
            args=[str(SEARCH_SCRIPT)],
            env={
                "MCP_PORT":"8000",
                "PYTHONPATH": f"{ROOT_DIR}:${{PYTHONPATH}}"
            }
        )
    )
    print(">> MCP toolset created successfully.")
    return tools, stack


async def return_sse_mcp_tools_search():
    print(">> Attempting to connect to MCP server for search and page read...")
    server_params = SseServerParams(url="http://localhost:8080/sse")
    tools, stack = await MCPToolset.from_server(connection_params=server_params)
    print(">> MCP toolset created successfully.")
    return tools, stack
