import sys
import os
import glob
import pandas as pd
import numpy as np
import xgboost as xgb
from datetime import datetime
import warnings

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.event_calendar import event_engine

warnings.filterwarnings('ignore')

DATA_DIR = '../data/raw'
MODEL_PATH = '../data/proteus_omega/omega_brain.json'
START_DATE = '2025-01-01'
INITIAL_CAPITAL = 1000.0
COMMISSION_RATE = 0.001
CONFIDENCE_THRESHOLD = 0.88
TARGETS = ['BTC_USDT', 'ETH_USDT', 'SOL_USDT', 'NVDA']

def run_perfect_sniper_2025():
    print("="*80)
    print(f"🎯 PERFECT SNIPER - 2025 FINAL PERFORMANCE TEST")
    print(f"💰 Starting Capital: ${INITIAL_CAPITAL}")
    print(f"🧠 Confidence: {CONFIDENCE_THRESHOLD*100}% | 🐋 Whale Approval Required")
    print("="*80)

    model = xgb.XGBClassifier()
    model.load_model(MODEL_PATH)

    assets_data = {}
    print(f"[*] Syncing {TARGETS}...")
    for symbol in TARGETS:
        file_path = os.path.join(DATA_DIR, f"{symbol}_1h.csv")
        if not os.path.exists(file_path): continue
        df = pd.read_csv(file_path)
        df['date'] = pd.to_datetime(df['time'], unit='ms')
        df = df[df['date'] >= '2024-12-01'].set_index('date').sort_index()
        df['rsi'] = (df['close'].diff().apply(lambda x: max(x,0)).rolling(14).mean() / 
                     df['close'].diff().apply(lambda x: abs(x)).rolling(14).mean() * 100).fillna(50)
        df['micro_vol'] = df['close'].rolling(4).std().fillna(0)
        df['macro_trend'] = df['close'].rolling(24).mean().fillna(df['close'])
        df['whale'] = (df['volume'] > df['volume'].rolling(24).mean() * 2.5).astype(int)
        df['net_flow'] = (df['close'] - df['open']) * df['whale']
        ev = event_engine.get_event_features(df.index)
        df = pd.concat([df, ev], axis=1)
        feats = ['rsi', 'micro_vol', 'macro_trend', 'whale', 'net_flow'] + [col for col in df.columns if 'event_' in col]
        df['prob'] = model.predict_proba(df[feats])[:, 1]
        assets_data[symbol] = df[df.index >= START_DATE]

    master_timeline = pd.to_datetime(sorted(list(set().union(*[df.index for df in assets_data.values()]))))
    balance, current_asset, units, trade_count = INITIAL_CAPITAL, None, 0, 0

    print(f"[*] Simulation Start ({len(master_timeline)} hours)...")
    for ts in master_timeline:
        if current_asset:
            if ts in assets_data[current_asset].index:
                if assets_data[current_asset].loc[ts, 'prob'] < 0.45:
                    balance = units * assets_data[current_asset].loc[ts, 'close'] * (1 - COMMISSION_RATE)
                    current_asset, units = None, 0
        
        if not current_asset:
            best_s, max_p = None, 0
            for sym in TARGETS:
                if ts in assets_data[sym].index:
                    row = assets_data[sym].loc[ts]
                    if row['prob'] > CONFIDENCE_THRESHOLD and row['whale'] == 1:
                        if row['prob'] > max_p: max_p, best_s = row['prob'], sym
            if best_s:
                current_asset = best_s
                units = (balance * (1 - COMMISSION_RATE)) / assets_data[current_asset].loc[ts, 'close']
                balance, trade_count = 0, trade_count + 1

    if current_asset:
        balance = units * assets_data[current_asset].iloc[-1]['close']

    roi = (balance - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    print("\n" + "="*80)
    print(f"🏁 PERFECT SNIPER 2025 REPORT")
    print("="*80)
    print(f"💵 Initial:      ${INITIAL_CAPITAL:,.2f}")
    print(f"💰 Final Wealth: ${balance:,.2f}")
    print(f"🚀 Total ROI:    %{roi:,.2f}")
    print(f"🔄 Total Trades: {trade_count}")
    print(f"💎 Efficiency:   {roi/trade_count:.2f}% per trade" if trade_count > 0 else "N/A")
    print("="*80)

if __name__ == "__main__":
    run_perfect_sniper_2025()