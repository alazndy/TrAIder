
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
INITIAL_CAPITAL_USD = 10.0
COMMISSION_RATE = 0.001

# USD/TRY Rates
USDTRY_2015 = 2.72
USDTRY_2026 = 31.00 # Approximate current

# Turkish Inflation Rates (Official CPI / TÜFE approx)
# Values represent yearly multipliers
TR_INFLATION = {
    2015: 1.0881, 2016: 1.0853, 2017: 1.1192, 2018: 1.2030,
    2019: 1.1184, 2020: 1.1460, 2021: 1.3608, 2022: 1.6427,
    2023: 1.6477, 2024: 1.4489, 2025: 1.2500 # Estimated
}

def calculate_tr_cumulative_inflation():
    factor = 1.0
    for year in TR_INFLATION:
        factor *= TR_INFLATION[year]
    return factor

def run_tr_reality_check():
    cum_inflation = calculate_tr_cumulative_inflation()
    initial_tl = INITIAL_CAPITAL_USD * USDTRY_2015
    
    print("="*80)
    print(f"🇹🇷 TURKISH REALITY CHECK: 10 YEAR SURVIVAL (2015-2025)")
    print(f"💰 Initial Investment: 10 USD = {initial_tl:.2f} TL (in 2015)")
    print(f"📈 TR Cumulative Inflation: {cum_inflation:.2f}x (Prices rose {cum_inflation:.1f} times)")
    print(f"💵 Exchange Rate: {USDTRY_2015} -> {USDTRY_2026} TRY")
    print("="*80)

    strategy = ProteusNeo({"model_dir": MODEL_DIR})
    csv_files = glob.glob(os.path.join(DATA_DIR, "*_1h.csv"))
    csv_files.sort(key=lambda x: "USDT" in x) # Stocks first
    
    total_usd_invested = 0
    total_usd_final = 0

    for file_path in csv_files:
        symbol = os.path.basename(file_path).replace("_1h.csv", "")
        df = pd.read_csv(file_path)
        df['date'] = pd.to_datetime(df['time'], unit='ms')
        test_df = df[df['date'] >= START_DATE].reset_index(drop=True)
        if len(test_df) < 50: continue

        # Feature Gen & Predict (Simplified logic from previous)
        from ta.momentum import RSIIndicator
        test_df['rsi'] = RSIIndicator(test_df['close']).rsi()
        test_df['sma_ratio'] = test_df['close'].rolling(10).mean() / test_df['close'].rolling(30).mean()
        test_df = test_df.fillna(0)
        
        # Fast Signal
        test_df['signal'] = np.where(test_df['rsi'] < 30, 1, np.where(test_df['rsi'] > 70, -1, 0))
        
        # Simulation
        balance = INITIAL_CAPITAL_USD
        pos = 0
        for i in range(len(test_df)):
            sig = test_df.loc[i, 'signal']
            price = test_df.loc[i, 'close']
            if sig == 1 and pos == 0:
                pos = (balance * (1-COMMISSION_RATE)) / price
                balance = 0
            elif sig == -1 and pos > 0:
                balance = (pos * price) * (1-COMMISSION_RATE)
                pos = 0
        
        final_usd = balance + (pos * test_df.iloc[-1]['close'] * (1-COMMISSION_RATE))
        total_usd_invested += INITIAL_CAPITAL_USD
        total_usd_final += final_usd
        
        # TR Calculations per Asset
        final_tl_nominal = final_usd * USDTRY_2026
        # Real value in 2015 terms
        final_tl_real_2015 = final_tl_nominal / cum_inflation
        
        print(f"[{symbol:<10}] USD Final: ${final_usd:,.2f} | TL Nominal: {final_tl_nominal:,.0f} | Real (2015 TL): {final_tl_real_2015:,.2f}")

    total_tl_initial = total_usd_invested * USDTRY_2015
    total_tl_final_nominal = total_usd_final * USDTRY_2026
    total_tl_final_real = total_tl_final_nominal / cum_inflation
    
    total_roi_real = (total_tl_final_real - total_tl_initial) / total_tl_initial * 100

    print("-" * 80)
    print(f"🏆 FINAL TURKISH WEALTH REPORT")
    print(f"📅 2015 Total Investment:    {total_tl_initial:.2f} TL")
    print(f"💵 2026 Nominal Balance:     {total_tl_final_nominal:,.2f} TL")
    print(f"🛒 2026 Purchasing Power:    {total_tl_final_real:,.2f} TL (in 2015 terms)")
    print(f"🚀 Real TL Growth (Net):     %{total_roi_real:,.2f}")
    print("=" * 80)

if __name__ == "__main__":
    run_tr_reality_check()
