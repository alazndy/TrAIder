from .base import BaseStrategy
from typing import Dict, Any
import pandas as pd
import ta
import numpy as np

class MeanReversionStrategy(BaseStrategy):
    """
    MAT-R DİPTEN DÖNÜŞ (Dip Avcısı)
    Logic: RSI < 30 (Oversold) + Price turning up → BUY
           RSI > 70 (Overbought) → SELL
    """
    def __init__(self, parameters: Dict[str, Any]):
        super().__init__(parameters)
        self.name = "Mean Reversion (RSI)"
        self.rsi_period = int(parameters.get("rsi_period", 14))
        self.oversold = int(parameters.get("oversold", 30))
        self.overbought = int(parameters.get("overbought", 70))

    def analyze(self, candles: pd.DataFrame) -> Dict[str, Any]:
        if len(candles) < self.rsi_period + 5:
            return {"signal": "NEUTRAL", "reason": "Not enough data"}

        # Calculate RSI
        candles["rsi"] = ta.rsi(candles["close"], length=self.rsi_period)
        
        current_rsi = candles["rsi"].iloc[-1]
        prev_rsi = candles["rsi"].iloc[-2]
        current_price = candles["close"].iloc[-1]
        prev_price = candles["close"].iloc[-2]

        signal = "NEUTRAL"
        reason = f"RSI: {current_rsi:.2f}"

        # Buy Dip: Oversold + Turning Up
        if current_rsi < self.oversold and current_price > prev_price:
            signal = "BUY"
            reason = f"Oversold RSI({current_rsi:.2f}) + Price Turning Up"
        
        # Sell on Overbought
        elif current_rsi > self.overbought:
            signal = "SELL"
            reason = f"Overbought RSI({current_rsi:.2f})"

        return {
            "signal": signal,
            "rsi": round(current_rsi, 2),
            "reason": reason
        }
