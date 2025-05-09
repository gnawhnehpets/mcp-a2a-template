import os
from typing import Dict, Any

import finnhub
from dotenv import load_dotenv, find_dotenv
import json
from datetime import datetime, timezone

load_dotenv(find_dotenv())

# https://github.com/Finnhub-Stock-API/finnhub-python
class FinnHubService:
    def __init__(self):
        """ init finnhub service """
        self.client = finnhub.Client(api_key=os.getenv("API_KEY_FINNHUB"))

    def get_symbol_from_query(self, query: str) -> Dict[str,Any]:
        """
        Get the symbol of a stock from a query. This is useful if you have no idea about the symbol.
        :param query: name of company
        :return: response dict contains description, displaySymbol, symbol, type
        """

        return self.client.symbol_lookup(
            query=query,
        )

    def get_price_of_stock(self, symbol: str) -> Dict[str,Any]:
        """
        Get live price of stock
        :param symbol: stock symbol, e.g. QQQM
        :return: response dict contains current_price, change, percentage_change, day_high, day_low, day_open_price, previous_close_pricem, timestamp, timestamp_bson
        """
        resp = self.client.quote(symbol)
        return {
             'current_price': resp['c'],
             'change': resp['d'],
             'percentage_change': resp['dp'],
             'day_high': resp['h'],
             'day_low': resp['l'],
             'day_open_price': resp['o'],
             'previous_close_price': resp['pc'],
             'timestamp': datetime.fromtimestamp(resp['t'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
             'timestamp_bson': datetime.fromtimestamp(resp['t'], tz=timezone.utc)
         }

if __name__ == "__main__":
    service = FinnHubService()
    print(json.dumps(service.get_symbol_from_query("mongodb"), indent=2))
    print(json.dumps(service.get_price_of_stock("QQQM"), indent=2, default=str))