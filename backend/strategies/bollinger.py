from .base import BaseStrategy
from typing import Dict, Any
import pandas as pd
import pandas_ta as ta
import numpy as np

class BollingerBandStrategy(BaseStrategy):
    """
    MGB-4S BANT (Yatay Piyasa Dedektörü)
    Logic: Bollinger Band Squeeze detection and Breakout trading.
    - Squeeze (Low Bandwidth) → NEUTRAL (Stay out of choppy market)
    - Breakout Up (Price > Upper Band) → BUY
    - Breakout Down (Price < Lower Band) → SELL
    """
    def __init__(self, parameters: Dict[str, Any]):
        super().__init__(parameters)
        self.name = "Bollinger Bands"
        self.bb_period = int(parameters.get("bb_period", 20))
        self.bb_std = float(parameters.get("bb_std", 2.0))
        self.squeeze_threshold = float(parameters.get("squeeze_threshold", 0.02))  # 2% bandwidth

    def analyze(self, candles: pd.DataFrame) -> Dict[str, Any]:
        if len(candles) < self.bb_period + 5:
            return {"signal": "NEUTRAL", "reason": "Not enough data"}

        # Calculate Bollinger Bands
        bbands = ta.bbands(candles["close"], length=self.bb_period, std=self.bb_std)
        
        if bbands is None or bbands.empty:
            return {"signal": "NEUTRAL", "reason": "BB calculation failed"}
        
        # Get column names dynamically (pandas_ta column names can vary)
        cols = bbands.columns.tolist()
        lower_col = [c for c in cols if 'BBL' in c][0]
        mid_col = [c for c in cols if 'BBM' in c][0]
        upper_col = [c for c in cols if 'BBU' in c][0]
        
        current_price = candles["close"].iloc[-1]
        upper_band = bbands[upper_col].iloc[-1]
        lower_band = bbands[lower_col].iloc[-1]
        mid_band = bbands[mid_col].iloc[-1]
        
        # Bandwidth calculation
        bandwidth = (upper_band - lower_band) / mid_band

        signal = "NEUTRAL"
        reason = f"Bandwidth: {bandwidth:.4f}"

        # Squeeze Detection
        is_squeeze = bandwidth < self.squeeze_threshold
        
        if is_squeeze:
            signal = "NEUTRAL"
            reason = f"Squeeze Active (BW: {bandwidth:.4f}). Avoid Trading."
        else:
            # Breakout Up
            if current_price > upper_band:
                signal = "BUY"
                reason = f"Breakout UP! Price ${current_price:.2f} > Upper Band ${upper_band:.2f}"
            # Breakout Down
            elif current_price < lower_band:
                signal = "SELL"
                reason = f"Breakout DOWN! Price ${current_price:.2f} < Lower Band ${lower_band:.2f}"

        return {
            "signal": signal,
            "bandwidth": round(bandwidth, 4),
            "upper_band": round(upper_band, 2),
            "lower_band": round(lower_band, 2),
            "reason": reason
        }
