"""
Quant - stores price data and runs regression predictions.
Linear for 1/5/15min. Polynomial (degree 2) for all longer intervals.
"""

from datetime import datetime
from typing import List, Optional


class Quant:
    def __init__(self):
        self.stockprice:  Optional[float]   = None
        self.stockName:   str               = ""
        self.stockTime:   Optional[datetime]= None
        self._prices:     List[float]       = []
        self._timestamps: List[datetime]    = []
        self._predicted_prices: List[float] = []
        self._model = None

    def CreateData(self, api_response: dict) -> bool:
        """Parse TwelveData response into prices and timestamps."""
        if api_response.get("status") == "error":
            return False
        values = api_response.get("values", [])
        if not values:
            return False

        self.stockName = api_response.get("meta", {}).get("symbol", self.stockName)

        prices, timestamps = [], []
        for row in reversed(values):  # oldest → newest
            try:
                prices.append(float(row["close"]))
                timestamps.append(datetime.fromisoformat(row["datetime"]))
            except (KeyError, ValueError):
                continue

        if not prices:
            return False

        self._prices     = prices
        self._timestamps = timestamps
        self.stockprice  = prices[-1]
        self.stockTime   = timestamps[-1]
        return True

    def PredictPrice(self, regression_type: str = "linear",
                     future_steps: int = 10) -> List[float]:
        """
        Fit model on historical prices and predict future_steps bars ahead.
        Uses degree-2 polynomial to avoid wild extrapolation.
        Returns full list: history fit + future predictions.
        """
        if len(self._prices) < 5:
            return []

        try:
            import numpy as np
            from sklearn.linear_model import LinearRegression
            from sklearn.preprocessing import PolynomialFeatures
            from sklearn.pipeline import make_pipeline
        except ImportError as exc:
            raise RuntimeError("This function requires numpy and sklearn installed") from exc

        X = np.arange(len(self._prices)).reshape(-1, 1)
        y = np.array(self._prices)

        if regression_type == "linear":
            self._model = LinearRegression().fit(X, y)
        elif regression_type == "polynomial2":
            # degree=2 keeps the curve sensible near the data edge
            self._model = make_pipeline(
                PolynomialFeatures(degree=2), LinearRegression()
            ).fit(X, y)
        else:
            # degree=3 for higher-order option
            self._model = make_pipeline(
                PolynomialFeatures(degree=3), LinearRegression()
            ).fit(X, y)

        X_full = np.arange(len(self._prices) + future_steps).reshape(-1, 1)
        self._predicted_prices = self._model.predict(X_full).tolist()
        return self._predicted_prices

    def Recommendation(self) -> str:
        """BUY / SELL / HOLD by comparing current price to predicted price."""
        if not self._predicted_prices or self.stockprice is None:
            return "HOLD"
        future = self._predicted_prices[len(self._prices):]
        if not future:
            return "HOLD"
        predicted_next = future[-1]
        change_pct = (predicted_next - self.stockprice) / (abs(self.stockprice) + 1e-9) * 100
        if change_pct > 0.5:
            return "BUY"
        if change_pct < -0.5:
            return "SELL"
        return "HOLD"

    def DisplayPredicted(self) -> dict:
        if not self._predicted_prices:
            return {"future": []}
        n = len(self._prices)
        return {
            "history_fit": self._predicted_prices[:n],
            "future":      self._predicted_prices[n:],
        }

    @property
    def prices(self) -> List[float]:
        return self._prices

    @property
    def timestamps(self) -> List[datetime]:
        return self._timestamps

    @property
    def predicted_prices(self) -> List[float]:
        return self._predicted_prices