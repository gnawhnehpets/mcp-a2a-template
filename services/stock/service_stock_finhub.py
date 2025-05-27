from datetime import datetime, timezone
import json
import os
from typing import Dict, Any

import finnhub

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

# https://github.com/Finnhub-Stock-API/finnhub-python
class StockServiceFinnhub:
    def __init__(self):
        """ init finnhub service """
        self.client = finnhub.Client(api_key=os.getenv("API_KEY_FINNHUB"))

    def symbol_lookup(self, query: str) -> Dict[str,Any]:
        """
        Get the symbol of a stock from a query; useful if symbol is not known.
        :param query: name of company
        :return: response dict contains description, displaySymbol, symbol, type
        """
        return self.client.symbol_lookup(query=query)

    def get_symbol_quote(self, symbol: str) -> Dict[str,Any]:
        """
        Get live stock price via finnhub API.
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
    service = StockServiceFinnhub()
    print(json.dumps(service.symbol_lookup("mongodb"), indent=2))
    print(json.dumps(service.get_symbol_quote("QQQM"), indent=2, default=str))