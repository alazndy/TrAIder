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
from utils.risk_manager import risk_engine

warnings.filterwarnings('ignore')

DATA_DIR = '../data/omega'
MODEL_PATH = '../data/proteus_omega/omega_brain.json'
START_DATE = '2025-01-01'
INITIAL_CAPITAL = 1000.0
COMMISSION_RATE = 0.001

def run_omega_crypto_2025():
    print("="*80)
    print(f"💎 OMEGA PRIME - 2025 CRYPTO-ONLY PERFORMANCE TEST")
    print(f"💰 Starting Capital: ${INITIAL_CAPITAL}")
    print(f"🌑 Strategy: Long/Short + Kelly Risk Management")
    print("="*80)

    model = xgb.XGBClassifier()
    model.load_model(MODEL_PATH)

    csv_files = [f for f in glob.glob(os.path.join(DATA_DIR, "*_1h.csv")) if "USDT" in f]
    assets_data = {}
    print(f"[*] Syncing {len(csv_files)} crypto assets...")
    for f in csv_files:
        symbol = os.path.basename(f).replace("_1h.csv", "")
        df = pd.read_csv(f)
        df['date'] = pd.to_datetime(df['time'], unit='ms')
        df = df[df['date'] >= '2024-12-01'].set_index('date').sort_index()
        df['rsi'] = (df['close'].diff().apply(lambda x: max(x,0)).rolling(14).mean() / 
                     df['close'].diff().apply(lambda x: abs(x)).rolling(14).mean() * 100).fillna(50)
        df['micro_vol'] = df['close'].rolling(4).std().fillna(0)
        df['macro_trend'] = df['close'].rolling(24).mean().fillna(df['close'])
        df['whale_activity'] = (df['volume'] > df['volume'].rolling(24).mean() * 2.5).astype(int)
        df['net_flow_proxy'] = (df['close'] - df['open']) * df['whale_activity']
        ev = event_engine.get_event_features(df.index)
        df = pd.concat([df, ev], axis=1)
        feats = ['rsi', 'micro_vol', 'macro_trend', 'whale_activity', 'net_flow_proxy'] + [col for col in df.columns if 'event_' in col]
        df['prob'] = model.predict_proba(df[feats])[:, 1]
        assets_data[symbol] = df[df.index >= START_DATE]

    master_timeline = pd.to_datetime(sorted(list(set().union(*[df.index for df in assets_data.values()]))))
    balance, active_positions, trade_log = INITIAL_CAPITAL, {}, []

    print(f"[*] Trading through {len(master_timeline)} crypto hours...")
    for ts in master_timeline:
        to_close = []
        for sym, pos in active_positions.items():
            if ts in assets_data[sym].index:
                price, prob = assets_data[sym].loc[ts, 'close'], assets_data[sym].loc[ts, 'prob']
                pnl = (price - pos['entry'])/pos['entry'] if pos['type'] == 'long' else (pos['entry'] - price)/pos['entry']
                if (pos['type'] == 'long' and prob < 0.48) or (pos['type'] == 'short' and prob > 0.52) or pnl < -0.05:
                    balance += pos['size_usd'] * (1 + pnl) * (1 - COMMISSION_RATE)
                    to_close.append(sym)
                    trade_log.append(pnl)
        for sym in to_close: del active_positions[sym]

        if balance > 10 and len(active_positions) < 5:
            for sym, df in assets_data.items():
                if sym in active_positions or ts not in df.index: continue
                row = df.loc[ts]
                if (row['prob'] > 0.78 or row['prob'] < 0.22) and row['whale_activity'] == 1:
                    win_p = row['prob'] if row['prob'] > 0.78 else (1 - row['prob'])
                    alloc = risk_engine.calculate_position_size(win_p)
                    if alloc > 0.02:
                        size = balance * alloc
                        balance -= size
                        active_positions[sym] = {'type': 'long' if row['prob'] > 0.78 else 'short', 'entry': row['close'], 'size_usd': size}
                        if len(active_positions) >= 5: break

    for sym, pos in active_positions.items():
        price = assets_data[sym].iloc[-1]['close']
        pnl = (price - pos['entry'])/pos['entry'] if pos['type'] == 'long' else (pos['entry'] - price)/pos['entry']
        balance += pos['size_usd'] * (1 + pnl)

    roi = (balance - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    win_rate = len([t for t in trade_log if t > 0]) / len(trade_log) * 100 if trade_log else 0

    print("\n" + "="*80)
    print(f"🏁 OMEGA CRYPTO 2025 FINAL REPORT")
    print("="*80)
    print(f"💵 Initial:      ${INITIAL_CAPITAL:,.2f}")
    print(f"💰 Final Wealth: ${balance:,.2f}")
    print(f"🚀 Total ROI:    %{roi:,.2f}")
    print(f"✅ Win Rate:     %{win_rate:.2f}")
    print(f"🔄 Total Trades: {len(trade_log)}")
    print("="*80)

if __name__ == "__main__":
    run_omega_crypto_2025()