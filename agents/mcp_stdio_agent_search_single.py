import asyncio
import os

from google.adk import Runner
from google.genai import types
from google.adk.agents import LlmAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool import MCPToolset
from mcp import StdioServerParameters

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[1]

MCP_SERVER_DIR = ROOT_DIR / "mcp" / "stdio"
SEARCH_SCRIPT = MCP_SERVER_DIR / "mcp_stdio_search_google.py"
VENV_PYTHON = ROOT_DIR / ".venv" / "bin" / "python3"
os.environ["GOOGLE_API_KEY"] = os.getenv("API_KEY_GOOGLE")

print(f">> ROOT_DIR: {ROOT_DIR}")
print(f">> MCP_SERVER_DIR: {MCP_SERVER_DIR}")
print(f">> SEARCH_SCRIPT: {SEARCH_SCRIPT}")

async def get_tools_async():
    """Gets tools from Search MCP server"""
    print(">> Connecting to MCP server...")

    tools, stack = await MCPToolset.from_server(
        connection_params=StdioServerParameters(
            command=str(VENV_PYTHON),
            args=[str(SEARCH_SCRIPT)],
            env={
                "PYTHONPATH": f"{ROOT_DIR}:${{PYTHONPATH}}"
            },
        )
    )
    print(">> Toolset created successfully.")
    print(f">> Tools: {tools}")
    print(f">> Stack: {stack}")
    return tools, stack

async def get_agent_async():
    """Creates an ADK Agent equipped with tools from MCP server"""
    tools, exit_stack = await get_tools_async()
    print(f">> Equipping agent with {len(tools)} tools from MCP")
    agent = LlmAgent(
        model='gemini-2.5-pro-exp-03-25',
        name='search_agent',
        description="agent with google search capabilities",
        instruction="You are an expert researcher. You always respond to requests with facts that have been verified through an online search.",
        tools=tools
    )
    print(">> Agent created successfully.")
    print(f">> agent: {agent}")
    print(f">> agent.tools: {agent.tools}")
    return agent, exit_stack


async def async_main():
    session_service = InMemorySessionService()
    artifacts_service = InMemoryArtifactService()
    print(">> Creating session...")
    session = session_service.create_session(
        state={}, 
        app_name='mcp_search_app', 
        user_id='user123', 
        session_id='user123-session',
    )
    print(f">> session.id: {session.id}")

    query = "What are some upcoming events in 27502?"
    print(f">> query: '{query}'")

    content = types.Content(role='user', parts=[types.Part(text=query)])
    agent, stack = await get_agent_async()

    runner = Runner(
        app_name='mcp_search_app',
        agent=agent,
        artifact_service=artifacts_service,
        session_service=session_service,
    )

    print(">> Running agent...")
    events_async = runner.run_async(
        session_id=session.id, 
        user_id=session.user_id, 
        new_message=content
    )

    async for event in events_async:
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response_text = event.content.parts[0].text
            elif event.actions and event.actions.escalate:  # Handle potential errors/escalations
                final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
            print(f"{'*'*50}\n{final_response_text}")
            break

    print(">> Closing MCP server connection...")
    await stack.aclose()

if __name__ == '__main__':
    asyncio.run(async_main())
