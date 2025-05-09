from mcp.server.fastmcp import FastMCP
from services.search.service_search_google import SearchServiceSerper

mcp = FastMCP("google search") #, "1.0.0", "Search for google using the Serper API")

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

if __name__ == "__main__":
    mcp.run(transport='stdio')
