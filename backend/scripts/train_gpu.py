
import sys
import os
import glob
import pandas as pd
import numpy as np
import xgboost as xgb

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strategies.proteus_neo import ProteusNeo

DATA_DIR = '../data/raw'
MODEL_DIR = '../data/proteus_neo' 

def train_gpu():
    print("="*60)
    print("🚀 PROTEUS NEO - MASTER BRAIN GPU TRAINING (DEBUG MODE)")
    print("="*60)

    strategy = ProteusNeo({"model_dir": MODEL_DIR})
    csv_files = glob.glob(os.path.join(DATA_DIR, "*_1h.csv"))
    
    datasets = {m: {'X': [], 'y': []} for m in strategy.MODES}
    
    for file_path in csv_files:
        symbol = os.path.basename(file_path).replace("_1h.csv", "")
        print(f"[*] Processing {symbol}...")
        
        df = pd.read_csv(file_path)
        # Ensure macro columns exist so indicators don't fail
        for col in ['market_btc_close', 'market_btc_vol', 'vix_close', 'dxy_close', 'eth_btc_close']:
            df[col] = df['close'] if 'btc' in col else 1.0
            
        # 1. Pre-calculate ALL indicators to avoid per-row overhead
        # We manually trigger indicator calculation to avoid dropna() issues inside strategy
        from ta.momentum import RSIIndicator
        df['rsi'] = RSIIndicator(df['close']).rsi()
        df['sma_ratio'] = df['close'].rolling(10).mean() / df['close'].rolling(30).mean()
        
        # 2. Mode Detection (Loose thresholds for 1h)
        trend = df['close'].pct_change(20) * 100
        vol = df['close'].rolling(20).std() / df['close'].rolling(20).mean() * 100
        
        is_bull = (trend > 0.5) & (vol < 2)
        is_bear = (trend < -0.5) & (vol < 2)
        
        # 3. Target
        df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
        
        # 4. Feature Selection
        feature_cols = ['rsi', 'sma_ratio'] # Start with core features
        
        df_clean = df.dropna()
        
        for mode in strategy.MODES:
            if mode == 'bull': mask = is_bull
            elif mode == 'bear': mask = is_bear
            else: mask = ~(is_bull | is_bear)
            
            mode_data = df_clean[mask.reindex(df_clean.index, fill_value=False)]
            
            if len(mode_data) > 100:
                datasets[mode]['X'].append(mode_data[feature_cols])
                datasets[mode]['y'].append(mode_data['target'])
                print(f"  -> Added {len(mode_data)} samples for {mode}")

    print("\n[*] Starting GPU Training...")
    for mode in strategy.MODES:
        if not datasets[mode]['X']:
            print(f"  [Skip] {mode} has no data.")
            continue
            
        X = pd.concat(datasets[mode]['X'])
        y = pd.concat(datasets[mode]['y'])
        
        print(f"  [GPU] Training {mode.upper()} ({len(X)} samples)...")
        model = xgb.XGBClassifier(tree_method='hist', device='cuda', n_estimators=500)
        model.fit(X, y)
        model.save_model(os.path.join(MODEL_DIR, f"{mode}_model.json"))
        print(f"  ✅ Saved {mode}")

if __name__ == "__main__":
    if not os.path.exists(MODEL_DIR): os.makedirs(MODEL_DIR)
    train_gpu()
