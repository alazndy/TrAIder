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
INITIAL_CAPITAL_PER_ASSET = 10.0

def run_world_backtest():
    print("="*80)
    print(f"🌍 PROTEUS NEO - COMPLETE WORLD BACKTEST (2025)")
    print(f"💰 Initial Capital: ${INITIAL_CAPITAL_PER_ASSET} per asset")
    print(f"📅 Period: {START_DATE} to Now")
    print("="*80)

    # Initialize Strategy
    strategy = ProteusNeo({"model_dir": MODEL_DIR})
    
    csv_files = glob.glob(os.path.join(DATA_DIR, "*_1h.csv"))
    
    total_initial = 0
    total_final = 0
    
    # Sort files to show Stocks first then Crypto
    csv_files.sort(key=lambda x: "USDT" in x)
    
    for file_path in csv_files:
        symbol = os.path.basename(file_path).replace("_1h.csv", "")
        
        # Load Data
        df = pd.read_csv(file_path)
        df['date'] = pd.to_datetime(df['time'], unit='ms')
        
        # Filter for 2025+
        mask = df['date'] >= START_DATE
        test_df = df[mask].reset_index(drop=True)
        
        if len(test_df) < 50:
            continue

        # Asset Type Detection
        is_crypto = "USDT" in symbol
        label = "CRY" if is_crypto else "STK"
        
        # Mock Missing Macro Cols
        for col in ['market_btc_close', 'market_btc_vol', 'vix_close', 'dxy_close', 'eth_btc_close']:
            test_df[col] = test_df['close'] if 'btc' in col else 1.0
            
        # Feature Generation
        from ta.momentum import RSIIndicator
        test_df['rsi'] = RSIIndicator(test_df['close']).rsi()
        test_df['sma_ratio'] = test_df['close'].rolling(10).mean() / test_df['close'].rolling(30).mean()
        test_df = test_df.fillna(0)
        
        # Mode Detection (Same as Training)
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
                
        # Simulation
        balance = INITIAL_CAPITAL_PER_ASSET
        position = 0
        trades = 0
        
        for i in range(1, len(test_df)):
            sig = test_df.loc[i, 'signal']
            price = test_df.loc[i, 'close']
            
            if sig == 1 and position == 0:
                position = balance / price
                balance = 0
                trades += 1
            elif sig == -1 and position > 0:
                balance = position * price
                position = 0
        
        final_val = balance + (position * test_df.iloc[-1]['close'])
        roi = (final_val - INITIAL_CAPITAL_PER_ASSET) / INITIAL_CAPITAL_PER_ASSET * 100
        
        total_initial += INITIAL_CAPITAL_PER_ASSET
        total_final += final_val
        
        icon = "🟢" if roi > 0 else "🔴"
        print(f"{icon} [{label}] {symbol:<12} | ROI: {roi:>8.2f}% | Trades: {trades:>4} | Value: ${final_val:.2f}")

    print("-" * 80)
    total_roi = (total_final - total_initial) / total_initial * 100
    print(f"🏆 FINAL CONSOLIDATED RESULTS")
    print(f"💵 Total Invested: ${total_initial:.2f}")
    print(f"💰 Total Wealth:   ${total_final:.2f}")
    print(f"🚀 Combined ROI:   {total_roi:.2f}%")
    print("=" * 80)

if __name__ == "__main__":
    run_world_backtest()