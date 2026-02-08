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
START_DATE = '2015-01-01'
INITIAL_CAPITAL = 20000.0
COMMISSION_RATE = 0.001

# Turkey Stats
USDTRY_2015 = 2.72
USDTRY_2026 = 31.00
TR_CUMULATIVE_INFLATION = 13.59

def run_omega_prime_final():
    print("="*80)
    print(f"🌌 OMEGA PRIME - 10 YEAR FINAL BOSS TEST (2015-2025)")
    print(f"💰 Starting Capital: ${INITIAL_CAPITAL:,.2f} (2015 USD)")
    print(f"🌑 Mode: LONG/SHORT DARK MODE")
    print("="*80)

    if not os.path.exists(MODEL_PATH):
        print("[!] Omega Brain not found!")
        return
    
    model = xgb.XGBClassifier()
    model.load_model(MODEL_PATH)

    print("[*] Reconstructing 10 years of market memory...")
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
    test_df['prob'] = model.predict_proba(X)[:, 1]
    
    balance, position, units, entry_price, trade_count = INITIAL_CAPITAL, 0, 0, 0, 0
    wins, losses = 0, 0
    
    print(f"[*] Simulation Start: {len(test_df)} hours...")
    for i in range(len(test_df)):
        price = test_df.iloc[i]['close']
        prob = test_df.iloc[i]['prob']
        
        if prob > 0.72 and position != 1:
            if position == -1: 
                pnl = units * (entry_price - price) + (units * entry_price)
                balance = pnl * (1 - COMMISSION_RATE)
                if price < entry_price: wins += 1
                else: losses += 1
            units = (balance * (1 - COMMISSION_RATE)) / price
            entry_price, balance, position, trade_count = price, 0, 1, trade_count + 1
            
        elif prob < 0.28 and position != -1:
            if position == 1: 
                balance = units * price * (1 - COMMISSION_RATE)
                if price > entry_price: wins += 1
                else: losses += 1
            units = (balance * (1 - COMMISSION_RATE)) / price
            entry_price, balance, position, trade_count = price, 0, -1, trade_count + 1
            
        elif 0.45 < prob < 0.55 and position != 0:
            if position == 1: 
                balance = units * price * (1 - COMMISSION_RATE)
                if price > entry_price: wins += 1
                else: losses += 1
            elif position == -1: 
                balance = (units * (entry_price - price) + (units * entry_price)) * (1 - COMMISSION_RATE)
                if price < entry_price: wins += 1
                else: losses += 1
            units, position = 0, 0

    if position == 1: balance = units * test_df.iloc[-1]['close']
    elif position == -1: balance = units * (entry_price - test_df.iloc[-1]['close']) + (units * entry_price)

    initial_tl = INITIAL_CAPITAL * USDTRY_2015
    final_tl_nom = balance * USDTRY_2026
    final_tl_real = final_tl_nom / TR_CUMULATIVE_INFLATION
    roi_real = (final_tl_real - initial_tl) / initial_tl * 100
    win_rate = (wins / (wins + losses)) * 100 if (wins+losses) > 0 else 0

    print("\n" + "="*80)
    print(f"🏁 OMEGA PRIME FINAL RESULTS (2026)")
    print("="*80)
    print(f"📊 PERFORMANCE STATS:")
    print(f"  ✅ Win Rate:      %{win_rate:.2f}")
    print(f"  🔄 Total Trades:  {trade_count}")
    print("-" * 40)
    print(f"  💵 Final USD:     ${balance:,.2f}")
    print(f"  🇹🇷 Final TL:      {final_tl_nom:,.0f} TL")
    print(f"  🛒 Real 2015 TL:  {final_tl_real:,.2f} TL (Start: {initial_tl:,.2f} TL)")
    print(f"  🚀 REAL GROWTH:   %{roi_real:,.2f}")
    print("=" * 80)

if __name__ == "__main__":
    run_omega_prime_final()