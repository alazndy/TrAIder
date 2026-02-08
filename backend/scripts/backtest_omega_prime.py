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
START_DATE = '2025-01-01'
INITIAL_CAPITAL = 1000.0
COMMISSION_RATE = 0.001

def run_omega_prime_backtest():
    print("="*80)
    print(f"🌌 OMEGA PRIME - 5 YEAR HYPER-GROWTH (LONG/SHORT + EVOLUTION)")
    print(f"💰 Initial Capital: ${INITIAL_CAPITAL}")
    print(f"🌑 Mode: DARK MODE (Profits from Crashes too!)")
    print("="*80)

    if not os.path.exists(MODEL_PATH):
        print("[!] Omega Brain not found!")
        return
    
    model = xgb.XGBClassifier()
    model.load_model(MODEL_PATH)

    print("[*] Reconstructing market memory with On-Chain Intelligence...")
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
    probs = model.predict_proba(X)[:, 1]
    test_df['signal_prob'] = probs
    
    balance, position, units, entry_price, trade_count = INITIAL_CAPITAL, 0, 0, 0, 0
    print(f"[*] Omega Prime is hunting on {len(test_df)} windows...")
    
    for i in range(len(test_df)):
        price = test_df.iloc[i]['close']
        prob = test_df.iloc[i]['signal_prob']
        
        if prob > 0.72 and position != 1:
            if position == -1: balance = units * (entry_price - price) + (units * entry_price)
            units = (balance * (1 - COMMISSION_RATE)) / price
            entry_price, balance, position, trade_count = price, 0, 1, trade_count + 1
            
        elif prob < 0.28 and position != -1:
            if position == 1: balance = units * price * (1 - COMMISSION_RATE)
            units = (balance * (1 - COMMISSION_RATE)) / price
            entry_price, balance, position, trade_count = price, 0, -1, trade_count + 1
            
        elif 0.45 < prob < 0.55 and position != 0:
            if position == 1: balance = units * price * (1 - COMMISSION_RATE)
            elif position == -1: balance = units * (entry_price - price) + (units * entry_price)
            units, position = 0, 0

    if position == 1: balance = units * test_df.iloc[-1]['close']
    elif position == -1: balance = units * (entry_price - test_df.iloc[-1]['close']) + (units * entry_price)

    roi = (balance - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    print("\n" + "="*80)
    print(f"🏁 OMEGA PRIME MISSION COMPLETE")
    print("="*80)
    print(f"💵 Initial:      ${INITIAL_CAPITAL:,.2f}")
    print(f"💰 Final Wealth: ${balance:,.2f}")
    print(f"🚀 Total ROI:    {roi:,.2f}%")
    print(f"🔄 Total Trades: {trade_count}")
    print("="*80)

if __name__ == "__main__":
    run_omega_prime_backtest()