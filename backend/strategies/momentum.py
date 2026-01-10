from .base import BaseStrategy
from typing import Dict, Any
import pandas as pd
import numpy as np

class MomentumStrategy(BaseStrategy):
    """
    RUA MOMENTUM (Rate of Change)
    Logic: ROC > threshold → BUY (Strong upward momentum)
           ROC < 0 → SELL (Momentum lost)
    """
    def __init__(self, parameters: Dict[str, Any]):
        super().__init__(parameters)
        self.name = "Momentum (ROC)"
        self.roc_period = int(parameters.get("roc_period", 5))
        self.threshold = float(parameters.get("threshold", 2.0))  # 2% momentum

    def analyze(self, candles: pd.DataFrame) -> Dict[str, Any]:
        if len(candles) < self.roc_period + 5:
            return {"signal": "NEUTRAL", "reason": "Not enough data"}

        current_price = candles["close"].iloc[-1]
        prev_price = candles["close"].iloc[-self.roc_period - 1]
        
        # Rate of Change (ROC) calculation
        roc = ((current_price - prev_price) / prev_price) * 100

        signal = "NEUTRAL"
        reason = f"ROC({self.roc_period}): {roc:.2f}%"

        # Strong Momentum Up
        if roc > self.threshold:
            signal = "BUY"
            reason = f"Strong Momentum: ROC {roc:.2f}% > {self.threshold}%"
        
        # Momentum Lost
        elif roc < 0:
            signal = "SELL"
            reason = f"Momentum Lost: ROC {roc:.2f}%"

        return {
            "signal": signal,
            "roc": round(roc, 2),
            "reason": reason
        }
