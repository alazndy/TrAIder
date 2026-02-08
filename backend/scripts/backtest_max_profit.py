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
START_DATE = '2024-01-01'
END_DATE = '2025-12-31'
INITIAL_CAPITAL = 10.0

def run_max_profit_backtest():
    print("="*80)
    print(f"🚀 PROTEUS NEO - MAX PROFIT CHALLENGE (10$ to ???)")
    print(f"💰 Starting Capital: ${INITIAL_CAPITAL}")
    print(f"📅 Period: {START_DATE} to {END_DATE}")
    print("="*80)

    # 1. Load All Assets and Pre-calculate Signals
    strategy = ProteusNeo({"model_dir": MODEL_DIR})
    csv_files = glob.glob(os.path.join(DATA_DIR, "*_1h.csv"))
    
    all_signals = {}
    all_prices = {}
    
    print("[*] Loading assets and pre-calculating global signals...")
    
    for file_path in csv_files:
        symbol = os.path.basename(file_path).replace("_1h.csv", "")
        df = pd.read_csv(file_path)
        df['date'] = pd.to_datetime(df['time'], unit='ms')
        mask = (df['date'] >= START_DATE) & (df['date'] <= END_DATE)
        df = df[mask].set_index('date')
        if len(df) < 100: continue
        
        from ta.momentum import RSIIndicator
        df['rsi'] = RSIIndicator(df['close']).rsi()
        df['sma_ratio'] = df['close'].rolling(10).mean() / df['close'].rolling(30).mean()
        df = df.fillna(0)
        
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
                preds = strategy.models[mode].predict(X)
                df.loc[mode_idx, 'signal'] = np.where(preds == 1, 1, -1)
        
        all_signals[symbol] = df['signal']
        all_prices[symbol] = df['close']

    # 2. Master Timeline Simulation
    master_timeline = pd.to_datetime(pd.concat(all_prices.values()).index.unique()).sort_values()
    balance = INITIAL_CAPITAL
    current_asset = None
    units = 0
    trade_count = 0

    print(f"[*] Starting Global Opportunity Scan on {len(master_timeline)} hours...")

    for ts in master_timeline:
        if current_asset:
            if ts in all_signals[current_asset].index:
                signal = all_signals[current_asset].loc[ts]
                price = all_prices[current_asset].loc[ts]
                if signal == -1:
                    balance = units * price
                    current_asset = None
                    units = 0
        
        if not current_asset:
            for symbol in all_signals:
                if ts in all_signals[symbol].index:
                    if all_signals[symbol].loc[ts] == 1:
                        current_asset = symbol
                        price = all_prices[current_asset].loc[ts]
                        units = balance / price
                        balance = 0
                        trade_count += 1
                        break

    if current_asset:
        balance = units * all_prices[current_asset].iloc[-1]

    roi = (balance - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    print("\n" + "="*70)
    print(f"🏁 CHALLENGE COMPLETE")
    print("="*70)
    print(f"💵 Initial:      ${INITIAL_CAPITAL}")
    print(f"💰 Final Wealth: ${balance:,.2f}")
    print(f"🚀 Total ROI:    {roi:,.2f}%")
    print(f"🔄 Total Trades: {trade_count}")
    print("="*70)

if __name__ == "__main__":
    run_max_profit_backtest()