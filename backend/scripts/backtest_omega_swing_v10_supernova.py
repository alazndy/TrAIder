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

def run_omega_swing_supernova():
    print("="*80)
    print(f"🚀 OMEGA SWING V10 SUPERNOVA - THE INFINITE GROWTH TEST")
    print(f"💰 Starting Capital: ${INITIAL_CAPITAL}")
    print(f"⚡ Features: 2x Leverage Proxy + Correlation Guard + Aggressive Scaling")
    print("="*80)

    model = xgb.XGBClassifier()
    model.load_model(MODEL_PATH)

    csv_files = glob.glob(os.path.join(DATA_DIR, "*_4h.csv"))
    assets_data, btc_df = {}, None
    print(f"[*] Syncing assets and building market-guard...")
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
        if "BTC_USDT" in symbol: btc_df = assets_data[symbol]

    master_timeline = pd.to_datetime(sorted(list(set().union(*[df.index for df in assets_data.values()]))))
    balance, active_positions, trade_count = INITIAL_CAPITAL, {}, 0

    print(f"[*] Supernova mission started on {len(master_timeline)} periods...")
    for ts in master_timeline:
        btc_crash = False
        if btc_df is not None and ts in btc_df.index:
            if btc_df.loc[ts, 'prob'] < 0.40: btc_crash = True

        to_close = []
        for sym, pos in active_positions.items():
            if ts in assets_data[sym].index:
                row = assets_data[sym].loc[ts]
                pnl_base = (row['close'] - pos['entry'])/pos['entry'] if pos['type'] == 'long' else (pos['entry'] - row['close'])/pos['entry']
                pnl_lev = pnl_base * pos['lev']
                if (pos['type'] == 'long' and (row['prob'] < 0.48 or (btc_crash and sym != "BTC_USDT"))) or (pos['type'] == 'short' and row['prob'] > 0.52) or pnl_lev < -0.25:
                    balance += pos['size'] * (1 + pnl_lev) * (1 - COMMISSION_RATE)
                    to_close.append(sym)
        for s in to_close: del active_positions[s]

        if len(active_positions) < MAX_SLOTS and balance > 10:
            total_eq = balance + sum([p['size'] for p in active_positions.values()])
            best_s, best_t, best_p = None, None, 0
            for sym, df in assets_data.items():
                if sym in active_positions or ts not in df.index: continue
                p = df.loc[ts, 'prob']
                if p > 0.70 and p > best_p: best_p, best_s, best_t = p, sym, 'long'
                elif p < 0.30 and (1-p) > best_p: best_p, best_s, best_t = (1-p), sym, 'short'
            if best_s:
                alloc = min(0.45, max(0.15, (best_p - 0.70) * 2.0 + 0.15))
                lev = 2.0 if best_p > 0.85 else 1.0
                size = total_eq * alloc
                if balance >= size:
                    active_positions[best_s] = {'type': best_t, 'entry': assets_data[best_s].loc[ts, 'close'], 'size': size, 'lev': lev}
                    balance -= size
                    trade_count += 1

    for sym, pos in active_positions.items():
        pnl = (assets_data[sym].iloc[-1]['close'] - pos['entry'])/pos['entry'] if pos['type'] == 'long' else (pos['entry'] - assets_data[sym].iloc[-1]['close'])/pos['entry']
        balance += pos['size'] * (1 + (pnl * pos['lev']))

    print("\n" + "="*80)
    print(f"🏁 OMEGA SWING SUPERNOVA REPORT (2025)")
    print("="*80)
    print(f"💵 Initial:      ${INITIAL_CAPITAL:,.2f}")
    print(f"💰 Final Wealth: ${balance:,.2f}")
    print(f"🚀 Total ROI:    %{(balance-1000)/10:,.2f}")
    print(f"🔄 Total Trades: {trade_count}")
    print("="*80)

if __name__ == "__main__":
    run_omega_swing_supernova()