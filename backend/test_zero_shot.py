"""
Zero-Shot Generalization Test
Tests Proteus AI on an asset it was NEVER trained on.
"""

import pandas as pd
from strategies import get_strategy
from utils.data_loader import fetch_crypto, fetch_macro_data, merge_data
import warnings

warnings.filterwarnings('ignore')

# 1. Source Model (The "Brain")
SOURCE_MODEL_DIR = "data/proteus_BTC_USDT_unified"
SOURCE_NAME = "BTC Master Brain"

# 2. Target Market (The "Unknown")
TARGET_SYMBOL = "LTC/USDT" 
TEST_START_DATE = "2025-01-01"
TEST_END_DATE = "2025-12-31"
INITIAL_CAPITAL = 1000.0

def run_zero_shot():
    print("\n" + "="*70)
    print(f"🧬 ZERO-SHOT GENERALIZATION TEST")
    print(f"🧠 Brain: {SOURCE_NAME} (Trained on BTC)")
    print(f"🌍 World: {TARGET_SYMBOL} (Never seen before)")
    print("="*70)

    # 1. Fetch Data
    print(f"[*] Fetching Data for {TARGET_SYMBOL}...")
    crypto_df = fetch_crypto(TARGET_SYMBOL)
    macro_df = fetch_macro_data()
    
    if crypto_df is None or macro_df is None:
        print("Error fetching data.")
        return

    full_df = merge_data(crypto_df, macro_df)
    
    # 2. Load PRE-TRAINED Strategy
    # We point model_dir to the BTC folder
    # We do NOT call train_all()
    print(f"[*] Loading Pre-trained Model from: {SOURCE_MODEL_DIR}")
    strategy = get_strategy("proteus", {"model_dir": SOURCE_MODEL_DIR})
    
    # Check if loaded
    # Accessing private attrs for verification (don't do this in prod)
    loaded_modes = [m for m, loaded in strategy.is_trained.items() if loaded]
    print(f"  -> Loaded Modes: {loaded_modes}")
    
    if not loaded_modes:
        print("  [!] Error: No pre-trained models found! Run run_backtest.py first to train BTC.")
        return

    # 3. Execution Loop
    mask = (full_df['date'] >= TEST_START_DATE) & (full_df['date'] <= TEST_END_DATE)
    test_df = full_df[mask].copy().reset_index(drop=True)
    
    position = 0
    capital = INITIAL_CAPITAL
    trades = 0
    wins = 0
    
    print(f"[*] Running Simulation on {len(test_df)} days...")
    
    for i in range(20, len(test_df)):
        current_date_val = test_df.iloc[i]['date']
        window = full_df[full_df['date'] <= current_date_val]
        
        # Predict using BTC logic on LTC data
        result = strategy.analyze(window)
        signal = result.get('signal', 'NEUTRAL')
        price = test_df.iloc[i]['close']
        
        if signal == "BUY" and position == 0:
            position = capital / price
            capital = 0
            trades += 1
            entry_price = price
            
        elif signal == "SELL" and position > 0:
            capital = position * price
            if price > entry_price: wins += 1
            position = 0
            
    if position > 0:
        capital = position * test_df.iloc[-1]['close']
        
    roi = ((capital - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100
    profit = capital - INITIAL_CAPITAL
    win_rate = (wins / trades * 100) if trades > 0 else 0
    
    print("\n" + "-"*70)
    print(f"RESULT: {TARGET_SYMBOL} using BTC Brain")
    print("-"*70)
    print(f"Initial: ${INITIAL_CAPITAL}")
    print(f"Final:   ${capital:.2f}")
    print(f"Profit:  ${profit:.2f}")
    print(f"ROI:     {roi:.2f}%")
    print(f"Trades:  {trades}")
    print(f"WinRate: {win_rate:.1f}%")
    print("="*70)

if __name__ == "__main__":
    run_zero_shot()
