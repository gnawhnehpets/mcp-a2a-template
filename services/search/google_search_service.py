import json
import os
import requests
from typing import List, Dict, Any

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

class SearchServiceSerper:
    def __init__(self):
        self.__api_key__=os.getenv("API_KEY_SERPER")
        self.url_search = "https://google.serper.dev/search"
        self.url_scraper = "https://scrape.serper.dev"

    def google_search(self, query: str, n_results: int = 10, page: int = 1) -> List[Dict[str, Any]]:
        """
        Google Search via Serper API.
        :param query: search query
        :param n_results: number of results to return per page
        :param page: page number to return
        :return: response dict contains title, link, snippet, date, and other metadata
        """
        payload = json.dumps({"q": query, "num": n_results, "page": page})
        headers = {
            'X-API-KEY': self.__api_key__,
            'Content-Type': 'application/json'
        }

        response = requests.request(
            method="POST",
            url=self.url_search,
            headers=headers,
            data=payload
        )

        return response.json()['organic']


    def scrape_page(self, url: str) -> str:
        """
        Scrape text from a web page via Serper API.
        :param url: page url to scrape
        :return: text content of page
        """
        payload = json.dumps({"url": url })
        headers = {
            'X-API-KEY': self.__api_key__,
            'Content-Type': 'application/json'
        }

        response = requests.request(
            method="POST",
            url=self.url_scraper,
            headers=headers,
            data=payload,
        )

        return response.text

if __name__ == "__main__":
    service = SearchServiceSerper()
    print(json.dumps(service.google_search("caleb williams goat", 3, 1), indent=2))
    print(json.dumps(service.scrape_page("https://bearswire.usatoday.com/story/sports/nfl/bears/2025/05/07/bears-colston-loveland-praises-caleb-williams-nfl-draft/83263414007/"), indent=2))