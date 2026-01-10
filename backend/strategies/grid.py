from .base import BaseStrategy
from typing import Dict, Any
import pandas as pd
import numpy as np

class GridStrategy(BaseStrategy):
    """
    Grid Trading Strategy
    Belirli fiyat aralıklarında otomatik AL/SAT yapar.
    Yatay piyasalarda etkili.
    """
    def __init__(self, parameters: Dict[str, Any]):
        super().__init__(parameters)
        self.name = "Grid Trading"
        self.grid_size = float(parameters.get("grid_size", 0.02))  # 2% grid aralığı
        self.grids = int(parameters.get("grids", 10))
        self.last_grid_level = None
        
    def analyze(self, candles: pd.DataFrame) -> Dict[str, Any]:
        if len(candles) < 20:
            return {"signal": "NEUTRAL", "reason": "Not enough data"}
        
        current_price = candles["close"].iloc[-1]
        prev_price = candles["close"].iloc[-2]
        
        # İlk kurulum: Merkez fiyatı belirle
        if self.last_grid_level is None:
            center = candles["close"].iloc[-20:].mean()  # Son 20 günün ortalaması
            self.last_grid_level = int(current_price / (center * self.grid_size))
        
        # Hangi grid seviyesindeyiz?
        center = candles["close"].iloc[-20:].mean()
        current_grid = int(current_price / (center * self.grid_size))
        
        signal = "NEUTRAL"
        reason = f"Grid Level: {current_grid}"
        
        # Grid seviyesi değişti mi?
        if current_grid < self.last_grid_level:
            # Fiyat düştü -> BUY
            signal = "BUY"
            reason = f"Price dropped to grid level {current_grid}. BUY the dip."
        elif current_grid > self.last_grid_level:
            # Fiyat yükseldi -> SELL
            signal = "SELL"
            reason = f"Price rose to grid level {current_grid}. SELL the rally."
            
        self.last_grid_level = current_grid
        
        return {
            "signal": signal,
            "grid_level": current_grid,
            "reason": reason
        }
