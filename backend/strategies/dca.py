from .base import BaseStrategy
from typing import Dict, Any
import pandas as pd
import numpy as np

class DCAStrategy(BaseStrategy):
    """
    Dollar Cost Averaging Strategy
    Düzenli aralıklarla satın al, fiyat düştükçe daha çok al.
    Uzun vadeli yatırımcılar için.
    """
    def __init__(self, parameters: Dict[str, Any]):
        super().__init__(parameters)
        self.name = "DCA (Avg Down)"
        self.dip_threshold = float(parameters.get("dip_threshold", -0.05))  # %5 düşüşte extra al
        self.rally_threshold = float(parameters.get("rally_threshold", 0.15))  # %15 yükselişte sat
        
    def analyze(self, candles: pd.DataFrame) -> Dict[str, Any]:
        if len(candles) < 30:
            return {"signal": "NEUTRAL", "reason": "Not enough data"}
        
        current_price = candles["close"].iloc[-1]
        
        # Son 30 günün ortalaması
        avg_30d = candles["close"].iloc[-30:].mean()
        
        # Fiyatın ortalamadan sapması
        deviation = (current_price - avg_30d) / avg_30d
        
        signal = "NEUTRAL"
        reason = f"Price deviation from 30d avg: {deviation*100:.2f}%"
        
        # Dip: Ortalamadan %5+ aşağıda
        if deviation < self.dip_threshold:
            signal = "BUY"
            reason = f"DCA Buy Zone! Price {deviation*100:.2f}% below 30d avg."
        
        # Rally: Ortalamadan %15+ yukarıda
        elif deviation > self.rally_threshold:
            signal = "SELL"
            reason = f"Take Profit! Price {deviation*100:.2f}% above 30d avg."
        
        return {
            "signal": signal,
            "deviation": round(deviation * 100, 2),
            "reason": reason
        }
