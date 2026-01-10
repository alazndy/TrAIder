from .base import BaseStrategy
from typing import Dict, Any
import pandas as pd
import numpy as np

class BreakoutStrategy(BaseStrategy):
    """
    Breakout Strategy
    Logic: Price breaks above N-day high -> BUY (Trend following)
           Price breaks below N-day low -> SELL (Trend breakdown)
    Popular in turtle trading and other trend-following systems.
    """
    def __init__(self, parameters: Dict[str, Any]):
        super().__init__(parameters)
        self.name = "Breakout (N-Day)"
        self.lookback = int(parameters.get("lookback", 20))

    def analyze(self, candles: pd.DataFrame) -> Dict[str, Any]:
        if len(candles) < self.lookback + 5:
            return {"signal": "NEUTRAL", "reason": "Not enough data"}

        current_price = candles["close"].iloc[-1]
        
        # N-day high/low (excluding current day)
        high_n = candles["high"].iloc[-self.lookback-1:-1].max()
        low_n = candles["low"].iloc[-self.lookback-1:-1].min()
        
        signal = "NEUTRAL"
        reason = f"{self.lookback}D High: ${high_n:.2f}, Low: ${low_n:.2f}"

        # Breakout Up
        if current_price > high_n:
            signal = "BUY"
            reason = f"BREAKOUT UP! Price ${current_price:.2f} > {self.lookback}D High ${high_n:.2f}"
        
        # Breakout Down
        elif current_price < low_n:
            signal = "SELL"
            reason = f"BREAKDOWN! Price ${current_price:.2f} < {self.lookback}D Low ${low_n:.2f}"

        return {
            "signal": signal,
            "high_n": round(high_n, 2),
            "low_n": round(low_n, 2),
            "reason": reason
        }
