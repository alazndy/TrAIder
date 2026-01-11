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
        import os
        import json
        
        cred = None
        
        # 1. Try Environment Variable (Render / Cloud)
        env_creds = os.environ.get("FIREBASE_CREDENTIALS_JSON")
        if env_creds:
            try:
                # Handle potential quoting issues in env vars
                if env_creds.startswith("'") and env_creds.endswith("'"):
                    env_creds = env_creds[1:-1]
                
                cred_dict = json.loads(env_creds)
                cred = credentials.Certificate(cred_dict)
                print("[+] Firebase initialized with FIREBASE_CREDENTIALS_JSON env var.")
            except Exception as e:
                print(f"[!] Error parsing FIREBASE_CREDENTIALS_JSON: {e}")

        # 2. Try Local File
        if not cred:
            if os.path.exists("serviceAccountKey.json"):
                cred_path = "serviceAccountKey.json"
            elif os.path.exists("backend/serviceAccountKey.json"):
                cred_path = "backend/serviceAccountKey.json"
            else:
                cred_path = None
                
            if cred_path:
                cred = credentials.Certificate(cred_path)
                print(f"[+] Firebase initialized with file: {cred_path}")

        # 3. Initialize App
        if cred:
            firebase_admin.initialize_app(cred, {
                'storageBucket': 'tr-ai-der.firebasestorage.app'
            })
        else:
            # Fallback to default credentials (GCP Cloud Run / Functions)
            firebase_admin.initialize_app(options={
                'storageBucket': 'tr-ai-der.firebasestorage.app'
            })
            print("[+] Firebase initialized with default credentials (GCP environment detected).")
            
    except Exception as e:
        print(f"[!] Firebase initialization failed: {e}")

# Import download_models (after firebase init to ensure app exists)
try:
    from download_models import download_models
except ImportError:
    # Handle both root and backend execution contexts
    try:
        from backend.download_models import download_models
    except ImportError:
        pass

def get_data_dir():
    """Get the correct data directory path"""
    import os
    if os.path.exists("data"):
        return "data"
    elif os.path.exists("backend/data"):
        return "backend/data"
    return "data"  # Default fallback

DATA_DIR = get_data_dir()
LAST_REPORT_TIME = time.time()

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
    print("INITIALIZING & TRAINING MODELS FOR PAPER TRADING")
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
    from portfolio_manager import get_portfolio_manager
    
    print("\n" + "="*60)
    print(f"PAPER TRADING LIVE START: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Initialize portfolio manager
    pm = get_portfolio_manager()
    portfolio_stats = pm.get_stats()
    print(f"[PORTFOLIO] Balance: ${portfolio_stats['balance']:.2f} | Trades: {portfolio_stats['total_trades']} | Win Rate: {portfolio_stats['win_rate']:.1f}%")
    
    macro_df = fetch_macro_data() # Refresh macro once per cycle
    
    current_prices = {}
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
        # Use simple string concatenation or path join relative to DATA_DIR
        import os
        model_dir = os.path.join(DATA_DIR, f"paper_{strat_name}_{sym.replace('/', '_')}")
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
        
        current_prices[sym] = price
        
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
        
        # 4. Execute Paper Trade
        pm.execute_trade(sym, signal, price, conf)
        
    # Save portfolio snapshot
    if current_prices:
        pm.save_snapshot(current_prices)
    
    # Send Heartbeat / System Log
    try:
        log_msg = f"Scan complete. {len(signals)} opportunities found. Portfolio: ${portfolio_stats['balance']:.0f}"
        heartbeat = {
            "symbol": "SYSTEM",
            "strategy": "HEARTBEAT",
            "signal": "INFO",
            "confidence": 100.0,
            "price": 0.0,
            "mode": "system",
            "desc": log_msg,
            "is_paper": True,
            "timestamp": firestore.SERVER_TIMESTAMP,
            "created_at": datetime.now()
        }
        db = firestore.client()
        db.collection('signals').add(heartbeat)
        print(f"  [Heartbeat] {log_msg}")
    except Exception as e:
        print(f"  [!] Heartbeat failed: {e}")

    # Check for Hourly Report (Every 60 mins)
    global LAST_REPORT_TIME
    if time.time() - LAST_REPORT_TIME >= 3600:
        try:
            report_msg = f"Hourly Report: Profit ${portfolio_stats['total_profit']:.2f} | Trades: {portfolio_stats['total_trades']} | Balance: ${portfolio_stats['balance']:.2f}"
            hourly_signal = {
                "symbol": "SYSTEM",
                "strategy": "HOURLY_REPORT",
                "signal": "INFO", 
                "confidence": 100.0,
                "price": 0.0,
                "mode": "system",
                "desc": report_msg,
                "is_paper": True,
                "timestamp": firestore.SERVER_TIMESTAMP,
                "created_at": datetime.now()
            }
            db.collection('signals').add(hourly_signal)
            print(f"  [Report] {report_msg}")
            LAST_REPORT_TIME = time.time()
        except Exception as e:
            print(f"  [!] Hourly Report Failed: {e}")

    print("-" * 60)

    print("Waiting for next cycle...")

if __name__ == "__main__":
    # Ensure models are present (for Cloud Run / Fresh Env)
    print("[*] Checking for models...")
    try:
        download_models()
    except Exception as e:
        print(f"[!] Warning: Model download failed (Active models might be missing): {e}")


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
