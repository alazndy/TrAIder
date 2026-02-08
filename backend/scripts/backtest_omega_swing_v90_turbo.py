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

def run_omega_swing_turbo():
    print("="*80)
    print(f"🚀 OMEGA SWING TURBO - PROFIT MAXIMIZATION TEST (2025)")
    print(f"💰 Starting Capital: ${INITIAL_CAPITAL}")
    print(f"🌑 Mode: Long/Short + Dynamic Scaling")
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

    print(f"[*] Turbo hunting on {len(master_timeline)} periods...")
    for ts in master_timeline:
        to_close = []
        for sym, pos in active_positions.items():
            if ts in assets_data[sym].index:
                row = assets_data[sym].loc[ts]
                p, prob = row['close'], row['prob']
                pnl = (p - pos['entry'])/pos['entry'] if pos['type'] == 'long' else (pos['entry'] - p)/pos['entry']
                if (pos['type'] == 'long' and prob < 0.48) or (pos['type'] == 'short' and prob > 0.52):
                    balance += pos['size'] * (1 + pnl) * (1 - COMMISSION_RATE)
                    to_close.append(sym)
        for s in to_close: del active_positions[s]

        if len(active_positions) < MAX_SLOTS and balance > 10:
            total_eq = balance + sum([p['size'] for p in active_positions.values()])
            best_s, best_t, best_p = None, None, 0
            for sym, df in assets_data.items():
                if sym in active_positions or ts not in df.index: continue
                p = df.loc[ts, 'prob']
                if p > 0.72 and p > best_p: best_p, best_s, best_t = p, sym, 'long'
                elif p < 0.28 and (1-p) > best_p: best_p, best_s, best_t = (1-p), sym, 'short'
            if best_s:
                multiplier = max(0.1, (best_p - 0.70) * 1.5 + 0.1)
                alloc = min(0.40, multiplier)
                size = total_eq * alloc
                if balance >= size:
                    active_positions[best_s] = {'type': best_t, 'entry': assets_data[best_s].loc[ts, 'close'], 'size': size}
                    balance, trade_count = balance - size, trade_count + 1

    for sym, pos in active_positions.items():
        pnl = (assets_data[sym].iloc[-1]['close'] - pos['entry'])/pos['entry'] if pos['type'] == 'long' else (pos['entry'] - assets_data[sym].iloc[-1]['close'])/pos['entry']
        balance += pos['size'] * (1 + pnl)

    print("\n" + "="*80)
    print(f"🏁 OMEGA SWING TURBO REPORT (2025)")
    print("="*80)
    print(f"💵 Initial:      ${INITIAL_CAPITAL:,.2f}")
    print(f"💰 Final Wealth: ${balance:,.2f}")
    print(f"🚀 Total ROI:    %{(balance-1000)/10:,.2f}")
    print(f"🔄 Total Trades: {trade_count}")
    print("="*80)

if __name__ == "__main__":
    run_omega_swing_turbo()