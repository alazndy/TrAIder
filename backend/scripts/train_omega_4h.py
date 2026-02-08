import sys
import os
import glob
import pandas as pd
import numpy as np
import xgboost as xgb
from datetime import datetime

# Add paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.event_calendar import event_engine

DATA_DIR = '../data/omega_4h'
MODEL_DIR = '../data/proteus_omega_4h'

def train_omega_4h():
    print("="*60)
    print("🚀 OMEGA SWING 4H - TRAINING MASTER BRAIN")
    print("="*60)

    csv_files = glob.glob(os.path.join(DATA_DIR, "*_4h.csv"))
    all_X, all_y = [], []
    
    for f in csv_files:
        symbol = os.path.basename(f).replace("_4h.csv", "")
        print(f"[*] Processing {symbol}...")
        df = pd.read_csv(f)
        df['date'] = pd.to_datetime(df['time'], unit='ms')
        df = df.set_index('date').sort_index()
        
        df['rsi'] = (df['close'].diff().apply(lambda x: max(x,0)).rolling(14).mean() / 
                     df['close'].diff().apply(lambda x: abs(x)).rolling(14).mean() * 100).fillna(50)
        df['sma_ratio'] = (df['close'].rolling(10).mean() / df['close'].rolling(30).mean()).fillna(1.0)
        df['volatility'] = df['close'].rolling(20).std() / df['close'].rolling(20).mean() * 100
        
        ev = event_engine.get_event_features(df.index)
        df = pd.concat([df, ev], axis=1)
        
        df['target'] = (df['close'].shift(-12) > df['close']).astype(int)
        
        feats = ['rsi', 'sma_ratio', 'volatility'] + [col for col in df.columns if 'event_' in col]
        df_clean = df.dropna()
        all_X.append(df_clean[feats])
        all_y.append(df_clean['target'])

    X = pd.concat(all_X)
    y = pd.concat(all_y)
    
    print(f"[*] Training OMEGA 4H Model on GPU ({len(X)} samples)...")
    model = xgb.XGBClassifier(tree_method='hist', device='cuda', n_estimators=1500, max_depth=10, learning_rate=0.02)
    model.fit(X, y)
    
    if not os.path.exists(MODEL_DIR): os.makedirs(MODEL_DIR)
    model.save_model(os.path.join(MODEL_DIR, "omega_4h_brain.json"))
    print("✅ OMEGA 4H BRAIN IS LIVE!")

if __name__ == "__main__":
    train_omega_4h()