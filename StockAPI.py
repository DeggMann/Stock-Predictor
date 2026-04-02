"""
StockApi - wraps TwelveData REST API calls.
"""

import requests
from typing import Optional

TWELVE_DATA_BASE = "https://api.twelvedata.com"


class StockApi:
    def __init__(self, api_key: str):
        self.api = api_key
        self.dataPoints: dict = {}
        self.dP: int = 60

    def makecall(self, symbol: str, timeFrame: str, dP: int,
                 api: str, startDate: Optional[str]) -> dict:
        """Fetch OHLCV time-series from TwelveData."""
        self.dP = dP
        params = {
            "symbol":     symbol.upper(),
            "interval":   timeFrame,
            "outputsize": dP,
            "apikey":     api,
            "format":     "JSON",
        }
        if startDate:
            params["start_date"] = startDate

        try:
            resp = requests.get(f"{TWELVE_DATA_BASE}/time_series", params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            return {"status": "error", "message": str(e), "values": []}

        self.dataPoints = data
        return data

    def get_quote(self, symbol: str) -> dict:
        """Real-time quote for a symbol."""
        try:
            resp = requests.get(
                f"{TWELVE_DATA_BASE}/quote",
                params={"symbol": symbol.upper(), "apikey": self.api},
                timeout=8,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            return {"status": "error", "message": str(e)}

    def search_symbols(self, query: str) -> list:
        """Search for matching symbols / company names."""
        try:
            resp = requests.get(
                f"{TWELVE_DATA_BASE}/symbol_search",
                params={"symbol": query, "apikey": self.api, "outputsize": 20},
                timeout=8,
            )
            resp.raise_for_status()
            return resp.json().get("data", [])
        except requests.RequestException:
            return []