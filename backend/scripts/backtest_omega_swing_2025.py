import sys
import os
import glob
import pandas as pd
import numpy as np
import xgboost as xgb
from datetime import datetime
import warnings

# Add paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.event_calendar import event_engine

warnings.filterwarnings('ignore')

DATA_DIR = '../data/omega_4h'
MODEL_PATH = '../data/proteus_omega_4h/omega_4h_brain.json'
START_DATE = '2025-01-01'
INITIAL_CAPITAL = 1000.0
COMMISSION_RATE = 0.001
MAX_SLOTS = 5

def run_omega_swing_2025():
    print("="*80)
    print(f"🌊 OMEGA SWING 4H - 5-SLOT PORTFOLIO TEST (2025)")
    print(f"💰 Initial Capital: ${INITIAL_CAPITAL} | 🎰 Max Slots: {MAX_SLOTS}")
    print("="*80)

    model = xgb.XGBClassifier()
    model.load_model(MODEL_PATH)

    csv_files = glob.glob(os.path.join(DATA_DIR, "*_4h.csv"))
    assets_data = {}
    print(f"[*] Syncing assets...")
    for f in csv_files:
        symbol = os.path.basename(f).replace("_4h.csv", "")
        df = pd.read_csv(f)
        df['date'] = pd.to_datetime(df['time'], unit='ms')
        df = df[df['date'] >= '2024-10-01'].set_index('date').sort_index()
        df['rsi'] = (df['close'].diff().apply(lambda x: max(x,0)).rolling(14).mean() / 
                     df['close'].diff().apply(lambda x: abs(x)).rolling(14).mean() * 100).fillna(50)
        df['sma_ratio'] = (df['close'].rolling(10).mean() / df['close'].rolling(30).mean()).fillna(1.0)
        df['volatility'] = df['close'].rolling(20).std() / df['close'].rolling(20).mean() * 100
        ev = event_engine.get_event_features(df.index)
        df = pd.concat([df, ev], axis=1)
        feats = ['rsi', 'sma_ratio', 'volatility'] + [col for col in df.columns if 'event_' in col]
        df['prob'] = model.predict_proba(df[feats])[:, 1]
        assets_data[symbol] = df[df.index >= START_DATE]

    master_timeline = pd.to_datetime(sorted(list(set().union(*[df.index for df in assets_data.values()]))))
    balance, active_positions, trade_count = INITIAL_CAPITAL, {}, 0

    print(f"[*] Swing hunting on {len(master_timeline)} periods...")
    for ts in master_timeline:
        to_close = []
        for sym, pos in active_positions.items():
            if ts in assets_data[sym].index:
                if assets_data[sym].loc[ts, 'prob'] < 0.48:
                    pnl = (assets_data[sym].loc[ts, 'close'] - pos['entry']) / pos['entry']
                    balance += pos['size'] * (1 + pnl) * (1 - COMMISSION_RATE)
                    to_close.append(sym)
        for s in to_close: del active_positions[s]

        if len(active_positions) < MAX_SLOTS and balance > 10:
            total_equity = balance + sum([p['size'] for p in active_positions.values()])
            slot_size = total_equity / MAX_SLOTS
            if balance >= slot_size:
                best_s, max_p = None, 0
                for sym, df in assets_data.items():
                    if sym in active_positions or ts not in df.index: continue
                    if df.loc[ts, 'prob'] > 0.75:
                        if df.loc[ts, 'prob'] > max_p: max_p, best_s = df.loc[ts, 'prob'], sym
                if best_s:
                    active_positions[best_s] = {'entry': assets_data[best_s].loc[ts, 'close'], 'size': slot_size}
                    balance, trade_count = balance - slot_size, trade_count + 1

    for sym, pos in active_positions.items():
        pnl = (assets_data[sym].iloc[-1]['close'] - pos['entry']) / pos['entry']
        balance += pos['size'] * (1 + pnl)

    roi = (balance - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    print("\n" + "="*80)
    print(f"🏁 OMEGA SWING 2025 REPORT")
    print("="*80)
    print(f"💵 Initial:      ${INITIAL_CAPITAL:,.2f}")
    print(f"💰 Final Wealth: ${balance:,.2f}")
    print(f"🚀 Total ROI:    %{roi:,.2f}")
    print(f"🔄 Total Trades: {trade_count}")
    print("="*80)

if __name__ == "__main__":
    run_omega_swing_2025()