import sys
import os
import glob
import pandas as pd
import numpy as np
import json
from datetime import datetime
import warnings

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strategies.proteus_neo import ProteusNeo

warnings.filterwarnings('ignore')

DATA_DIR = '../data/raw'
MODEL_DIR = '../data/proteus_neo'
SIDEWINDER_MAP = '../data/sidewinder_map.json'
START_DATE = '2015-01-01'
INITIAL_CAPITAL = 100.0
COMMISSION_RATE = 0.001

# Turkey Stats
USDTRY_2015 = 2.72
USDTRY_2026 = 31.00
TR_CUMULATIVE_INFLATION = 13.59 # Prices rose 13.6x

def run_showdown():
    print("="*80)
    print(f"⚔️ THE ULTIMATE SHOWDOWN: HUNTER vs SNIPER (2015-2025)")
    print(f"💰 Starting Capital: $10.0 per bot")
    print(f"🇹🇷 Inflation Hurdle: Beat 1359% return to survive")
    print("="*80)

    # 1. Load Data
    csv_files = glob.glob(os.path.join(DATA_DIR, "*_1h.csv"))
    all_data = {}
    print("[*] Loading history...")
    for f in csv_files:
        symbol = os.path.basename(f).replace("_1h.csv", "")
        df = pd.read_csv(f)
        df['date'] = pd.to_datetime(df['time'], unit='ms')
        df = df[df['date'] >= START_DATE].set_index('date').sort_index()
        if not df.empty: all_data[symbol] = df

    master_timeline = pd.to_datetime(sorted(list(set().union(*[df.index for df in all_data.values()]))))
    
    # Bots
    bots = {
        "Hunter 🦅": {"balance": INITIAL_CAPITAL, "asset": None, "units": 0, "trades": 0},
        "Sniper 🎯": {"balance": INITIAL_CAPITAL, "asset": None, "units": 0, "trades": 0}
    }
    
    strategy = ProteusNeo({"model_dir": MODEL_DIR})
    
    # Pre-calc
    print("[*] Pre-calculating AI Signals...")
    for s, df in all_data.items():
        from ta.momentum import RSIIndicator
        df['rsi'] = RSIIndicator(df['close']).rsi().fillna(50)
        df['sma_ratio'] = (df['close'].rolling(10).mean() / df['close'].rolling(30).mean()).fillna(1.0)
        
        df['mode'] = 'sideways'
        trend = df['close'].pct_change(20) * 100
        vol = df['close'].rolling(20).std() / df['close'].rolling(20).mean() * 100
        t_thresh = 0.5 if "USDT" not in s else 1.0
        v_thresh = 1.0 if "USDT" not in s else 2.0
        df.loc[(trend > t_thresh) & (vol < v_thresh), 'mode'] = 'bull'
        df.loc[(trend < -t_thresh) & (vol < v_thresh), 'mode'] = 'bear'
        
        df['pred'] = 0
        df['conf'] = 0.0
        for mode in ['bull', 'bear', 'sideways']:
            idx = df[df['mode'] == mode].index
            if len(idx) == 0: continue
            if strategy.models[mode]:
                X = df.loc[idx, ['rsi', 'sma_ratio']]
                probs = strategy.models[mode].predict_proba(X)
                df.loc[idx, 'pred'] = np.argmax(probs, axis=1)
                df.loc[idx, 'conf'] = np.max(probs, axis=1)

    print("[*] Simulation Start...")
    for ts in master_timeline[::4]: 
        for name, bot in bots.items():
            if bot['asset']:
                if ts in all_data[bot['asset']].index:
                    row = all_data[bot['asset']].loc[ts]
                    exit_signal = False
                    if name == "Hunter 🦅" and row['pred'] == 0: exit_signal = True
                    elif name == "Sniper 🎯" and row['conf'] < 0.6: exit_signal = True
                    
                    if exit_signal:
                        bot['balance'] = bot['units'] * row['close'] * (1 - COMMISSION_RATE)
                        bot['asset'] = None
                        bot['units'] = 0
            
            if not bot['asset']:
                best_s, best_c = None, 0
                for s, df in all_data.items():
                    if ts in df.index:
                        r = df.loc[ts]
                        if name == "Hunter 🦅" and r['pred'] == 1:
                            if r['conf'] > best_c: best_s, best_c = s, r['conf']
                        elif name == "Sniper 🎯" and r['pred'] == 1 and r['conf'] > 0.85:
                            if r['conf'] > best_c: best_s, best_c = s, r['conf']
                
                if best_s:
                    bot['units'] = (bot['balance'] * (1 - COMMISSION_RATE)) / all_data[best_s].loc[ts, 'close']
                    bot['asset'] = best_s
                    bot['balance'] = 0
                    bot['trades'] += 1

    print("\n" + "="*80)
    print(f"🏁 FINAL SHOWDOWN RESULTS (2026)")
    print("="*80)
    for name, bot in bots.items():
        val = bot['balance'] if not bot['asset'] else bot['units'] * all_data[bot['asset']].iloc[-1]['close']
        tl_real = (val * USDTRY_2026) / TR_CUMULATIVE_INFLATION
        gain = (tl_real - (INITIAL_CAPITAL * USDTRY_2015)) / (INITIAL_CAPITAL * USDTRY_2015) * 100
        print(f"🤖 {name} | USD: ${val:,.2f} | Real 2015 TL: {tl_real:,.2f} TL | Net Real: {gain:+.2f}% | Trades: {bot['trades']}")
    print("="*80)

if __name__ == "__main__":
    run_showdown()