import uvicorn
from mcp.server import Server
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Route, Mount

from services.stock.service_stock_finhub import StockServiceFinnhub

mcp = FastMCP("stock search")

finnhub_service = StockServiceFinnhub()

@mcp.tool()
def lookup_symbol(query: str) -> dict:
    """
    Get the symbol of a stock from a query; useful if symbol is not known.
    :param query: name of company
    :return: response dict contains description, displaySymbol, symbol, type
    """
    return finnhub_service.symbol_lookup(query)

@mcp.tool()
def get_stock_price(symbol: str) -> dict:
    """
    Get live stock price via finnhub API.
    :param symbol: stock symbol, e.g. QQQM
    :return: response dict contains current_price, change, percentage_change, day_high, day_low, day_open_price, previous_close_pricem, timestamp, timestamp_bson
    """
    return finnhub_service.get_symbol_quote(symbol)

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
    parser.add_argument('--port', type=int, default=8181, help='Port to listen on')
    args = parser.parse_args()

    starlette_app = create_starlette(mcp_server, debug=True)
    
    print(f">> Starting Stock Lookup MCP-SSE server on {args.host}:{args.port}")
    uvicorn.run(starlette_app, host=args.host, port=args.port)

