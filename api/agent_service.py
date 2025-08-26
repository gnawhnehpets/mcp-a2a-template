import asyncio
import os
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from termcolor import colored

from google.adk import Agent, Runner
from google.adk.artifacts import InMemoryArtifactService
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types
from google.generativeai import GenerativeModel # Keep this, might be used by ADK or tools
from google.adk.models.registry import LLMRegistry


from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv()) # Load .env before other imports that might need env vars

# Assuming these tool initializers are in the `agents.tools` directory relative to project root
# Adjust paths if necessary based on your project structure
# Since this file is in api/, and tools are in agents/tools, we need to adjust Python's import path or use relative imports carefully.
# For simplicity and robustness with Uvicorn, let's assume PYTHONPATH is set or we use a common root package.
# Or, more directly, ensure the tools can be imported.
# Let's try to import them as if 'agents' is a top-level package.
# This might require running uvicorn from the project root.
import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[1] # This should be the project root
sys.path.append(str(ROOT_DIR))

from agents.tools.mcp_tool_stocks import return_streamed_http_mcp_tools_stocks
from agents.tools.mcp_tool_search import return_streamed_http_mcp_tools_search
from agents.tools.mcp_tool_health_check import return_streamed_http_mcp_tools_health_check # Updated name
# from agents.utils.agent_retry import RetryableGeminiLlm # If needed

# --- Configuration ---
MODEL_NAME = os.getenv("MODEL_NAME", 'gemini-1.5-pro-latest') # Default if not in .env
API_KEY_GOOGLE = os.getenv("API_KEY_GOOGLE")
if not API_KEY_GOOGLE:
    raise ValueError("API_KEY_GOOGLE not found in environment variables. Please set it in your .env file.")
os.environ["GOOGLE_API_KEY"] = API_KEY_GOOGLE # ADK might pick this up

APP_NAME = 'enterprise_assistant_api' # Can be different from the script's APP_NAME
# USER_ID and SESSION_ID will be generated per request or managed if stateful

# --- Global ADK and MCP Resources ---
# These will be initialized in the lifespan manager
adk_resources = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(colored(">> API Service: Initializing ADK components and MCP Tools...", "cyan"))
    try:
        adk_resources["session_service"] = InMemorySessionService()
        adk_resources["artifact_service"] = InMemoryArtifactService()

        print(colored(">> API Service: Connecting to MCP SHTTP servers...", "cyan"))
        # Initialize MCP Tools
        search_tools, search_exit_stack = await return_streamed_http_mcp_tools_search()
        stocks_tools, stocks_exit_stack = await return_streamed_http_mcp_tools_stocks()
        health_check_tools, health_exit_stack = await return_streamed_http_mcp_tools_health_check() # Updated call

        adk_resources["search_tools"] = search_tools
        adk_resources["search_exit_stack"] = search_exit_stack
        adk_resources["stocks_tools"] = stocks_tools
        adk_resources["stocks_exit_stack"] = stocks_exit_stack
        adk_resources["health_check_tools"] = health_check_tools
        adk_resources["health_check_exit_stack"] = health_exit_stack # Variable name updated
        print(colored(">> API Service: MCP Tools connected.", "green"))

        # Define Agents (similar to the script)
        # base_llm = LLMRegistry.new_llm(MODEL_NAME) # ADK agents take model name string

        agent_analyze_stock = Agent(
            model=MODEL_NAME,
            name="agent_stock_analysis",
            instruction="Perform in-depth analysis of stock data and return key financial insights, including the latest market price.",
            description="Specializes in analyzing stock market data and generating financial insights. Retrieves and reports on the most recent stock prices.",
            tools=adk_resources["stocks_tools"]
        )

        agent_search_google = Agent(
            model=MODEL_NAME,
            name="agent_search_google",
            instruction="First, use 'search_google' to find relevant web pages for the user's query. If initial search results are sufficient, summarize them. If more detail is needed, use 'get_page_text' on the most promising URLs (up to 2-3 pages). Consolidate all gathered information into a single, comprehensive answer. Avoid making separate responses for each piece of information. Your goal is to provide a complete answer in one go after gathering and processing all necessary information.",
            description="Handles open-ended queries by performing Google searches, reading content from web pages, and synthesizing the information.",
            tools=adk_resources["search_tools"]
        )

        root_agent = Agent(
            name=APP_NAME + "_root", # Differentiate from main app name if needed
            model=MODEL_NAME,
            description="Root assistant: Handles requests about stocks, company information, and user well-being by first performing a mental health check.",
            instruction=(
                "You are the primary assistant orchestrating a team of expert agents. Your process for EVERY user query is:\n"
                "1. **Mental Health Check (ALWAYS Perform First):** Use your 'perform_mental_health_check' tool with the original user query to assess for potential mental health concerns. Store this assessment.\n"
                "2. **Address Primary Request:** After the health check, proceed to address the user's main query. This may involve:\n"
                "    a. Providing comprehensive reports on companies directly if the information is straightforward.\n"
                "    b. For stock price or market trend insights, delegate to 'agent_stock_analysis'.\n"
                "    c. For general or real-time information, delegate to 'agent_search_google'.\n"
                "3. **Formulate Final Response:** Consolidate all information. If the 'perform_mental_health_check' tool indicated a concern, its supportive message MUST be included prominently and respectfully at the BEGINNING of your overall response. Then, provide the answer to the user's primary request based on step 2.\n"
                "Carefully interpret the user's intent for step 2, decide whether to handle it directly or delegate, and respond accordingly.\n"
                "When uncertain about step 2, ask the user for clarification. Only use tools or delegate tasks as defined."
            ),
            tools=adk_resources["health_check_tools"],
            sub_agents=[agent_search_google, agent_analyze_stock],
            output_key="last_assistant_response", # As per original script
        )
        adk_resources["root_agent"] = root_agent
        adk_resources["runner"] = Runner(
            app_name=APP_NAME, # Runner's app_name
            agent=root_agent,
            artifact_service=adk_resources["artifact_service"],
            session_service=adk_resources["session_service"]
        )
        print(colored(">> API Service: ADK Agents and Runner initialized.", "green"))
        yield
    finally:
        print(colored(">> API Service: Shutting down. Closing MCP connections...", "cyan"))
        if "search_exit_stack" in adk_resources:
            await adk_resources["search_exit_stack"].aclose()
            print(colored(">> API Service: Search MCP connection closed.", "magenta"))
        if "stocks_exit_stack" in adk_resources:
            await adk_resources["stocks_exit_stack"].aclose()
            print(colored(">> API Service: Stocks MCP connection closed.", "magenta"))
        if "health_check_exit_stack" in adk_resources:
            await adk_resources["health_check_exit_stack"].aclose()
            print(colored(">> API Service: Health Check MCP connection closed.", "magenta"))
        print(colored(">> API Service: Shutdown complete.", "green"))


app = FastAPI(lifespan=lifespan)

class QueryRequest(BaseModel):
    query: str
    user_id: str = "api_user" # Default or allow client to send
    session_id: str | None = None # Optional: client can manage session ID for stateful interactions

async def event_stream_generator(query_request: QueryRequest):
    """
    Handles the agent interaction and streams events back to the client.
    """
    session_service = adk_resources["session_service"]
    runner = adk_resources["runner"]

    # For stateless: new session per request. If session_id is provided, try to use it (though InMemory won't persist across restarts)
    # For true stateless mimicking the script, always create new session details.
    current_user_id = query_request.user_id
    current_session_id = query_request.session_id or f"session_{os.urandom(8).hex()}" # Generate if not provided

    print(colored(f">> API Service: Creating session for user '{current_user_id}', session '{current_session_id}'", "yellow"))
    session = session_service.create_session(
        state={}, # Fresh state for each call if truly stateless
        app_name=APP_NAME, # Use the runner's app_name
        user_id=current_user_id,
        session_id=current_session_id
    )

    content = genai_types.Content(role='user', parts=[genai_types.Part(text=query_request.query)])
    
    print(colored(f">> API Service: Running agent for query: \"{query_request.query}\"", "yellow"))
    
    api_call_count = 0
    try:
        async for event in runner.run_async(session_id=session.id, user_id=session.user_id, new_message=content):
            event_data = {"type": event.type.name if hasattr(event.type, 'name') else str(event.type)}
            
            # Basic event serialization, can be expanded
            if hasattr(event, 'content') and event.content:
                if event.content.parts:
                    part = event.content.parts[0]
                    if hasattr(part, 'text') and part.text:
                        event_data["text"] = part.text
                    if hasattr(part, 'function_call') and part.function_call:
                        event_data["function_call"] = {"name": part.function_call.name, "args": part.function_call.args}
                event_data["role"] = event.content.role if hasattr(event.content, 'role') else None

            if hasattr(event, 'author') and event.author:
                event_data["author"] = event.author
            
            if event.is_final_response():
                event_data["is_final"] = True
                if event.content and event.content.parts and hasattr(event.content.parts[0], 'text'):
                     event_data["final_response_text"] = event.content.parts[0].text
                elif event.actions and event.actions.escalate:
                    event_data["final_response_text"] = f"Agent error: {event.error_message or 'No specific message.'}"
                    event_data["error"] = True

            # For debugging on server side
            # print(colored(f"Streaming event: {event_data}", "grey"))

            yield f"data: {json.dumps(event_data)}\n\n"
            
            if event.is_final_response():
                print(colored(">> API Service: Final response sent.", "green"))
                break
    except Exception as e:
        print(colored(f">> API Service: Error during agent execution: {e}", "red"))
        error_event = {"type": "ERROR", "message": str(e), "is_final": True, "error": True}
        yield f"data: {json.dumps(error_event)}\n\n"
    finally:
        print(colored(f">> API Service: Event stream finished for session '{current_session_id}'.", "yellow"))


@app.post("/api/v1/agent/invoke")
async def agent_invoke(query_request: QueryRequest, request: Request): # Added request for client disconnect check
    print(colored(f">> API Service: Received query from {request.client.host}: \"{query_request.query}\"", "blue"))
    return StreamingResponse(event_stream_generator(query_request), media_type="text/event-stream")

# To run this app: uvicorn api.agent_service:app --reload --port 8000
if __name__ == "__main__":
    import uvicorn
    print(colored(">> Starting FastAPI Agent Service with Uvicorn on http://localhost:8000", "cyan"))
    # Note: Lifespan events (startup/shutdown) are better handled by Uvicorn when run as a module.
    # Running this __main__ block directly might not trigger lifespan correctly for all Uvicorn versions/setups.
    # Recommended to run with: uvicorn api.agent_service:app --host 0.0.0.0 --port 8000
    uvicorn.run("agent_service:app", host="0.0.0.0", port=8000, reload=True, workers=1)
