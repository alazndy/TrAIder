"""
PAPER TRADER ENGINE
Executes the 'Golden List' portfolio in live/simulation mode.
"""

import time
import argparse
import pandas as pd
from datetime import datetime
from paper_config import PAPER_PORTFOLIO, CAPITAL_PER_ASSET
from strategies import get_strategy
from utils.data_loader import fetch_crypto, fetch_macro_data, merge_data
import warnings
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase (Check if already initialized)
if not firebase_admin._apps:
    try:
        # Auto-discovery for Cloud Run or local GOOGLE_APPLICATION_CREDENTIALS
        firebase_admin.initialize_app(options={
            'storageBucket': 'tr-ai-der.firebasestorage.app'
        })
        print("[+] Firebase initialized successfully.")
    except Exception as e:
        print(f"[!] Firebase initialization failed: {e}")

warnings.filterwarnings('ignore')

def save_signal_to_db(signal_data):
    """Save signal to Firestore"""
    try:
        db = firestore.client()
        # Add timestamp to record
        signal_data['timestamp'] = firestore.SERVER_TIMESTAMP
        signal_data['created_at'] = datetime.now()
        
        # Collection: signals
        db.collection('signals').add(signal_data)
        # print("  [Cloud] Signal saved.")
    except Exception as e:
        print(f"  [!] DB Error: {e}")

def train_models():
    print("\n" + "="*60)
    print("🚂 INITIALIZING & TRAINING MODELS FOR PAPER TRADING")
    print("="*60)
    
    macro_df = fetch_macro_data()
    
    for item in PAPER_PORTFOLIO:
        sym = item['symbol']
        strat_name = item['strategy']
        print(f"\n[*] Processing {sym} ({strat_name})...")
        
        crypto_df = fetch_crypto(sym)
        if crypto_df is None: continue
        
        full_df = merge_data(crypto_df, macro_df)
        
        # Init & Train
        model_dir = f"data/paper_{strat_name}_{sym.replace('/', '_')}"
        strategy = get_strategy(strat_name, {"model_dir": model_dir})
        
        strategy.train_all(full_df)
        print(f"  -> Model trained and saved to {model_dir}")

    print("\n[+] All systems ready. Run with --live to start trading.")

def run_live_cycle():
    print("\n" + "="*60)
    print(f"📡 PAPER TRADING LIVE START: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    macro_df = fetch_macro_data() # Refresh macro once per cycle
    
    portfolio_value = 0
    signals = []
    
    for item in PAPER_PORTFOLIO:
        sym = item['symbol']
        strat_name = item['strategy']
        desc = item['desc']
        
        # 1. Fetch Real-time Data (Simulated via OHLCV for now)
        # In real prod, this would hit specific 'ticker' endpoint
        crypto_df = fetch_crypto(sym)
        if crypto_df is None: continue
        
        full_df = merge_data(crypto_df, macro_df)
        
        # 2. Load Model
        model_dir = f"data/paper_{strat_name}_{sym.replace('/', '_')}"
        strategy = get_strategy(strat_name, {"model_dir": model_dir})
        
        # Check if model exists/trained
        # Accessing internal dict just to check
        if not any(strategy.is_trained.values()):
             print(f"  [!] Model for {sym} not found. Skipping.")
             continue
             
        # 3. Predict (Live Candle)
        # We pass the full history up to NOW
        result = strategy.analyze(full_df)
        
        signal = result.get('signal', 'NEUTRAL')
        conf = result.get('confidence', 0)
        mode = result.get('mode', 'unknown')
        price = full_df['close'].iloc[-1]
        
        # Log
        print(f"  {sym:<10} | {strat_name:<11} | {signal:<6} ({conf:>5.1f}%) | ${price:<8.4f} | {desc}")
        
        signal_record = {
            "symbol": sym,
            "strategy": strat_name,
            "signal": signal,
            "confidence": float(conf),
            "price": float(price),
            "mode": mode,
            "desc": desc,
            "is_paper": True
        }
        
        signals.append(signal_record)
        save_signal_to_db(signal_record)
        
    print("-" * 60)
    print("Waiting for next cycle...")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true", help="Train models first")
    parser.add_argument("--live", action="store_true", help="Start infinite live loop")
    parser.add_argument("--run-once", action="store_true", help="Run a single cycle and exit (For Cloud Scheduler)")
    args = parser.parse_args()
    
    if args.train:
        train_models()
        
    if args.live:
        print("[*] Starting Live Trader (Infinite Loop)...")
        while True:
            try:
                run_live_cycle()
                # Run every 60 seconds (for testing). In prod, maybe 15 mins.
                time.sleep(60) 
            except KeyboardInterrupt:
                print("\n[!] Stopping Trader.")
                break
            except Exception as e:
                print(f"[!] Critical Error: {e}")
                time.sleep(10)

    if args.run_once:
        print("[*] Starting Live Trader (Single Execution)...")
        try:
            run_live_cycle()
            print("[+] Cycle Complete. Exiting.")
        except Exception as e:
            print(f"[!] Critical Error: {e}")
            exit(1)
