"""
Connector - single point of contact between the GUI and the data layer.
GUI only imports Connector. All Quant and StockApi logic is handled here.

INTERVAL_OPTIONS fields
-----------------------
fetch_interval : candle size sent to the TwelveData API
outputsize     : number of those candles to fetch — sized so the window
                 exactly covers one unit of the display interval
regression     : model type fed to Quant
graph_steps    : future bars to predict (1 = next candle only)
seconds        : calendar seconds per FETCH candle — used for predicted_time
"""

from Quant import Quant
from StockAPI import StockApi

INTERVAL_OPTIONS = {
    # display   fetch_interval  bars   steps  regression    seconds/fetch-bar
    "5min":  {"fetch_interval": "1min",  "outputsize":  15,  "graph_steps": 5, "regression": "linear",     "seconds":    60},
    "15min": {"fetch_interval": "1min",  "outputsize": 30,  "graph_steps": 15, "regression": "polynomial2",     "seconds":    60},
    "30min": {"fetch_interval": "5min",  "outputsize": 18,  "graph_steps": 6, "regression": "polynomial2",     "seconds":    300},
    "1h":    {"fetch_interval": "5min",  "outputsize": 32,  "graph_steps": 12, "regression": "polynomial2",     "seconds":    300},
    "4h":    {"fetch_interval": "15min",  "outputsize": 24,  "graph_steps": 16, "regression": "polynomial", "seconds":   900},
    "1day":  {"fetch_interval": "1h", "outputsize": 72,  "graph_steps": 24, "regression": "polynomial", "seconds":   3600},
    "1week": {"fetch_interval": "1day",    "outputsize": 21, "graph_steps": 7, "regression": "polynomial", "seconds":  86400},
    "1month":{"fetch_interval": "1day",  "outputsize": 90,  "graph_steps": 30, "regression": "polynomial", "seconds": 86400},
}

# Auto-refresh cadence matches the display interval duration
REFRESH_SECONDS = {
    "5min": 300, "15min": 900, "30min": 1800, "1h": 3600,
}


class Connector:
    def __init__(self):
        self.TimeInterval = "5min"
        self._quant      = Quant()
        self._stock_api  = None
        self._last_error = ""

    # ── Setup ─────────────────────────────────────────────────────────────────

    def connect(self, api_key: str) -> bool:
        if not api_key:
            return False
        self._stock_api = StockApi(api_key=api_key)
        return True

    @property
    def is_connected(self) -> bool:
        return self._stock_api is not None

    # ── Interval ──────────────────────────────────────────────────────────────

    def SelectTimeInterval(self, interval: str):
        if interval not in INTERVAL_OPTIONS:
            raise ValueError(f"Unknown interval: {interval}")
        self.TimeInterval = interval

    @property
    def interval_keys(self) -> list:
        return list(INTERVAL_OPTIONS.keys())

    @property
    def regression_type(self) -> str:
        return INTERVAL_OPTIONS[self.TimeInterval]["regression"]

    @property
    def fetch_interval(self) -> str:
        return INTERVAL_OPTIONS[self.TimeInterval]["fetch_interval"]

    @property
    def refresh_seconds(self) -> int:
        return REFRESH_SECONDS.get(self.TimeInterval, 60)

    # ── Data & prediction ─────────────────────────────────────────────────────

    def LoadHistoricalData(self, symbol: str) -> bool:
        cfg  = INTERVAL_OPTIONS[self.TimeInterval]
        data = self._stock_api.makecall(
            symbol=symbol,
            timeFrame=cfg["fetch_interval"],   # fine-grained candle size
            dP=cfg["outputsize"],              # bars that fill the display window
            api=self._stock_api.api,
            startDate=None,
        )
        if data.get("status") == "error":
            self._last_error = data.get("message", "Unknown error")
            return False
        return self._quant.CreateData(data)

    def RunPrediction(self) -> None:
        cfg = INTERVAL_OPTIONS[self.TimeInterval]
        self._quant.PredictPrice(
            regression_type=cfg["regression"],
            future_steps=cfg["graph_steps"],
        )

    def ResetPrediction(self):
        self._quant.reset()

    def search_symbols(self, query: str) -> list:
        if not self._stock_api:
            return []
        results = self._stock_api.search_symbols(query)
        return [
            f"{r.get('symbol',''):<8} {r.get('instrument_name','')[:28]:<28} {r.get('exchange','')}"
            for r in results[:10]
        ]

    # ── Display properties (GUI reads these) ──────────────────────────────────

    @property
    def has_data(self) -> bool:
        return bool(self._quant.prices)

    @property
    def symbol(self) -> str:
        return self._quant.stockName

    @property
    def current_price(self):
        return self._quant.stockprice

    @property
    def current_time(self) -> str:
        t = self._quant.stockTime
        return t.strftime("%Y-%m-%d %H:%M:%S") if t else "—"

    @property
    def predicted_price(self):
        """The predicted price = last point of the prediction line."""
        future = self._quant.predicted_prices[len(self._quant.prices):]
        return round(future[-1], 4) if future else None

    @property
    def predicted_time(self) -> str:
        """Timestamp of the last predicted bar (current + graph_steps × seconds)."""
        from datetime import timedelta
        t = self._quant.stockTime
        if not t:
            return "—"
        cfg     = INTERVAL_OPTIONS[self.TimeInterval]
        seconds = cfg["seconds"] * cfg["graph_steps"]
        return (t + timedelta(seconds=seconds)).strftime("%Y-%m-%d %H:%M:%S")

    @property
    def recommendation(self) -> str:
        return self._quant.Recommendation()

    @property
    def prices(self) -> list:
        return self._quant.prices

    @property
    def timestamps(self) -> list:
        return self._quant.timestamps

    @property
    def predicted_prices(self) -> list:
        return self._quant.predicted_prices

    @property
    def last_error(self) -> str:
        return self._last_error