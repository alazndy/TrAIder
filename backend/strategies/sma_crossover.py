from .base import BaseStrategy
from typing import Dict, Any
import pandas as pd
import ta

class SMACrossoverStrategy(BaseStrategy):
    def __init__(self, parameters: Dict[str, Any]):
        super().__init__(parameters)
        self.name = "SMA Crossover"
        self.fast_period = int(parameters.get("fast_period", 10))
        self.slow_period = int(parameters.get("slow_period", 20))

    def analyze(self, candles: pd.DataFrame) -> Dict[str, Any]:
        # Ensure enough data
        if len(candles) < self.slow_period:
            return {"signal": "NEUTRAL", "reason": "Not enough data"}

        # Calculate Indicators
        candles["fast_sma"] = ta.sma(candles["close"], length=self.fast_period)
        candles["slow_sma"] = ta.sma(candles["close"], length=self.slow_period)

        # Get latest values
        current_fast = candles["fast_sma"].iloc[-1]
        current_slow = candles["slow_sma"].iloc[-1]
        prev_fast = candles["fast_sma"].iloc[-2]
        prev_slow = candles["slow_sma"].iloc[-2]

        signal = "NEUTRAL"
        reason = f"Fast({current_fast:.2f}) vs Slow({current_slow:.2f})"

        # Golden Cross (Fast crosses above Slow)
        if prev_fast <= prev_slow and current_fast > current_slow:
            signal = "BUY"
            reason = "Golden Cross (SMA Fast > Slow)"
        
        # Death Cross (Fast crosses below Slow)
        elif prev_fast >= prev_slow and current_fast < current_slow:
            signal = "SELL"
            reason = "Death Cross (SMA Fast < Slow)"

        return {
            "signal": signal,
            "fast_sma": current_fast,
            "slow_sma": current_slow,
            "reason": reason
        }
