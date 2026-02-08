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
INITIAL_CAPITAL = 1000.0
COMMISSION_RATE = 0.001
MAX_SLOTS = 5

def run_multi_year_test(year):
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    model = xgb.XGBClassifier()
    model.load_model(MODEL_PATH)
    csv_files = glob.glob(os.path.join(DATA_DIR, "*_4h.csv"))
    assets_data, btc_df = {}, None
    for f in csv_files:
        symbol = os.path.basename(f).replace("_4h.csv", "")
        df = pd.read_csv(f)
        df['date'] = pd.to_datetime(df['time'], unit='ms')
        df = df.set_index('date').sort_index()
        df['rsi'] = (df['close'].diff().apply(lambda x: max(x,0)).rolling(14).mean() / 
                     df['close'].diff().apply(lambda x: abs(x)).rolling(14).mean() * 100).fillna(50)
        df['sma_ratio'] = (df['close'].rolling(10).mean() / df['close'].rolling(30).mean()).fillna(1.0)
        df['volatility'] = df['close'].rolling(20).std() / df['close'].rolling(20).mean() * 100
        ev = event_engine.get_event_features(df.index)
        df = pd.concat([df, ev], axis=1)
        feats = ['rsi', 'sma_ratio', 'volatility'] + [col for col in df.columns if 'event_' in col]
        df['prob'] = model.predict_proba(df[feats])[:, 1]
        assets_data[symbol] = df[(df.index >= start_date) & (df.index <= end_date)]
        if "BTC_USDT" in symbol: btc_df = assets_data[symbol]

    master_timeline = pd.to_datetime(sorted(list(set().union(*[df.index for df in assets_data.values()]))))
    balance, active_positions = INITIAL_CAPITAL, {}
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
    for sym, pos in active_positions.items():
        if not assets_data[sym].empty:
            pnl = (assets_data[sym].iloc[-1]['close'] - pos['entry'])/pos['entry'] if pos['type'] == 'long' else (pos['entry'] - assets_data[sym].iloc[-1]['close'])/pos['entry']
            balance += pos['size'] * (1 + (pnl * pos['lev']))
    return (balance - INITIAL_CAPITAL) / 10

if __name__ == "__main__":
    results = {}
    for year in [2022, 2023, 2024]:
        print(f"[*] Testing Year: {year}...")
        results[year] = run_multi_year_test(year)
    print("\n" + "="*60)
    print(f"📊 SUPERNOVA HISTORICAL PERFORMANCE")
    print("="*60)
    for year, roi in results.items():
        icon = "🐻" if year == 2022 else ("💤" if year == 2023 else "🐂")
        print(f"  {icon} {year}: %{roi:+.2f} ROI")
    print("="*60)