from mcp.server.fastmcp import FastMCP
from services.finnhub.service_finhub import FinnHubService

mcp = FastMCP("stock search", "1.0.0", "Search for stocks using the FinHub API")

finnhub_service = FinnHubService()

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
