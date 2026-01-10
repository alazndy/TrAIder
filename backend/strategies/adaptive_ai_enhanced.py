
from .adaptive_ai import AdaptiveAIStrategy
import pandas as pd
import pandas_ta as ta
import numpy as np


class ProteusAI(AdaptiveAIStrategy):
    """
    Proteus AI Strategy (formerly Adaptive AI Enhanced)
    
    'Shape-shifting' strategy that adapts to market conditions.
    Inherits from AdaptiveAIStrategy but adds Macro-Economic features:
    - VIX (Volatility Index) -> Fear gauge
    - DXY (Dollar Index) -> Crypto inverse correlation
    - ETH/BTC -> Altseason Indicator
    """
    
    def __init__(self, parameters):
        super().__init__(parameters)
        self.name = "Proteus AI"
        # Use a different model directory to avoid overwriting standard models
        self.model_dir = parameters.get("model_dir", "data/proteus_ai")
        
    def _create_features(self, df: pd.DataFrame, mode: str) -> pd.DataFrame:
        """
        Generates features including Macro Data if available.
        """
        # Get standard features first
        features = super()._create_features(df, mode)
        
        # Add Macro Features if columns exist
        if 'vix_close' in df.columns:
            # VIX High = Fear, VIX Low = Greed
            features['vix_rsi'] = ta.rsi(df['vix_close'], length=14)
            features['vix_trend'] = df['vix_close'].pct_change(5)
            
        if 'dxy_close' in df.columns:
            # DXY Strong = Crypto Weak
            features['dxy_roc'] = ta.roc(df['dxy_close'], length=10)
            features['dxy_rsi'] = ta.rsi(df['dxy_close'], length=14)
            
            # Correlation Check (Rolling correlation between Price and DXY)
            features['dxy_corr'] = df['close'].rolling(20).corr(df['dxy_close'])

        if 'eth_btc_close' in df.columns:
            # ETH/BTC Rising = Altseason (Good for SOL, AVAX)
            # ETH/BTC Falling = Bitcoin Season (Bad for Alts)
            features['alt_season_strength'] = ta.roc(df['eth_btc_close'], length=20)
            features['alt_season_rsi'] = ta.rsi(df['eth_btc_close'], length=14)
            
            # Correlation: Does this asset move with Altseason?
            # SOL should have High positive correlation. BTC might have low/negative.
            features['alt_correlation'] = df['close'].rolling(30).corr(df['eth_btc_close'])
            
        # Cleanup imports again because adding new features might introduce NaNs
        features = features.replace([np.inf, -np.inf], np.nan).dropna()
        
        return features
