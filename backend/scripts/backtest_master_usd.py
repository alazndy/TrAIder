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
START_DATE = '2015-01-01'
INITIAL_CAPITAL = 10.0
COMMISSION_RATE = 0.001
US_CUMULATIVE_INFLATION = 1.36 

def run_master_usd():
    print("="*80)
    print(f"🧠 MASTER DECIDER - GLOBAL USD REALITY CHECK")
    print(f"💰 Starting Capital: $10.0 (2015 USD)")
    print(f"📉 US Inflation Hurdle: ~36% (Target > $13.60)")
    print("="*80)

    csv_files = glob.glob(os.path.join(DATA_DIR, "*_1h.csv"))
    all_data = {}
    print("[*] Syncing markets...")
    for f in csv_files:
        symbol = os.path.basename(f).replace("_1h.csv", "")
        df = pd.read_csv(f)
        df['date'] = pd.to_datetime(df['time'], unit='ms')
        df = df[df['date'] >= START_DATE].set_index('date').sort_index()
        if not df.empty: all_data[symbol] = df

    master_timeline = pd.to_datetime(sorted(list(set().union(*[df.index for df in all_data.values()]))))
    strategy = ProteusNeo({"model_dir": MODEL_DIR})

    print("[*] Pre-calculating Global Intelligence...")
    for s, df in all_data.items():
        from ta.momentum import RSIIndicator
        df['rsi'] = RSIIndicator(df['close']).rsi().fillna(50)
        df['sma_ratio'] = (df['close'].rolling(10).mean() / df['close'].rolling(30).mean()).fillna(1.0)
        df['volatility'] = (df['close'].rolling(24).std() / df['close'].rolling(24).mean() * 100).fillna(0)
        
        df['pred'] = 0
        df['conf'] = 0.0
        # Fast mock logic
        df.loc[df['rsi'] < 32, 'pred'] = 1
        df.loc[df['rsi'] < 32, 'conf'] = 0.92
        df.loc[df['rsi'] > 68, 'pred'] = 0
        df.loc[df['rsi'] > 68, 'conf'] = 0.92

    balance = INITIAL_CAPITAL
    current_asset = None
    units = 0
    trade_count = 0
    
    print("[*] Simulation Start (10 Years)...")

    for ts in master_timeline[::4]:
        active_assets = [s for s in all_data if ts in all_data[s].index]
        if not active_assets: continue
        
        market_stress = np.mean([all_data[s].loc[ts, 'volatility'] for s in active_assets])
        mode = "Sniper"
        if market_stress < 1.2: mode = "Hunter"
        
        if current_asset:
            if ts in all_data[current_asset].index:
                row = all_data[current_asset].loc[ts]
                if (mode == "Hunter" and row['pred'] == 0) or (mode == "Sniper" and row['conf'] < 0.6):
                    balance = units * row['close'] * (1 - COMMISSION_RATE)
                    current_asset = None
        
        if not current_asset:
            best_s, max_c = None, 0
            entry_conf = 0.90 if mode == "Sniper" else 0.80
            for s in active_assets:
                r = all_data[s].loc[ts]
                if r['pred'] == 1 and r['conf'] > entry_conf:
                    if r['conf'] > max_c:
                        max_c = r['conf']
                        best_s = s
            if best_s:
                price = all_data[best_s].loc[ts, 'close']
                units = (balance * (1 - COMMISSION_RATE)) / price
                current_asset = best_s
                balance = 0
                trade_count += 1

    if current_asset:
        balance = units * all_data[current_asset].iloc[-1]['close']

    real_value = balance / US_CUMULATIVE_INFLATION
    net_roi_real = (real_value - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

    print("\n" + "="*80)
    print(f"🏁 MASTER DECIDER FINAL REPORT (USD)")
    print("="*80)
    print(f"💵 Nominal Final Balance: ${balance:,.2f}")
    print(f"🛒 Real Purchasing Power:  ${real_value:,.2f} (In 2015 Dollars)")
    print(f"🚀 Real ROI (Adjusted):    %{net_roi_real:,.2f}")
    print(f"🔄 Total Trades:           {trade_count}")
    print("=" * 80)

if __name__ == "__main__":
    run_master_usd()