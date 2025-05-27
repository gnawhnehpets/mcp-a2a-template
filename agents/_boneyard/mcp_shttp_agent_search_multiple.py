import asyncio
import os

from google.adk import Agent, Runner
from google.adk.artifacts import InMemoryArtifactService
from google.adk.sessions import InMemorySessionService
from google.genai import types

from tools.mcp_tool_stocks import return_sse_mcp_tools_stocks
from tools.mcp_tool_search import return_sse_mcp_tools_search

from termcolor import colored

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[1]

MCP_SERVER_DIR = ROOT_DIR / "mcp" / "stdio"
SEARCH_SCRIPT = MCP_SERVER_DIR / "mcp_stdio_search_google.py"
VENV_PYTHON = ROOT_DIR / ".venv" / "bin" / "python3"
os.environ["GOOGLE_API_KEY"] = os.getenv("API_KEY_GOOGLE")

MODEL='gemini-2.5-pro-exp-03-25'
APP_NAME='enterprise_analysis'
USER_ID='user_stephen'
SESSION_ID='session_stephen'

async def async_main():
    service_session = InMemorySessionService()
    service_artifacts = InMemoryArtifactService()
    
    print(colored(text=">> Creating session...", color='blue'))
    session = session_service.create_session(
        state={},
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
    )

    query = input("Enter your query:\n")
    content = types.Content(role='user', parts=[types.Part(text=query)])

    print(">> Initializing tools from MCP servers...")
    search_tools, search_exit_stack = await return_sse_mcp_tools_search()
    stocks_tools, stocks_exit_stack = await return_sse_mcp_tools_stocks()

    print(">> Initializing agents...")
    agent_analyze_stock = Agent(
        model=MODEL,
        name="agent_stock_analysis",
        instruction="Perform in-depth analysis of stock data and return key financial insights, including the latest market price.",
        description="Specializes in analyzing stock market data and generating financial insights. Retrieves and reports on the most recent stock prices.",
        tools=stocks_tools
    )

    agent_search_google = Agent(
        model=MODEL,
        name="agent_search_google",
        instruction="Conduct web searches using Google and extract relevant information from online sources.",
        description="Handles open-ended queries by performing Google searches and reading content from web pages.",
        tools=search_tools
    )

    # Create the root agent with sub-agents; delegates tasks to the appropriate sub-agent based on user query
    root_agent = Agent(
        name=APP_NAME,
        model=MODEL,
        description="Root assistant: Handles requests about stocks and information of companies.",
        instruction=(
        "You are the primary assistant orchestrating a team of expert agents to fulfill user requests regarding companies and stock performance.\n"
        "Responsibilities:\n"
        "1. Provide comprehensive reports on companies when requested.\n"
        "2. For stock price or market trend insights, delegate to 'agent_stock_analysis'.\n"
        "3. For general or real-time information, delegate to 'agent_search_google'.\n"
        "Carefully interpret the user’s intent, decide whether to handle the request directly or delegate it, and respond accordingly.\n"
        "When uncertain, ask the user for clarification. Only use tools or delegate tasks as defined."
    ),
        sub_agents=[agent_search_google, agent_analyze_stock],
        output_key="last_assistant_response",
    )

    print(">> Create agent pipeline...")
    runner = Runner(
        app_name=APP_NAME,
        agent=root_agent,
        artifact_service=service_artifacts,
        session_service=service_session,
    )

    print(">> Running agent...")
    events_async = runner.run_async(session_id=session.id, user_id=session.user_id, new_message=content)

    async for event in events_async:
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response_text = event.content.parts[0].text
            elif event.actions and event.actions.escalate:
                final_response_text = f">> agent error: {event.error_message or 'No specific message.'}"
            print(colored(text=f"{'*'*50}\n\n{final_response_text}", color='green'))
            break
        else:
            print(event)


    print(">> closing MCP server connection...")
    await stocks_exit_stack.aclose()
    await search_exit_stack.aclose()


if __name__ == '__main__':
    asyncio.run(async_main())
