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

DATA_DIR = '../data/omega'
MODEL_DIR = '../data/proteus_omega'

def train_omega_prime():
    print("="*60)
    print("🚀 OMEGA PRIME MASTER BRAIN - 13 DIMENSIONAL TRAINING")
    print("="*60)

    # 1. Align and Merge Everything (Price + MTF + Events + On-Chain)
    btc_1h = pd.read_csv(os.path.join(DATA_DIR, 'BTC_USDT_1h.csv'))
    btc_1h['date'] = pd.to_datetime(btc_1h['time'], unit='ms')
    df = btc_1h.set_index('date').sort_index()
    
    # On-Chain Proxy
    df['whale_activity'] = (df['volume'] > df['volume'].rolling(24).mean() * 3).astype(int)
    df['net_flow_proxy'] = (df['close'] - df['open']) * df['whale_activity']
    
    # MTF Features
    btc_1d = pd.read_csv(os.path.join(DATA_DIR, 'BTC_USDT_1d.csv'))
    btc_1d['date'] = pd.to_datetime(btc_1d['time'], unit='ms')
    btc_1d = btc_1d.set_index('date').sort_index()
    df['macro_trend'] = btc_1d['close'].reindex(df.index, method='ffill')
    df['micro_vol'] = df['close'].rolling(4).std()
    
    # Events
    events = event_engine.get_event_features(df.index)
    df = pd.concat([df, events], axis=1)
    
    # Target
    df['target'] = (df['close'].shift(-24) > df['close']).astype(int)
    
    # Features
    df['rsi'] = (df['close'].diff().apply(lambda x: max(x,0)).rolling(14).mean() / 
                 df['close'].diff().apply(lambda x: abs(x)).rolling(14).mean() * 100).fillna(50)
    
    # 13 Dimensions: RSI, micro_vol, macro_trend, whale_activity, net_flow_proxy + 8 Events
    features = ['rsi', 'micro_vol', 'macro_trend', 'whale_activity', 'net_flow_proxy'] + [col for col in df.columns if 'event_' in col]
    
    df_clean = df.dropna()
    X = df_clean[features]
    y = df_clean['target']
    
    print(f"[*] Dataset Ready: {len(df_clean)} samples with {len(features)} features.")
    print("[*] Training OMEGA PRIME Model on GPU...")
    
    model = xgb.XGBClassifier(
        tree_method='hist',
        device='cuda',
        n_estimators=2500,
        max_depth=14,
        learning_rate=0.01,
        subsample=0.85
    )
    
    model.fit(X, y)
    
    if not os.path.exists(MODEL_DIR): os.makedirs(MODEL_DIR)
    model.save_model(os.path.join(MODEL_DIR, "omega_brain.json"))
    
    print("✅ OMEGA PRIME MASTER BRAIN UPDATED!")

if __name__ == "__main__":
    train_omega_prime()