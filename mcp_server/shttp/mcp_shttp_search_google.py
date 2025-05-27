import uvicorn
from mcp.server import Server
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Route, Mount

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

def create_starlette(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """
    Create startlette app to serve the MCP server with SSE
    :param mcp_server: mcp server to serve
    :param debug: enable debug mode
    :return: app
    """
    shttp = SseServerTransport("/messages/")

    async def handle_shttp(request: Request) -> None:
        async with shttp.connect_sse(request.scope, request.receive, request._send) \
        as (read_stream, write_stream):
            await mcp_server.run(read_stream, write_stream, mcp_server.create_initialization_options() )

    return Starlette(
        debug=debug,
        routes=[Route("/sse", endpoint=handle_shttp), Mount("/messages/", app=shttp.handle_post_message)])


if __name__ == "__main__":
    mcp_server = mcp._mcp_server

    import argparse

    parser = argparse.ArgumentParser(description='Run MCP-SSE server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    args = parser.parse_args()

    starlette_app = create_starlette(mcp_server, debug=True)
    
    print(f">> Starting Google Search MCP-SSE server on {args.host}:{args.port}")
    uvicorn.run(starlette_app, host=args.host, port=args.port)
