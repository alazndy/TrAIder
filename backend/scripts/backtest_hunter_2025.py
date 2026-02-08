import sys
import os
import glob
import pandas as pd
import numpy as np
from datetime import datetime
import warnings

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strategies.proteus_neo import ProteusNeo

warnings.filterwarnings('ignore')

DATA_DIR = '../data/raw'
MODEL_DIR = '../data/proteus_neo'
START_DATE = '2025-01-01'
INITIAL_CAPITAL = 1000.0
COMMISSION_RATE = 0.001

def run_master_hunter_2025():
    print("="*80)
    print(f"🦅 MASTER HUNTER CHALLENGE - 2025 OPERATİON")
    print(f"💰 Starting Capital: ${INITIAL_CAPITAL}")
    print(f"📅 Period: {START_DATE} to Now")
    print("="*80)

    strategy = ProteusNeo({"model_dir": MODEL_DIR})
    csv_files = glob.glob(os.path.join(DATA_DIR, "*_1h.csv"))
    all_signals, all_prices = {}, {}
    
    print("[*] Global Market Sync initiated...")
    for file_path in csv_files:
        symbol = os.path.basename(file_path).replace("_1h.csv", "")
        df = pd.read_csv(file_path)
        df['date'] = pd.to_datetime(df['time'], unit='ms')
        mask = (df['date'] >= START_DATE)
        df = df[mask].set_index('date').sort_index()
        if len(df) < 50: continue
        
        from ta.momentum import RSIIndicator
        df['rsi'] = RSIIndicator(df['close']).rsi().fillna(50)
        df['sma_ratio'] = (df['close'].rolling(10).mean() / df['close'].rolling(30).mean()).fillna(1.0)
        
        trend = df['close'].pct_change(20) * 100
        vol = df['close'].rolling(20).std() / df['close'].rolling(20).mean() * 100
        is_crypto = "USDT" in symbol
        t_thresh = 0.5 if not is_crypto else 1.0
        v_thresh = 1.0 if not is_crypto else 2.0
        
        df['signal'] = 0
        for mode in ['bull', 'bear', 'sideways']:
            if mode == 'bull': m_mask = (trend > t_thresh) & (vol < v_thresh)
            elif mode == 'bear': m_mask = (trend < -t_thresh) & (vol < v_thresh)
            else: m_mask = ~((trend > t_thresh) & (vol < v_thresh)) & ~((trend < -t_thresh) & (vol < v_thresh))
            
            mode_idx = df[m_mask].index
            if len(mode_idx) == 0: continue
            if strategy.models[mode]:
                X = df.loc[mode_idx, ['rsi', 'sma_ratio']]
                probs = strategy.models[mode].predict_proba(X)
                df.loc[mode_idx, 'signal'] = np.where(np.argmax(probs, axis=1) == 1, 1, -1)
        
        all_signals[symbol] = df['signal']
        all_prices[symbol] = df['close']

    master_timeline = pd.to_datetime(sorted(list(set().union(*[df.index for df in all_signals.values()]))))
    balance = INITIAL_CAPITAL
    current_asset, units, trade_count = None, 0, 0

    print(f"[*] Hunter is scanning {len(master_timeline)} hourly windows...")
    for ts in master_timeline:
        if current_asset:
            if ts in all_signals[current_asset].index:
                if all_signals[current_asset].loc[ts] == -1:
                    balance = units * all_prices[current_asset].loc[ts] * (1 - COMMISSION_RATE)
                    current_asset, units = None, 0
        
        if not current_asset:
            for symbol in all_signals:
                if ts in all_signals[symbol].index:
                    if all_signals[symbol].loc[ts] == 1:
                        current_asset = symbol
                        units = (balance * (1 - COMMISSION_RATE)) / all_prices[current_asset].loc[ts]
                        balance, trade_count = 0, trade_count + 1
                        break

    if current_asset:
        balance = units * all_prices[current_asset].iloc[-1]

    roi = (balance - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    print("\n" + "="*80)
    print(f"🏁 2025 HUNTER REPORT")
    print("="*80)
    print(f"💵 Initial Capital: ${INITIAL_CAPITAL:,.2f}")
    print(f"💰 Final Wealth:    ${balance:,.2f}")
    print(f"🚀 Total ROI:       %{roi:,.2f}")
    print(f"🔄 Total Trades:    {trade_count}")
    print("="*80)

if __name__ == "__main__":
    run_master_hunter_2025()