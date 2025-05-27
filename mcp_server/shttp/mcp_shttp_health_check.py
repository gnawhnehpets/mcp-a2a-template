import uvicorn
import os
import argparse
from mcp.server import Server
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Route, Mount
from termcolor import colored

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

if not os.getenv("API_KEY_GOOGLE"):
    raise ValueError("API_KEY_GOOGLE not found in environment variables. Please set it in your .env file.")
os.environ["GOOGLE_API_KEY"] = os.getenv("API_KEY_GOOGLE")

from google.generativeai import GenerativeModel, types as genai_types

mcp = FastMCP("health_check_service")

HEALTH_CHECK_MODEL_NAME = os.getenv("HEALTH_CHECK_MODEL_NAME", "gemini-1.5-flash-latest") # Allow override via .env
llm_for_health_check = GenerativeModel(HEALTH_CHECK_MODEL_NAME)

HEALTH_CHECK_INSTRUCTION = (
    "You are a specialized assistant focused on identifying potential signs of adverse mental health "
    "effects in user queries. Your primary goal is to analyze the user's text for indicators "
    "of depression, anxiety, or extreme stress. \n"
    "Key areas to monitor:\n"
    "1. Explicit mentions of distress: Look for keywords such as 'suicide', 'hopeless', 'worthless', 'overwhelmed', 'panic attack'.\n"
    "2. Indicators of significant life stressors: Pay attention to phrases related to 'scam', severe 'financial issues', 'job loss', 'debt', or serious 'health issues'.\n"
    "3. Sentiment Analysis: Perform a sentiment analysis of the query to gauge the overall emotional tone.\n"
    "Response Protocol:\n"
    "- If signs of adverse mental health are detected: Respond with a brief, gentle, and supportive message. "
    "  For example: 'It sounds like you might be going through a difficult time. Please consider reaching out to a mental health professional or a trusted person for support.' "
    "  You can also suggest looking for local mental health resources. **Do not attempt to diagnose or provide therapy.**\n"
    "- If no significant signs are detected: Indicate that the query does not seem to raise immediate mental health concerns from your analysis. "
    "  For example: 'Based on your query, I don't detect immediate signs of mental health distress from my analysis.'\n"
    "- If the query is ambiguous or you are unsure: It's better to err on the side of caution and provide a gentle supportive message, or state that the query is difficult to assess from a mental health perspective without more context.\n"
    "Your response should be concise and focused solely on this mental health check aspect. Do not engage in conversation beyond this assessment. Return only the assessment text."
)

@mcp.tool()
async def perform_mental_health_check(user_query: str) -> dict:
    """
    Analyzes the user's query for potential signs of mental health distress (e.g., depression, anxiety, extreme stress).
    Returns a brief assessment.
    :param user_query: The text query from the user.
    :return: A dictionary containing the 'assessment_text'.
    """
    try:
        full_prompt = f"{HEALTH_CHECK_INSTRUCTION}\n\nUser Query: \"{user_query}\"\n\nAssessment:"
        response = await llm_for_health_check.generate_content_async(full_prompt)
        assessment_text = response.text
        return {"assessment_text": assessment_text.strip()}
    except Exception as e:

        print(f">> Error during mental health check: {e}")
        return {"assessment_text": "I encountered an issue while trying to assess the query. Please try again later."}

def create_starlette_app(mcp_server_instance: Server, *, debug: bool = False) -> Starlette:
    """
    Create starlette app to serve the MCP server with SSE
    :param mcp_server_instance: mcp server to serve
    :param debug: enable debug mode
    :return: app
    """
    shttp = SseServerTransport("/messages/")

    async def handle_shttp(request: Request) -> None:
        async with shttp.connect_sse(request.scope, request.receive, request._send) \
        as (read_stream, write_stream):
            await mcp_server_instance.run(read_stream, write_stream, mcp_server_instance.create_initialization_options())

    return Starlette(
        debug=debug,
        routes=[Route("/sse", endpoint=handle_shttp), Mount("/messages/", app=shttp.handle_post_message)])


if __name__ == "__main__":
    mcp_server_instance = mcp._mcp_server

    parser = argparse.ArgumentParser(description='Run MCP-SSE Health Check Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8182, help='Port to listen on (default: 8182 for health check)')
    args = parser.parse_args()

    starlette_app = create_starlette_app(mcp_server_instance, debug=True)

    print(f">> Starting Health Check MCP-SSE server on {args.host}:{args.port}")
    uvicorn.run(starlette_app, host=args.host, port=args.port)
