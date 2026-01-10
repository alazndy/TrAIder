"""
AI Trading Strategy - Machine Learning Based
Uses technical indicators as features to predict BUY/SELL signals.
"""

from .base import BaseStrategy
from typing import Dict, Any
import pandas as pd
import ta
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import pickle
import os

class AIStrategy(BaseStrategy):
    """
    Machine Learning Trading Strategy
    Uses Random Forest to predict trading signals based on technical indicators.
    
    Features:
    - RSI (14)
    - SMA Fast/Slow Ratio
    - MACD Histogram
    - ATR (Volatility)
    - Price Change %
    - Volume Change %
    
    Target:
    - 1 = Buy (Next day price goes up)
    - 0 = Sell (Next day price goes down)
    """
    
    def __init__(self, parameters: Dict[str, Any]):
        super().__init__(parameters)
        self.name = "AI (Machine Learning)"
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.model_path = parameters.get("model_path", "data/ai_model.pkl")
        self.min_training_samples = int(parameters.get("min_training_samples", 100))
        
        # Try to load existing model
        self._load_model()
    
    def _create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer features from price data."""
        features = pd.DataFrame(index=df.index)
        
        # RSI
        features['rsi'] = ta.rsi(df['close'], length=14)
        
        # SMA Ratio (Fast/Slow)
        sma_fast = ta.sma(df['close'], length=10)
        sma_slow = ta.sma(df['close'], length=30)
        features['sma_ratio'] = sma_fast / sma_slow
        
        # MACD Histogram
        macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
        if macd is not None and not macd.empty:
            hist_col = [c for c in macd.columns if 'MACDh' in c]
            if hist_col:
                features['macd_hist'] = macd[hist_col[0]]
        
        # ATR (Volatility)
        features['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        features['atr_pct'] = features['atr'] / df['close'] * 100
        
        # Price Change (Momentum)
        features['price_change_1d'] = df['close'].pct_change(1) * 100
        features['price_change_5d'] = df['close'].pct_change(5) * 100
        
        # Volume Change
        features['volume_change'] = df['volume'].pct_change(1) * 100
        
        # Bollinger Band Position
        bbands = ta.bbands(df['close'], length=20, std=2)
        if bbands is not None and not bbands.empty:
            cols = bbands.columns.tolist()
            upper = [c for c in cols if 'BBU' in c][0]
            lower = [c for c in cols if 'BBL' in c][0]
            mid = [c for c in cols if 'BBM' in c][0]
            features['bb_position'] = (df['close'] - bbands[lower]) / (bbands[upper] - bbands[lower])
        
        return features.dropna()
    
    def _create_target(self, df: pd.DataFrame, lookahead: int = 1) -> pd.Series:
        """Create target: 1 if price goes up next day, 0 otherwise."""
        future_return = df['close'].shift(-lookahead) / df['close'] - 1
        return (future_return > 0).astype(int)
    
    def train(self, df: pd.DataFrame):
        """Train the ML model on historical data."""
        print(f"[AI] Training on {len(df)} samples...")
        
        # Create features and target
        features = self._create_features(df)
        target = self._create_target(df)
        
        # Align and clean
        common_idx = features.index.intersection(target.dropna().index)
        X = features.loc[common_idx]
        y = target.loc[common_idx]
        
        # Remove last row (no future data for target)
        X = X.iloc[:-1]
        y = y.iloc[:-1]
        
        if len(X) < self.min_training_samples:
            print(f"[AI] Not enough data to train ({len(X)} < {self.min_training_samples})")
            return False
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train Random Forest
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=10,
            random_state=42,
            n_jobs=-1
        )
        self.model.fit(X_scaled, y)
        
        # Calculate training accuracy
        train_acc = self.model.score(X_scaled, y)
        print(f"[AI] Training complete. Accuracy: {train_acc:.2%}")
        
        # Save model
        self._save_model()
        self.is_trained = True
        
        return True
    
    def _save_model(self):
        """Save model to disk."""
        os.makedirs(os.path.dirname(self.model_path) if os.path.dirname(self.model_path) else ".", exist_ok=True)
        with open(self.model_path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'scaler': self.scaler
            }, f)
        print(f"[AI] Model saved to {self.model_path}")
    
    def _load_model(self):
        """Load model from disk if exists."""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    data = pickle.load(f)
                    self.model = data['model']
                    self.scaler = data['scaler']
                    self.is_trained = True
                    print(f"[AI] Model loaded from {self.model_path}")
            except Exception as e:
                print(f"[AI] Failed to load model: {e}")
    
    def analyze(self, candles: pd.DataFrame) -> Dict[str, Any]:
        """Analyze market using trained ML model."""
        
        if len(candles) < 50:
            return {"signal": "NEUTRAL", "reason": "Not enough data"}
        
        # If not trained, train on available data
        if not self.is_trained:
            success = self.train(candles)
            if not success:
                return {"signal": "NEUTRAL", "reason": "Model not trained yet"}
        
        # Create features for latest data
        features = self._create_features(candles)
        
        if features.empty:
            return {"signal": "NEUTRAL", "reason": "Feature calculation failed"}
        
        # Get latest features
        X = features.iloc[[-1]]
        X_scaled = self.scaler.transform(X)
        
        # Predict
        prediction = self.model.predict(X_scaled)[0]
        probability = self.model.predict_proba(X_scaled)[0]
        
        confidence = max(probability) * 100
        
        signal = "NEUTRAL"
        if prediction == 1 and confidence > 55:  # Require >55% confidence
            signal = "BUY"
        elif prediction == 0 and confidence > 55:
            signal = "SELL"
        
        reason = f"AI Prediction: {'UP' if prediction == 1 else 'DOWN'} (Confidence: {confidence:.1f}%)"
        
        # Get feature importances for explainability
        feature_names = features.columns.tolist()
        importances = dict(zip(feature_names, self.model.feature_importances_))
        top_feature = max(importances, key=importances.get)
        
        return {
            "signal": signal,
            "prediction": int(prediction),
            "confidence": round(confidence, 2),
            "top_feature": top_feature,
            "reason": reason
        }
    
    def retrain(self, candles: pd.DataFrame):
        """Force retrain the model."""
        self.is_trained = False
        return self.train(candles)
