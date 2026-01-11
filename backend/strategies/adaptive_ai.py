"""
Adaptive AI Trading Strategy - Multi-Mode
Her piyasa durumu icin ayri model egitir:
- BULL (Yukselen Piyasa)
- BEAR (Dusen Piyasa)  
- SIDEWAYS (Yatay Piyasa)
"""

from .base import BaseStrategy
from typing import Dict, Any, List
import pandas as pd
import ta_compat as ta
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
import pickle
import os

class AdaptiveAIStrategy(BaseStrategy):
    """
    Multi-Mode AI Strategy
    
    - Piyasa durumunu tespit eder (Bull/Bear/Sideways)
    - Her mod icin ayri model kullanir
    - Piyasa kosullarina gore strateji degistirir
    """
    
    MODES = ["bull", "bear", "sideways"]
    
    def __init__(self, parameters: Dict[str, Any]):
        super().__init__(parameters)
        self.name = "Adaptive AI (Multi-Mode)"
        
        # Her mod icin ayri model ve scaler
        self.models = {mode: None for mode in self.MODES}
        self.scalers = {mode: StandardScaler() for mode in self.MODES}
        self.is_trained = {mode: False for mode in self.MODES}
        
        self.model_dir = parameters.get("model_dir", "data/adaptive_ai")
        self.min_samples = int(parameters.get("min_samples", 50))
        self.trend_window = int(parameters.get("trend_window", 20))
        
        # Try to load existing models
        self._load_models()
    
    def detect_market_mode(self, df: pd.DataFrame) -> str:
        """Piyasa durumunu tespit et."""
        if len(df) < self.trend_window:
            return "sideways"
        
        # Son N gunluk trend
        closes = df['close'].tail(self.trend_window)
        sma = closes.mean()
        current = closes.iloc[-1]
        first = closes.iloc[0]
        
        # Trend yonu
        trend_pct = (current - first) / first * 100
        
        # Volatilite
        volatility = closes.std() / sma * 100
        
        # Mod belirleme
        if trend_pct > 5 and volatility < 10:
            return "bull"
        elif trend_pct < -5 and volatility < 10:
            return "bear"
        else:
            return "sideways"
    
    def _create_features(self, df: pd.DataFrame, mode: str) -> pd.DataFrame:
        """Moda gore ozellik uret."""
        features = pd.DataFrame(index=df.index)
        
        # Temel ozellikler (tum modlar)
        features['rsi'] = ta.rsi(df['close'], length=14)
        
        sma_fast = ta.sma(df['close'], length=10)
        sma_slow = ta.sma(df['close'], length=30)
        features['sma_ratio'] = sma_fast / sma_slow
        
        features['price_change_1d'] = df['close'].pct_change(1) * 100
        features['price_change_5d'] = df['close'].pct_change(5) * 100
        features['volume_change'] = df['volume'].pct_change(1) * 100
        
        # Moda ozel ozellikler
        if mode == "bull":
            # Bull piyasada momentum onemlier
            features['roc_10'] = ta.roc(df['close'], length=10)
            features['adx'] = ta.adx(df['high'], df['low'], df['close'], length=14)['ADX_14']
            macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
            if macd is not None:
                cols = macd.columns.tolist()
                hist_col = [c for c in cols if 'MACDh' in c]
                if hist_col:
                    features['macd_hist'] = macd[hist_col[0]]
                    
        elif mode == "bear":
            # Bear piyasada volatilite ve destek/direnc onemlier
            features['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            features['atr_pct'] = features['atr'] / df['close'] * 100
            
            # Dip tespiti
            features['distance_from_low'] = (df['close'] - df['low'].rolling(20).min()) / df['close'] * 100
            features['rsi_oversold'] = (features['rsi'] < 30).astype(int)
            
        else:  # sideways
            # Yatay piyasada Bollinger Band ve range trading
            bbands = ta.bbands(df['close'], length=20, std=2)
            if bbands is not None:
                cols = bbands.columns.tolist()
                upper = [c for c in cols if 'BBU' in c][0]
                lower = [c for c in cols if 'BBL' in c][0]
                mid = [c for c in cols if 'BBM' in c][0]
                features['bb_position'] = (df['close'] - bbands[lower]) / (bbands[upper] - bbands[lower])
                features['bb_width'] = (bbands[upper] - bbands[lower]) / bbands[mid]
        
        # Cleanup NaNs and Infinite values (Critical for Scikit-Learn)
        features = features.replace([np.inf, -np.inf], np.nan).dropna()
        return features
    
    def _create_target(self, df: pd.DataFrame) -> pd.Series:
        """Hedef: Yarin fiyat yukselecek mi?"""
        future_return = df['close'].shift(-1) / df['close'] - 1
        return (future_return > 0).astype(int)
    
    def train_mode(self, df: pd.DataFrame, mode: str) -> bool:
        """Belirli bir mod icin model egit."""
        print(f"[AI-{mode.upper()}] Training model...")
        
        features = self._create_features(df, mode)
        target = self._create_target(df)
        
        common_idx = features.index.intersection(target.dropna().index)
        X = features.loc[common_idx].iloc[:-1]
        y = target.loc[common_idx].iloc[:-1]
        
        if len(X) < self.min_samples:
            print(f"[AI-{mode.upper()}] Not enough data ({len(X)} < {self.min_samples})")
            return False
        
        # Scale
        X_scaled = self.scalers[mode].fit_transform(X)
        
        # Model secimi moda gore
        if mode == "bull":
            # Bull'da momentum onemlier - GradientBoosting
            model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            )
        elif mode == "bear":
            # Bear'da konservatif - RandomForest daha fazla ag
            model = RandomForestClassifier(
                n_estimators=150,
                max_depth=8,
                min_samples_split=15,
                random_state=42,
                n_jobs=-1
            )
        else:  # sideways
            # Sideways'de hassas - daha az derinlik
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=5,
                min_samples_split=20,
                random_state=42,
                n_jobs=None
            )
        
        model.fit(X_scaled, y)
        
        accuracy = model.score(X_scaled, y)
        print(f"[AI-{mode.upper()}] Training complete. Accuracy: {accuracy:.2%}")
        
        self.models[mode] = model
        self.is_trained[mode] = True
        
        self._save_model(mode)
        return True
    
    def train_all(self, df: pd.DataFrame):
        """Tum modlari egit - veriyi modlara ayir."""
        print("[AI] Training all modes...")
        
        # Her satir icin mod belirle
        modes_data = {mode: [] for mode in self.MODES}
        
        for i in range(self.trend_window, len(df)):
            window = df.iloc[:i+1]
            mode = self.detect_market_mode(window)
            modes_data[mode].append(df.iloc[i])
        
        # Her mod icin veri olustur ve egit
        for mode in self.MODES:
            if len(modes_data[mode]) > self.min_samples:
                mode_df = pd.DataFrame(modes_data[mode])
                mode_df.index = range(len(mode_df))
                self.train_mode(mode_df, mode)
            else:
                print(f"[AI-{mode.upper()}] Not enough {mode} market data ({len(modes_data[mode])} samples)")
    
    def _save_model(self, mode: str):
        """Model kaydet."""
        os.makedirs(self.model_dir, exist_ok=True)
        path = os.path.join(self.model_dir, f"{mode}_model.pkl")
        with open(path, 'wb') as f:
            pickle.dump({
                'model': self.models[mode],
                'scaler': self.scalers[mode]
            }, f)
        print(f"[AI-{mode.upper()}] Model saved to {path}")
    
    def _load_models(self):
        """Tum modelleri yukle."""
        for mode in self.MODES:
            path = os.path.join(self.model_dir, f"{mode}_model.pkl")
            if os.path.exists(path):
                try:
                    with open(path, 'rb') as f:
                        data = pickle.load(f)
                        self.models[mode] = data['model']
                        self.scalers[mode] = data['scaler']
                        self.is_trained[mode] = True
                        print(f"[AI-{mode.upper()}] Model loaded")
                except Exception as e:
                    print(f"[AI-{mode.upper()}] Failed to load: {e}")
    
    def analyze(self, candles: pd.DataFrame) -> Dict[str, Any]:
        """Piyasa durumuna gore analiz et."""
        
        if len(candles) < 50:
            return {"signal": "NEUTRAL", "reason": "Not enough data", "mode": "unknown"}
        
        # Modu tespit et
        current_mode = self.detect_market_mode(candles)
        
        # Model egitilmemisse egit
        if not self.is_trained[current_mode]:
            success = self.train_mode(candles, current_mode)
            if not success:
                return {"signal": "NEUTRAL", "reason": f"{current_mode} model not trained", "mode": current_mode}
        
        # Ozellik uret
        features = self._create_features(candles, current_mode)
        
        if features.empty:
            return {"signal": "NEUTRAL", "reason": "Feature calculation failed", "mode": current_mode}
        
        # Tahmin
        X = features.iloc[[-1]]
        X_scaled = self.scalers[current_mode].transform(X)
        
        prediction = self.models[current_mode].predict(X_scaled)[0]
        probability = self.models[current_mode].predict_proba(X_scaled)[0]
        confidence = max(probability) * 100
        
        # Moda gore sinyal esigi ayarla
        if current_mode == "bull":
            threshold = 52  # Bull'da daha agresif
        elif current_mode == "bear":
            threshold = 60  # Bear'da daha konservatif
        else:
            threshold = 55  # Sideways'de orta
        
        signal = "NEUTRAL"
        if prediction == 1 and confidence > threshold:
            signal = "BUY"
        elif prediction == 0 and confidence > threshold:
            signal = "SELL"
        
        mode_emoji = {"bull": "UP", "bear": "DOWN", "sideways": "FLAT"}[current_mode]
        reason = f"[{mode_emoji}] {current_mode.upper()} Mode | Prediction: {'UP' if prediction==1 else 'DOWN'} ({confidence:.1f}%)"
        
        return {
            "signal": signal,
            "mode": current_mode,
            "prediction": int(prediction),
            "confidence": round(confidence, 2),
            "reason": reason
        }
