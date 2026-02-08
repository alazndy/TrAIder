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
START_DATE = '2015-01-01'
INITIAL_CAPITAL = 10.0
COMMISSION_RATE = 0.001

# Turkey Inflation Stats
USDTRY_2015 = 2.72
USDTRY_2026 = 31.00
TR_C_INFLATION = 13.59

def run_master_decider():
    print("="*80)
    print(f"🧠 PROTEUS MASTER DECIDER - REGIME ADAPTIVE BACKTEST")
    print(f"💰 Starting Capital: $10.0 | 📅 Period: 2015-2025")
    print("="*80)

    # 1. Load Data
    csv_files = glob.glob(os.path.join(DATA_DIR, "*_1h.csv"))
    all_data = {}
    print("[*] Syncing global markets...")
    for f in csv_files:
        symbol = os.path.basename(f).replace("_1h.csv", "")
        df = pd.read_csv(f)
        df['date'] = pd.to_datetime(df['time'], unit='ms')
        df = df[df['date'] >= START_DATE].set_index('date').sort_index()
        if not df.empty: all_data[symbol] = df

    master_timeline = pd.to_datetime(sorted(list(set().union(*[df.index for df in all_data.values()]))))
    strategy = ProteusNeo({"model_dir": MODEL_DIR})

    # Pre-calculate Indicators & Regime Features
    print("[*] Analyzing market evolution...")
    for s, df in all_data.items():
        df['rsi'] = (df['close'].diff().apply(lambda x: max(x,0)).rolling(14).mean() / 
                     df['close'].diff().apply(lambda x: abs(x)).rolling(14).mean() * 100).fillna(50)
        df['sma_ratio'] = (df['close'].rolling(10).mean() / df['close'].rolling(30).mean()).fillna(1.0)
        df['volatility'] = (df['close'].rolling(24).std() / df['close'].rolling(24).mean() * 100).fillna(0)
        
        df['pred'] = 0
        df['conf'] = 0.0
        df.loc[df['rsi'] < 35, 'pred'] = 1
        df.loc[df['rsi'] < 30, 'conf'] = 0.90
        df.loc[(df['rsi'] >= 30) & (df['rsi'] < 35), 'conf'] = 0.75
        df.loc[df['rsi'] > 65, 'pred'] = 0
        df.loc[df['rsi'] > 70, 'conf'] = 0.90

    # Simulation
    balance = INITIAL_CAPITAL
    current_asset = None
    units = 0
    trade_count = 0
    mode_stats = {"Hunter": 0, "Sniper": 0}

    print("[*] Master Decider is taking control...")

    for ts in master_timeline[::4]:
        global_vol = np.mean([all_data[s].loc[ts, 'volatility'] for s in all_data if ts in all_data[s].index])
        
        active_mode = "Sniper"
        if global_vol > 2.5: active_mode = "Sniper"
        elif global_vol < 1.0: active_mode = "Hunter"
        
        mode_stats[active_mode] += 1

        if current_asset:
            if ts in all_data[current_asset].index:
                row = all_data[current_asset].loc[ts]
                exit_now = False
                if active_mode == "Hunter" and row['pred'] == 0: exit_now = True
                if active_mode == "Sniper" and row['conf'] < 0.5: exit_now = True
                if exit_now:
                    balance = units * row['close'] * (1 - COMMISSION_RATE)
                    current_asset = None
                    units = 0
        
        if not current_asset:
            best_s, max_score = None, 0
            for s, df in all_data.items():
                if ts in df.index:
                    r = df.loc[ts]
                    can_buy = False
                    if active_mode == "Hunter" and r['pred'] == 1: can_buy = True
                    if active_mode == "Sniper" and r['pred'] == 1 and r['conf'] > 0.85: can_buy = True
                    if can_buy and r['conf'] > max_score:
                        max_score = r['conf']
                        best_s = s
            
            if best_s:
                price = all_data[best_s].loc[ts, 'close']
                units = (balance * (1 - COMMISSION_RATE)) / price
                current_asset = best_s
                balance = 0
                trade_count += 1

    if current_asset:
        balance = units * all_data[current_asset].iloc[-1]['close']

    tl_initial = INITIAL_CAPITAL * USDTRY_2015
    tl_nominal = balance * USDTRY_2026
    tl_real = tl_nominal / TR_C_INFLATION
    roi_real = (tl_real - tl_initial) / tl_initial * 100

    print("\n" + "="*80)
    print(f"🏁 MASTER DECIDER FINAL REPORT (2026)")
    print("="*80)
    print(f"📊 Mode Usage: Hunter: {mode_stats['Hunter']} | Sniper: {mode_stats['Sniper']}")
    print(f"🔄 Total Trades: {trade_count}")
    print("-" * 40)
    print(f"💵 Final USD:      ${balance:,.2f}")
    print(f"🇹🇷 Final TL (Nom): {tl_nominal:,.0f} TL")
    print(f"🛒 Real 2015 TL:   {tl_real:,.2f} TL (Start: {tl_initial:.2f} TL)")
    print(f"🚀 REAL GROWTH:    %{roi_real:+.2f}")
    print("=" * 80)

if __name__ == "__main__":
    run_master_decider()