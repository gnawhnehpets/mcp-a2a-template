import uvicorn
# from mcp.server import Server # Underlying server type, if needed by transport
from fastmcp import FastMCP # Changed
from fastmcp.server.transports import StreamableHttpServerTransport # Hypothetical
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Route

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

def create_starlette(fast_mcp_instance: FastMCP, *, debug: bool = False) -> Starlette: # Changed
    """
    Create starlette app to serve the FastMCP server with Streamable HTTP
    :param fast_mcp_instance: The FastMCP instance
    :param debug: enable debug mode
    :return: app
    """
    mcp_server_to_run = fast_mcp_instance._mcp_server 
    transport = StreamableHttpServerTransport()

    async def stream_mcp_endpoint(request: Request):
        return await transport.handle_request(request, mcp_server_to_run)

    return Starlette(
        debug=debug,
        routes=[
            Route("/mcp", endpoint=stream_mcp_endpoint, methods=["POST"]) # New endpoint
        ]
    )

if __name__ == "__main__":
    fast_mcp_instance = mcp # mcp is the FastMCP instance

    import argparse

    parser = argparse.ArgumentParser(description='Run FastMCP Streamable HTTP server for Stocks') # Updated
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8181, help='Port to listen on')
    args = parser.parse_args()

    starlette_app = create_starlette(fast_mcp_instance, debug=True)
    
    print(f">> Starting Stock Lookup FastMCP Streamable HTTP server on {args.host}:{args.port}") # Updated
    uvicorn.run(starlette_app, host=args.host, port=args.port)
