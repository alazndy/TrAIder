"""
Proteus Neo Strategy
Proactive, Market-Aware AI Strategy.
Uses Global Market Context (BTC Trend, VIX, DXY) to make decisions.
"""

from .adaptive_ai_enhanced import ProteusAI
from typing import Dict, Any
import pandas as pd
import ta_compat as ta
import numpy as np

class ProteusNeo(ProteusAI):
    """
    Proteus Neo - The "Market Aware" Strategy
    
    Inherits from ProteusAI (which inherits from AdaptiveAI).
    Adds Global Market Context features:
    - BTC Trend (The King's Direction)
    - Asset vs BTC Correlation (Decoupling?)
    - Beta (Sensitivity to Market)
    - Volume Flow (Is money entering the system?)
    """
    
    def __init__(self, parameters: Dict[str, Any]):
        super().__init__(parameters)
        self.name = "Proteus Neo"
        self.model_dir = parameters.get("model_dir", "data/proteus_neo")

    def _create_features(self, df: pd.DataFrame, mode: str) -> pd.DataFrame:
        # Get standard + macro features (DXY, VIX, ETH/BTC)
        features = super()._create_features(df, mode)
        
        # Add NEO Features (Proactive Market Analysis)
        if 'market_btc_close' in df.columns:
            # 1. BTC Trend (Market Pulse)
            features['btc_rsi'] = ta.rsi(df['market_btc_close'], length=14)
            features['btc_roc'] = ta.roc(df['market_btc_close'], length=10)
            
            # 2. Relative Strength (Asset vs BTC)
            # If Asset is rising but BTC is flat => Strong Decoupling (Good)
            # If Asset is falling and BTC is rising => Weakness (Bad)
            features['rel_strength'] = df['close'] / df['market_btc_close']
            features['rel_rsi'] = ta.rsi(features['rel_strength'], length=14)
            
            # 3. Correlation (Rolling 30 days)
            # High Correlation + BTC Drop = DANGER (Sell)
            # Low Correlation + Asset Bullish = IDIOSYNCRATIC PUMP (Buy)
            features['btc_corr'] = df['close'].rolling(30).corr(df['market_btc_close'])
            
            # 4. Volume Divergence (Asset Vol vs Market Vol)
            features['vol_ratio'] = df['volume'] / df['market_btc_vol']
            
        # Cleanup
        features = features.replace([np.inf, -np.inf], np.nan).dropna()
        
        return features

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Override analyze to add 'Proactive Override'
        If Market is CRASHING (BTC < SMA50 & VIX > 30), force SELL/WAIT.
        """
        # 1. Proactive Safety Check (Circuit Breaker)
        if 'market_btc_close' in df.columns and 'vix_close' in df.columns:
            current_btc = df['market_btc_close'].iloc[-1]
            btc_sma50 = df['market_btc_close'].rolling(50).mean().iloc[-1]
            current_vix = df['vix_close'].iloc[-1]
            
            # Crash Detected? (BTC lost trend AND Fear is high)
            if current_btc < btc_sma50 and current_vix > 35:
                return {
                    "signal": "SELL",
                    "confidence": 100.0,
                    "mode": "CRASH_PROTECTION",
                    "prediction": 0
                }
                
        # 2. Standard AI Analysis
        return super().analyze(df)
