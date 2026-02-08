import sys
import os
import pandas as pd
import numpy as np
import xgboost as xgb
from datetime import datetime
import warnings

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.event_calendar import event_engine

warnings.filterwarnings('ignore')

DATA_DIR = '../data/omega'
MODEL_PATH = '../data/proteus_omega/omega_brain.json'
START_DATE = '2019-01-01'
INITIAL_CAPITAL = 10.0
COMMISSION_RATE = 0.001
US_INFLATION_FACTOR = 1.28

def run_omega_prime_2019():
    print("="*80)
    print(f"🌌 OMEGA PRIME - THE 2019 LEGACY TEST")
    print(f"💰 Starting Capital: ${INITIAL_CAPITAL} (2019 USD)")
    print(f"📉 US Inflation Adjustment: 1.28x")
    print(f"🌑 Mode: LONG/SHORT DARK MODE")
    print("="*80)

    model = xgb.XGBClassifier()
    model.load_model(MODEL_PATH)

    print("[*] Reconstructing 7 years of market memory...")
    btc_1h = pd.read_csv(os.path.join(DATA_DIR, 'BTC_USDT_1h.csv'))
    btc_1h['date'] = pd.to_datetime(btc_1h['time'], unit='ms')
    df = btc_1h.set_index('date').sort_index()
    
    df['whale_activity'] = (df['volume'] > df['volume'].rolling(24).mean() * 3).astype(int)
    df['net_flow_proxy'] = (df['close'] - df['open']) * df['whale_activity']
    
    btc_1d = pd.read_csv(os.path.join(DATA_DIR, 'BTC_USDT_1d.csv'))
    btc_1d['date'] = pd.to_datetime(btc_1d['time'], unit='ms')
    btc_1d = btc_1d.set_index('date').sort_index()
    df['macro_trend'] = btc_1d['close'].reindex(df.index, method='ffill')
    df['micro_vol'] = df['close'].rolling(4).std()
    
    events = event_engine.get_event_features(df.index)
    df = pd.concat([df, events], axis=1)
    
    df['rsi'] = (df['close'].diff().apply(lambda x: max(x,0)).rolling(14).mean() / 
                 df['close'].diff().apply(lambda x: abs(x)).rolling(14).mean() * 100).fillna(50)
    
    features = ['rsi', 'micro_vol', 'macro_trend', 'whale_activity', 'net_flow_proxy'] + [col for col in df.columns if 'event_' in col]
    test_df = df[df.index >= START_DATE].dropna()
    
    X = test_df[features]
    test_df['signal_prob'] = model.predict_proba(X)[:, 1]
    
    balance, position, units, entry_price, trade_count = INITIAL_CAPITAL, 0, 0, 0, 0
    wins, losses = 0, 0
    
    print(f"[*] Simulation Start: {len(test_df)} hours...")
    
    for i in range(len(test_df)):
        price = test_df.iloc[i]['close']
        prob = test_df.iloc[i]['signal_prob']
        
        # LONG Entry/Switch
        if prob > 0.72 and position != 1:
            if position == -1: # Exit Short
                pnl = units * (entry_price - price) + (units * entry_price)
                if pnl > (units * entry_price): wins += 1
                else: losses += 1
                balance = pnl * (1 - COMMISSION_RATE)
            
            units = (balance * (1 - COMMISSION_RATE)) / price
            entry_price, balance, position, trade_count = price, 0, 1, trade_count + 1
            
        # SHORT Entry/Switch
        elif prob < 0.28 and position != -1:
            if position == 1: # Exit Long
                if price > entry_price: wins += 1
                else: losses += 1
                balance = units * price * (1 - COMMISSION_RATE)
            
            units = (balance * (1 - COMMISSION_RATE)) / price
            entry_price, balance, position, trade_count = price, 0, -1, trade_count + 1
            
        # EXIT to Neutral
        elif 0.45 < prob < 0.55 and position != 0:
            if position == 1: # Close Long
                if price > entry_price: wins += 1
                else: losses += 1
                balance = units * price * (1 - COMMISSION_RATE)
            elif position == -1: # Close Short
                pnl = units * (entry_price - price) + (units * entry_price)
                if pnl > (units * entry_price): wins += 1
                else: losses += 1
                balance = pnl * (1 - COMMISSION_RATE)
            
            units, position = 0, 0

    if position == 1: 
        balance = units * test_df.iloc[-1]['close']
        if test_df.iloc[-1]['close'] > entry_price: wins += 1
        else: losses += 1
    elif position == -1: 
        balance = units * (entry_price - test_df.iloc[-1]['close']) + (units * entry_price)
        if entry_price > test_df.iloc[-1]['close']: wins += 1
        else: losses += 1

    win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
    real_value = balance / US_INFLATION_FACTOR
    roi_real = (real_value - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

    print("\n" + "="*80)
    print(f"🏁 OMEGA PRIME FINAL RESULTS (2019-2026)")
    print("="*80)
    print(f"📊 PERFORMANCE STATS:")
    print(f"  ✅ Win Rate:      %{win_rate:.2f}")
    print(f"  ❌ Loss Rate:     %{(100 - win_rate):.2f}")
    print(f"  💰 Total Wins:    {wins}")
    print(f"  💀 Total Losses:  {losses}")
    print(f"  🔄 Total Trades:  {trade_count}")
    print("-" * 40)
    print(f"  💵 Final USD:     ${balance:,.2f}")
    print(f"  🛒 Real 2019 USD: ${real_value:,.2f}")
    print(f"  🚀 Real Net ROI:  %{roi_real:,.2f}")
    print("="*80)

if __name__ == "__main__":
    run_omega_prime_2019()