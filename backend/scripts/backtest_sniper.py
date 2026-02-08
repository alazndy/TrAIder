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

# SNIPER SETTINGS
CONFIDENCE_THRESHOLD = 0.75  # Only trade if AI is 75% sure
VOLATILITY_THRESHOLD = 1.5   # Only trade if asset is moving (Standard Deviation)

def run_sniper_backtest():
    print("="*80)
    print(f"🎯 PROTEUS SNIPER - HIGH PRECISION BACKTEST")
    print(f"💰 Starting Capital: ${INITIAL_CAPITAL}")
    print(f"🧠 Min Confidence: {CONFIDENCE_THRESHOLD*100}% | ⚡ Min Volatility: {VOLATILITY_THRESHOLD}")
    print("="*80)

    strategy = ProteusNeo({"model_dir": MODEL_DIR})
    csv_files = glob.glob(os.path.join(DATA_DIR, "*_1h.csv"))
    
    all_signals = {}
    all_prices = {}
    all_confidences = {} # To store AI certainty
    all_volatilities = {} # To store potential return size
    
    print("[*] Loading assets and calculating Sniper Scores...")
    
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
        df['confidence'] = 0.0 # Default confidence
        
        for mode in ['bull', 'bear', 'sideways']:
            if mode == 'bull': m_mask = (trend > t_thresh) & (vol < v_thresh)
            elif mode == 'bear': m_mask = (trend < -t_thresh) & (vol < v_thresh)
            else: m_mask = ~((trend > t_thresh) & (vol < v_thresh)) & ~((trend < -t_thresh) & (vol < v_thresh))
            
            mode_idx = df[m_mask].index
            if len(mode_idx) == 0: continue
            
            if strategy.models[mode]:
                X = df.loc[mode_idx, ['rsi', 'sma_ratio']]
                # GET PROBABILITY instead of just class
                probs = strategy.models[mode].predict_proba(X)
                
                # XGBoost returns [prob_class_0, prob_class_1]
                # We want prob_class_1 (BUY confidence)
                buy_probs = probs[:, 1]
                
                df.loc[mode_idx, 'confidence'] = buy_probs
                
                # Signal is strictly based on Confidence Threshold
                df.loc[mode_idx, 'signal'] = np.where(buy_probs > CONFIDENCE_THRESHOLD, 1, -1)
        
        all_signals[symbol] = df['signal']
        all_prices[symbol] = df['close']
        all_confidences[symbol] = df['confidence']
        all_volatilities[symbol] = vol

    # 2. Sniper Execution Logic
    master_timeline = pd.to_datetime(pd.concat(all_prices.values()).index.unique()).sort_values()
    balance = INITIAL_CAPITAL
    current_asset = None
    units = 0
    trade_count = 0
    
    print(f"[*] Sniper waiting in the bushes... ({len(master_timeline)} hours)")

    for ts in master_timeline:
        # Exit Check (Trailing Stop or Signal Reversal)
        if current_asset:
            if ts in all_signals[current_asset].index:
                # Dynamic Stop Loss / Take Profit could be added here
                # For now, strict signal reversal (Confidence dropped below 50% effectively)
                current_conf = all_confidences[current_asset].loc[ts]
                
                # If confidence drops drastically, bail out
                if current_conf < 0.40:
                    price = all_prices[current_asset].loc[ts]
                    balance = units * price
                    # print(f"  🔴 [EXIT] {current_asset} | Conf dropped to {current_conf:.2f} | Bal: ${balance:.2f}")
                    current_asset = None
                    units = 0
            else:
                pass # Market closed, hold position
        
        # Entry Check (Find the PERFECT Shot)
        if not current_asset:
            best_asset = None
            max_score = 0
            
            for symbol in all_signals:
                if ts in all_signals[symbol].index:
                    conf = all_confidences[symbol].loc[ts]
                    vol = all_volatilities[symbol].loc[ts]
                    
                    # SNIPER CRITERIA:
                    # 1. Confidence > Threshold (75%)
                    # 2. Volatility > Threshold (Must be moving to make big money)
                    if conf > CONFIDENCE_THRESHOLD and vol > VOLATILITY_THRESHOLD:
                        # Score = Confidence * Volatility (High certainty on big move)
                        score = conf * vol
                        if score > max_score:
                            max_score = score
                            best_asset = symbol
            
            if best_asset:
                price = all_prices[best_asset].loc[ts]
                units = balance / price
                balance = 0
                current_asset = best_asset
                trade_count += 1
                conf = all_confidences[best_asset].loc[ts]
                # print(f"  🟢 [SNIPE] {best_asset} | Conf: {conf:.2f} | Price: ${price:.2f}")

    if current_asset:
        balance = units * all_prices[current_asset].iloc[-1]

    roi = (balance - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    
    print("\n" + "="*80)
    print(f"🏁 SNIPER MISSION REPORT")
    print("="*80)
    print(f"💵 Initial:      ${INITIAL_CAPITAL}")
    print(f"💰 Final Wealth: ${balance:,.2f}")
    print(f"🚀 Total ROI:    {roi:,.2f}%")
    print(f"🎯 Total Shots:  {trade_count}")
    print("="*80)

if __name__ == "__main__":
    run_sniper_backtest()