from .base import BaseStrategy
from typing import Dict, Any
import pandas as pd
import ta
import numpy as np

class MACDStrategy(BaseStrategy):
    """
    MACD Crossover Strategy
    Logic: MACD line crosses above Signal line -> BUY
           MACD line crosses below Signal line -> SELL
    """
    def __init__(self, parameters: Dict[str, Any]):
        super().__init__(parameters)
        self.name = "MACD Crossover"
        self.fast = int(parameters.get("fast", 12))
        self.slow = int(parameters.get("slow", 26))
        self.signal_period = int(parameters.get("signal", 9))

    def analyze(self, candles: pd.DataFrame) -> Dict[str, Any]:
        if len(candles) < self.slow + self.signal_period + 5:
            return {"signal": "NEUTRAL", "reason": "Not enough data"}

        macd = ta.macd(candles["close"], fast=self.fast, slow=self.slow, signal=self.signal_period)
        
        if macd is None or macd.empty:
            return {"signal": "NEUTRAL", "reason": "MACD calculation failed"}
        
        # Get column names dynamically
        cols = macd.columns.tolist()
        macd_col = [c for c in cols if 'MACD_' in c and 'MACDs' not in c and 'MACDh' not in c][0]
        signal_col = [c for c in cols if 'MACDs_' in c][0]
        
        current_macd = macd[macd_col].iloc[-1]
        prev_macd = macd[macd_col].iloc[-2]
        current_signal = macd[signal_col].iloc[-1]
        prev_signal = macd[signal_col].iloc[-2]

        signal = "NEUTRAL"
        reason = f"MACD: {current_macd:.4f}, Signal: {current_signal:.4f}"

        # Bullish Crossover: MACD crosses above Signal
        if prev_macd <= prev_signal and current_macd > current_signal:
            signal = "BUY"
            reason = f"Bullish MACD Crossover! MACD({current_macd:.4f}) > Signal({current_signal:.4f})"
        
        # Bearish Crossover: MACD crosses below Signal
        elif prev_macd >= prev_signal and current_macd < current_signal:
            signal = "SELL"
            reason = f"Bearish MACD Crossover! MACD({current_macd:.4f}) < Signal({current_signal:.4f})"

        return {
            "signal": signal,
            "macd": round(current_macd, 4),
            "signal_line": round(current_signal, 4),
            "reason": reason
        }
