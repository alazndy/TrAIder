from .base import BaseStrategy
from typing import Dict, Any
import pandas as pd
import numpy as np

class SuperTrendStrategy(BaseStrategy):
    """
    BUM Trend Algorithm (SuperTrend Benzeri)
    EMA crossover ile trend yönünü belirler.
    EMA10 > EMA30 -> Bullish (BUY)
    EMA10 < EMA30 -> Bearish (SELL)
    """
    def __init__(self, parameters: Dict[str, Any]):
        super().__init__(parameters)
        self.name = "SuperTrend (EMA)"
        self.fast_ema = int(parameters.get("fast_ema", 10))
        self.slow_ema = int(parameters.get("slow_ema", 30))
        self.buffer_pct = float(parameters.get("buffer_pct", 0.01))  # 1% buffer
        
    def analyze(self, candles: pd.DataFrame) -> Dict[str, Any]:
        if len(candles) < self.slow_ema + 5:
            return {"signal": "NEUTRAL", "reason": "Not enough data"}
        
        closes = candles["close"]
        
        # EMA hesapla
        ema_fast = closes.ewm(span=self.fast_ema, adjust=False).mean().iloc[-1]
        ema_slow = closes.ewm(span=self.slow_ema, adjust=False).mean().iloc[-1]
        
        current_price = closes.iloc[-1]
        
        diff_pct = (ema_fast - ema_slow) / ema_slow
        
        signal = "NEUTRAL"
        reason = f"EMA{self.fast_ema}: {ema_fast:.2f}, EMA{self.slow_ema}: {ema_slow:.2f}"
        
        # Bullish: Fast > Slow + buffer
        if diff_pct > self.buffer_pct:
            signal = "BUY"
            reason = f"Bullish Trend! EMA{self.fast_ema} > EMA{self.slow_ema} by {diff_pct*100:.2f}%"
        
        # Bearish: Fast < Slow
        elif diff_pct < 0:
            signal = "SELL"
            reason = f"Bearish Trend! EMA{self.fast_ema} < EMA{self.slow_ema}"
        
        return {
            "signal": signal,
            "ema_fast": round(ema_fast, 2),
            "ema_slow": round(ema_slow, 2),
            "diff_pct": round(diff_pct * 100, 2),
            "reason": reason
        }
