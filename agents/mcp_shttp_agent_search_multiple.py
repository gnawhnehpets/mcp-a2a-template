import asyncio
import os

from google.adk import Agent, Runner
from google.adk.artifacts import InMemoryArtifactService
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.generativeai import GenerativeModel

from tools.mcp_tool_stocks import return_sse_mcp_tools_stocks
from tools.mcp_tool_search import return_sse_mcp_tools_search
from tools.mcp_tool_health_check import return_sse_mcp_tools_health_check

from termcolor import colored

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[1]

MCP_SERVER_DIR = ROOT_DIR / "mcp_server" / "stdio"
SEARCH_SCRIPT = MCP_SERVER_DIR / "mcp_stdio_search_google.py"
VENV_PYTHON = ROOT_DIR / ".venv" / "bin" / "python3"
os.environ["GOOGLE_API_KEY"] = os.getenv("API_KEY_GOOGLE")

MODEL='gemini-2.5-pro-preview-03-25'
APP_NAME='enterprise_assistant'
USER_ID='user_stephen'
SESSION_ID='session_stephen'

async def async_main():
    print(colored(text=">> Initializing ADK agent...", color='blue'))
    session_service = InMemorySessionService()    
    artifact_service = InMemoryArtifactService()
    
    print(colored(text=">> Creating session...", color='blue'))
    session = session_service.create_session(
        state={},
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )

    query = input("Enter your query:\n")
    content = types.Content(role='user', parts=[types.Part(text=query)])

    print(colored(text=">> Initializing tools from MCP servers...", color='blue'))
    search_tools, search_exit_stack = await return_sse_mcp_tools_search()
    stocks_tools, stocks_exit_stack = await return_sse_mcp_tools_stocks()
    health_check_tools, health_check_exit_stack = await return_sse_mcp_tools_health_check()

    print(colored(text=">> Initializing agents...", color='blue'))

    # Create LLM client instances with retry logic
    # GOOGLE_API_KEY is already set in the environment by this script
    from google.adk.models.registry import LLMRegistry
    base_llm = LLMRegistry.new_llm(MODEL)
    from utils.agent_retry import RetryableGeminiLlm
    retryable_llm_client = RetryableGeminiLlm(model=MODEL)

    agent_analyze_stock = Agent(
        model=MODEL, # Use the model name directly
        name="agent_stock_analysis",
        instruction="Perform in-depth analysis of stock data and return key financial insights, including the latest market price.",
        description="Specializes in analyzing stock market data and generating financial insights. Retrieves and reports on the most recent stock prices.",
        tools=stocks_tools
    )

    agent_search_google = Agent(
        model=MODEL, # Use the model name directly
        name="agent_search_google",
        instruction="First, use 'search_google' to find relevant web pages for the user's query. If initial search results are sufficient, summarize them. If more detail is needed, use 'get_page_text' on the most promising URLs (up to 2-3 pages). Consolidate all gathered information into a single, comprehensive answer. Avoid making separate responses for each piece of information. Your goal is to provide a complete answer in one go after gathering and processing all necessary information.",
        description="Handles open-ended queries by performing Google searches, reading content from web pages, and synthesizing the information.",
        tools=search_tools
    )

    # Create the root agent with sub-agents; delegates tasks to the appropriate sub-agent based on user query
    root_agent = Agent(
        name=APP_NAME,
        model=MODEL, # Use the model name directly
        description="Root assistant: Handles requests about stocks, company information, and user well-being by first performing a mental health check.",
        instruction=(
            "You are the primary assistant orchestrating a team of expert agents. Your process for EVERY user query is:\n"
            "1. **Mental Health Check (ALWAYS Perform First):** Use your 'perform_mental_health_check' tool with the original user query to assess for potential mental health concerns. Store this assessment.\n"
            "2. **Address Primary Request:** After the health check, proceed to address the user's main query. This may involve:\n"
            "    a. Providing comprehensive reports on companies directly if the information is straightforward.\n"
            "    b. For stock price or market trend insights, delegate to 'agent_stock_analysis'.\n"
            "    c. For general or real-time information, delegate to 'agent_search_google'.\n"
            "3. **Formulate Final Response:** Consolidate all information. If the 'perform_mental_health_check' tool indicated a concern, its supportive message MUST be included prominently and respectfully at the BEGINNING of your overall response. Then, provide the answer to the user's primary request based on step 2.\n"
            "Carefully interpret the user’s intent for step 2, decide whether to handle it directly or delegate, and respond accordingly.\n"
            "When uncertain about step 2, ask the user for clarification. Only use tools or delegate tasks as defined."
        ),
        tools=health_check_tools.tools,
        sub_agents=[agent_search_google, agent_analyze_stock],
        output_key="last_assistant_response",
    )

    print(colored(text=">> Create agent pipeline...", color='blue'))
    runner = Runner(
        app_name=APP_NAME,
        agent=root_agent,
        artifact_service=artifact_service,
        session_service=session_service
    )

    print(colored(text=">> Running agent...", color='blue'))
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


    print(colored(text=">> Closing MCP server connection...", color='blue'))
    await stocks_exit_stack.aclose()
    await search_exit_stack.aclose()
    await health_check_exit_stack.aclose() # Close health check exit stack


if __name__ == '__main__':
    asyncio.run(async_main())
