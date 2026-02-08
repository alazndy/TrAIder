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
CONF_ENTRY_LONG = 0.65
CONF_ENTRY_SHORT = 0.35
TRAILING_STOP = 0.03
TARGETS = ['BTC_USDT', 'ETH_USDT', 'SOL_USDT']

def run_profit_hunter():
    print("="*80)
    print(f"💰 OMEGA PROFIT HUNTER - 2025 REVENUE MAXIMIZER")
    print(f"🎯 Targets: {TARGETS} | 🌑 Mode: Long/Short + Trailing Stop")
    print("="*80)

    model = xgb.XGBClassifier()
    model.load_model(MODEL_PATH)

    assets_data = {}
    print(f"[*] Syncing assets...")
    for sym in TARGETS:
        f = os.path.join(DATA_DIR, f"{sym}_1h.csv")
        if not os.path.exists(f): continue
        df = pd.read_csv(f)
        df['date'] = pd.to_datetime(df['time'], unit='ms')
        df = df[df['date'] >= '2024-12-01'].set_index('date').sort_index()
        df['rsi'] = (df['close'].diff().apply(lambda x: max(x,0)).rolling(14).mean() / 
                     df['close'].diff().apply(lambda x: abs(x)).rolling(14).mean() * 100).fillna(50)
        df['micro_vol'] = df['close'].rolling(4).std().fillna(0)
        df['macro_trend'] = df['close'].rolling(24).mean().fillna(df['close'])
        df['whale'] = (df['volume'] > df['volume'].rolling(24).mean() * 2.0).astype(int)
        df['net_flow'] = (df['close'] - df['open']) * df['whale']
        ev = event_engine.get_event_features(df.index)
        df = pd.concat([df, ev], axis=1)
        feats = ['rsi', 'micro_vol', 'macro_trend', 'whale', 'net_flow'] + [col for col in df.columns if 'event_' in col]
        df['prob'] = model.predict_proba(df[feats])[:, 1]
        assets_data[sym] = df[df.index >= START_DATE]

    master_timeline = pd.to_datetime(sorted(list(set().union(*[df.index for df in assets_data.values()]))))
    balance, current_asset, pos_type, units, entry_price, hi, lo, trade_count = INITIAL_CAPITAL, None, None, 0, 0, 0, 0, 0

    print(f"[*] Hunting profit on {len(master_timeline)} hours...")
    for ts in master_timeline:
        if current_asset:
            if ts in assets_data[current_asset].index:
                price, prob = assets_data[current_asset].loc[ts, 'close'], assets_data[current_asset].loc[ts, 'prob']
                exit_now = False
                if pos_type == 'long':
                    hi = max(hi, price)
                    if price < hi * (1 - TRAILING_STOP) or prob < 0.45: exit_now = True
                    if exit_now: balance, current_asset = units * price * (1 - COMMISSION_RATE), None
                elif pos_type == 'short':
                    lo = min(lo, price)
                    if price > lo * (1 + TRAILING_STOP) or prob > 0.55: exit_now = True
                    if exit_now: balance, current_asset = (units * (entry_price - price) + (units * entry_price)) * (1 - COMMISSION_RATE), None

        if not current_asset and balance > 10:
            best_s, best_p, best_t = None, 0, None
            for sym, df in assets_data.items():
                if ts not in df.index: continue
                p = df.loc[ts, 'prob']
                if p > CONF_ENTRY_LONG and p > best_p: best_p, best_s, best_t = p, sym, 'long'
                elif p < CONF_ENTRY_SHORT and (1-p) > best_p: best_p, best_s, best_t = (1-p), sym, 'short'
            if best_s:
                current_asset, pos_type, entry_price = best_s, best_t, assets_data[best_s].loc[ts, 'close']
                hi, lo, units, balance, trade_count = entry_price, entry_price, (balance * (1 - COMMISSION_RATE)) / entry_price, 0, trade_count + 1

    if current_asset:
        p = assets_data[current_asset].iloc[-1]['close']
        if pos_type == 'long': balance = units * p
        else: balance = units * (entry_price - p) + (units * entry_price)

    print("\n" + "="*80)
    print(f"🏁 PROFIT HUNTER 2025 REPORT")
    print("="*80)
    print(f"💵 Initial:      ${INITIAL_CAPITAL:,.2f}")
    print(f"💰 Final Wealth: ${balance:,.2f}")
    print(f"🚀 Total ROI:    %{(balance-1000)/10:,.2f}")
    print(f"🔄 Total Trades: {trade_count}")
    print("="*80)

if __name__ == "__main__":
    run_profit_hunter()