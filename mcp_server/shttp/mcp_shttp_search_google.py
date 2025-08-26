import uvicorn
# Server class might come from fastmcp or be compatible if FastMCP uses it internally
# from mcp.server import Server 
from fastmcp import FastMCP # Changed from mcp.server.fastmcp
# Hypothetical new server transport for streamable HTTP mode
from fastmcp.server.transports import StreamableHttpServerTransport # Hypothetical
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Route
# Mount might not be needed for a single endpoint

from services.search.service_search_google import SearchServiceSerper

mcp = FastMCP("google search")

search_service = SearchServiceSerper()

@mcp.tool()
def search_google( query: str, n_results: int = 5, page: int = 1) -> list:
    """
    Google Search via Serper API.
    :param query: search query
    :param n_results: number of results to return per page
    :param page: page number to return
    :return: response dict contains title, link, snippet, date, and other metadata
    """
    return search_service.google_search(query, n_results, page)

@mcp.tool()
def get_page_text(url_to_scrape: str) -> str:
    """
    Scrape text from a web page via Serper API.
    :param url: page url to scrape
    :return: text content of page
    """
    return search_service.scrape_page(url_to_scrape)

def create_starlette(fast_mcp_instance: FastMCP, *, debug: bool = False) -> Starlette: # Changed param name and type
    """
    Create starlette app to serve the FastMCP server in streamable HTTP mode
    :param fast_mcp_instance: The FastMCP instance
    :param debug: enable debug mode
    :return: app
    """
    # The FastMCP instance itself might provide an ASGI app or a way to get one
    # when configured for a specific transport or mode.
    # The documentation snippet mentioned "FastMCP servers running in streamable-http mode".

    # Hypothetical: FastMCP provides a method to get an ASGI app for this mode
    # This is a guess based on how some frameworks work.
    # return fast_mcp_instance.to_asgi_app(transport=StreamableHttpServerTransport(), debug=debug)

    # Alternative: Manually wire up a StreamableHttpServerTransport with the underlying mcp.server.Server
    # This is closer to the previous SseServerTransport pattern.
    
    # Get the underlying mcp.server.Server instance from the FastMCP object
    # (assuming FastMCP still wraps/uses one, or is one)
    # If FastMCP itself is the server object to be used with transports:
    # mcp_server_to_run = fast_mcp_instance # If FastMCP is directly usable as the server core
    # Else, if it still has _mcp_server:
    mcp_server_to_run = fast_mcp_instance._mcp_server # Using the passed FastMCP instance

    transport = StreamableHttpServerTransport() # Assuming it's parameterless or configured elsewhere

    # The transport needs to expose a Starlette-compatible endpoint.
    # This endpoint will handle the bidirectional stream with the mcp_server_to_run.
    # This is the most speculative part without server-side docs for StreamableHttpServerTransport.
    # Let's assume it provides a handler method.
    async def stream_mcp_endpoint(request: Request):
        # The transport's handler would take the request and the server instance,
        # establish streams, and call server.run().
        return await transport.handle_request(request, mcp_server_to_run)

    return Starlette(
        debug=debug,
        routes=[
            Route("/mcp", endpoint=stream_mcp_endpoint, methods=["POST"]) # New endpoint
        ]
    )

if __name__ == "__main__":
    # mcp is the FastMCP instance
    fast_mcp_instance = mcp 
    
    import argparse

    parser = argparse.ArgumentParser(description='Run FastMCP Streamable HTTP server') # Updated
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    args = parser.parse_args()

    # Pass the FastMCP instance itself to create_starlette,
    # it can then get _mcp_server if needed, or use itself if it's the server obj for transport
    starlette_app = create_starlette(fast_mcp_instance, debug=True) 
    
    print(f">> Starting Google Search FastMCP Streamable HTTP server on {args.host}:{args.port}") # Updated
    uvicorn.run(starlette_app, host=args.host, port=args.port)
