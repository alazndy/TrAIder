
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
COMMISSION_RATE = 0.001 # 0.1% per trade (Binance Standard)

# US Inflation Rates (Yearly) based on CPI
INFLATION_DATA = {
    2015: 0.0012, 2016: 0.0126, 2017: 0.0213, 2018: 0.0244,
    2019: 0.0181, 2020: 0.0123, 2021: 0.0470, 2022: 0.0800,
    2023: 0.0410, 2024: 0.0340, 2025: 0.0250 # Est
}

def calculate_cumulative_inflation():
    factor = 1.0
    for year in range(2015, 2026):
        rate = INFLATION_DATA.get(year, 0.025)
        factor *= (1 + rate)
    return factor

def run_inflation_backtest():
    inflation_factor = calculate_cumulative_inflation()
    
    print("="*80)
    print(f"💸 REALITY CHECK: INFLATION ADJUSTED BACKTEST (2015-2025)")
    print(f"💰 Initial: ${INITIAL_CAPITAL} per asset (in 2015 Money)")
    print(f"📉 Cumulative Inflation Factor: {inflation_factor:.2f}x (1$ in 2015 = ${inflation_factor:.2f} today)")
    print("="*80)

    strategy = ProteusNeo({"model_dir": MODEL_DIR})
    csv_files = glob.glob(os.path.join(DATA_DIR, "*_1h.csv"))
    
    # Sort: Stocks first, then Crypto
    csv_files.sort(key=lambda x: "USDT" in x)
    
    total_invested = 0
    total_nominal_wealth = 0
    
    results = []

    for file_path in csv_files:
        symbol = os.path.basename(file_path).replace("_1h.csv", "")
        
        # Load Data
        df = pd.read_csv(file_path)
        df['date'] = pd.to_datetime(df['time'], unit='ms')
        mask = df['date'] >= START_DATE
        test_df = df[mask].reset_index(drop=True)
        
        if len(test_df) < 50: continue

        # Determine Type
        is_crypto = "USDT" in symbol
        label = "CRY" if is_crypto else "STK"
        
        # Mock Macro
        for col in ['market_btc_close', 'market_btc_vol', 'vix_close', 'dxy_close', 'eth_btc_close']:
            test_df[col] = test_df['close'] if 'btc' in col else 1.0
            
        # Features
        from ta.momentum import RSIIndicator
        test_df['rsi'] = RSIIndicator(test_df['close']).rsi()
        test_df['sma_ratio'] = test_df['close'].rolling(10).mean() / test_df['close'].rolling(30).mean()
        test_df = test_df.fillna(0)
        
        # Mode
        trend = test_df['close'].pct_change(20) * 100
        vol = test_df['close'].rolling(20).std() / test_df['close'].rolling(20).mean() * 100
        t_thresh = 0.5 if not is_crypto else 1.0
        v_thresh = 1.0 if not is_crypto else 2.0
        
        modes = pd.Series('sideways', index=test_df.index)
        modes[(trend > t_thresh) & (vol < v_thresh)] = 'bull'
        modes[(trend < -t_thresh) & (vol < v_thresh)] = 'bear'
        
        # Predict
        test_df['signal'] = 0
        for mode in ['bull', 'bear', 'sideways']:
            mode_idx = modes[modes == mode].index
            if len(mode_idx) == 0: continue
            X = test_df.loc[mode_idx, ['rsi', 'sma_ratio']]
            if strategy.models[mode]:
                test_df.loc[mode_idx, 'signal'] = np.where(strategy.models[mode].predict(X) == 1, 1, -1)
        
        # Simulation with Commission
        balance = INITIAL_CAPITAL
        position = 0
        trades = 0
        
        for i in range(1, len(test_df)):
            sig = test_df.loc[i, 'signal']
            price = test_df.loc[i, 'close']
            
            if sig == 1 and position == 0:
                # Buy (Apply Commission)
                amount = balance * (1 - COMMISSION_RATE)
                position = amount / price
                balance = 0
                trades += 1
            elif sig == -1 and position > 0:
                # Sell (Apply Commission)
                amount = position * price
                balance = amount * (1 - COMMISSION_RATE)
                position = 0
        
        final_nominal = balance + (position * test_df.iloc[-1]['close'] * (1 - COMMISSION_RATE))
        final_real = final_nominal / inflation_factor
        
        total_invested += INITIAL_CAPITAL
        total_nominal_wealth += final_nominal
        
        results.append({
            'symbol': symbol,
            'nominal': final_nominal,
            'real': final_real,
            'trades': trades
        })
        
        print(f"[{label}] {symbol:<10} | Start: $10 | End(Nominal): ${final_nominal:,.2f} | Real(2015$): ${final_real:,.2f}")

    total_real_wealth = total_nominal_wealth / inflation_factor
    total_roi = (total_real_wealth - total_invested) / total_invested * 100
    
    print("-" * 80)
    print(f"🏆 FINAL WEALTH REPORT (Net of Inflation & Fees)")
    print(f"📅 10 Years Ago You Invested:   ${total_invested:,.2f}")
    print(f"💵 Today's Account Balance:     ${total_nominal_wealth:,.2f}")
    print(f"🛒 Real Purchasing Power:       ${total_real_wealth:,.2f}")
    print(f"🚀 Real ROI (After Inflation):  {total_roi:.2f}%")
    print("=" * 80)

if __name__ == "__main__":
    run_inflation_backtest()
