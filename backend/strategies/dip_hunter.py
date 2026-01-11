from .base import BaseStrategy
from typing import Dict, Any
import pandas as pd
import ta_compat as ta
import numpy as np

class DipHunterStrategy(BaseStrategy):
    """
    MAT-R DipTen Donus (Dip Avcisi)
    Logic: RSI < 30 (Oversold) AND Price > Previous Close (Turning Up) -> BUY
           RSI > 50 -> Quick profit take (SELL)
    """
    def __init__(self, parameters: Dict[str, Any]):
        super().__init__(parameters)
        self.name = "Dip Hunter"
        self.rsi_period = int(parameters.get("rsi_period", 14))
        self.oversold = int(parameters.get("oversold", 30))
        self.take_profit_rsi = int(parameters.get("take_profit_rsi", 50))

    def analyze(self, candles: pd.DataFrame) -> Dict[str, Any]:
        if len(candles) < self.rsi_period + 5:
            return {"signal": "NEUTRAL", "reason": "Not enough data"}

        candles["rsi"] = ta.rsi(candles["close"], length=self.rsi_period)
        
        current_rsi = candles["rsi"].iloc[-1]
        prev_rsi = candles["rsi"].iloc[-2]
        current_price = candles["close"].iloc[-1]
        prev_price = candles["close"].iloc[-2]

        signal = "NEUTRAL"
        reason = f"RSI: {current_rsi:.2f}"

        # Buy Dip: Oversold + Price Turning Up
        if current_rsi < self.oversold and current_price > prev_price:
            signal = "BUY"
            reason = f"DIP DETECTED! RSI({current_rsi:.2f}) + Price Turning Up"
        
        # Quick Take Profit: RSI recovered to 50
        elif current_rsi > self.take_profit_rsi and prev_rsi < self.take_profit_rsi:
            signal = "SELL"
            reason = f"Quick Bounce! RSI crossed above {self.take_profit_rsi}"

        return {
            "signal": signal,
            "rsi": round(current_rsi, 2),
            "reason": reason
        }
