"""
Benchmark Training Script - All Models
Trains and times AdaptiveAI and ProteusNeo with 15 years of data.
"""

import sys
import os
import time
import glob
import pandas as pd
import numpy as np

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strategies.adaptive_ai import AdaptiveAIStrategy
from strategies.proteus_neo import ProteusNeo

# Use absolute path (relative to repo root)
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'raw')
RESULTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

def count_samples(file_path):
    """Count rows in CSV without loading it fully."""
    with open(file_path, 'r') as f:
        return sum(1 for _ in f) - 1  # Minus header

def benchmark():
    print("=" * 70)
    print("🚀 MODEL TRAINING BENCHMARK - 15 YEARS DATA")
    print("=" * 70)
    
    csv_files = sorted(glob.glob(os.path.join(DATA_DIR, "*_1h.csv")))
    
    if not csv_files:
        print(f"[ERROR] No CSV files found in {DATA_DIR}")
        return
    
    # Summary
    total_samples = 0
    for f in csv_files:
        samples = count_samples(f)
        total_samples += samples
        symbol = os.path.basename(f).replace("_1h.csv", "")
        print(f"  📊 {symbol}: {samples:,} candles")
    
    print(f"\n  📈 TOTAL: {total_samples:,} hourly candles across {len(csv_files)} coins\n")
    
    # Load & Merge all data
    print("[*] Loading all data...")
    load_start = time.time()
    all_dfs = []
    for f in csv_files:
        df = pd.read_csv(f)
        df['symbol'] = os.path.basename(f).replace("_1h.csv", "")
        all_dfs.append(df)
    
    merged = pd.concat(all_dfs, ignore_index=True)
    load_time = time.time() - load_start
    print(f"    ✅ Loaded {len(merged):,} rows in {load_time:.2f}s\n")
    
    results = []
    
    # =========== BENCHMARK 1: AdaptiveAI (Sklearn) ===========
    print("[BENCHMARK 1] AdaptiveAI (RandomForest/GradientBoosting)")
    print("-" * 50)
    
    adaptive_model_dir = os.path.join(RESULTS_DIR, 'benchmark_adaptive_ai')
    os.makedirs(adaptive_model_dir, exist_ok=True)
    
    adaptive_start = time.time()
    adaptive_ai = AdaptiveAIStrategy({"model_dir": adaptive_model_dir, "min_samples": 100})
    
    # Train on combined data (using first symbol's structure for OHLCV)
    train_df = merged[merged['symbol'] == 'BTC_USDT'].reset_index(drop=True)
    adaptive_ai.train_all(train_df)
    adaptive_time = time.time() - adaptive_start
    
    print(f"    ⏱️  AdaptiveAI Training Time: {adaptive_time:.2f} seconds ({adaptive_time/60:.2f} min)")
    results.append(("AdaptiveAI (Sklearn)", adaptive_time, len(train_df)))
    print()
    
    # =========== BENCHMARK 2: ProteusNeo (XGBoost GPU) ===========
    print("[BENCHMARK 2] ProteusNeo (XGBoost GPU)")
    print("-" * 50)
    
    proteus_model_dir = os.path.join(RESULTS_DIR, 'benchmark_proteus_neo')
    os.makedirs(proteus_model_dir, exist_ok=True)
    
    # ProteusNeo expects macro columns
    train_df['market_btc_close'] = train_df['close']
    train_df['market_btc_vol'] = train_df['volume']
    train_df['vix_close'] = 20.0
    train_df['dxy_close'] = 100.0
    train_df['eth_btc_close'] = 0.05
    
    proteus_start = time.time()
    proteus = ProteusNeo({"model_dir": proteus_model_dir, "min_samples": 100})
    proteus.train_all(train_df)
    proteus_time = time.time() - proteus_start
    
    print(f"    ⏱️  ProteusNeo Training Time: {proteus_time:.2f} seconds ({proteus_time/60:.2f} min)")
    results.append(("ProteusNeo (XGBoost)", proteus_time, len(train_df)))
    print()
    
    # =========== SUMMARY ===========
    print("=" * 70)
    print("📋 BENCHMARK RESULTS SUMMARY")
    print("=" * 70)
    print(f"{'Model':<30} {'Time (sec)':<15} {'Samples':<15}")
    print("-" * 70)
    for name, duration, samples in results:
        print(f"{name:<30} {duration:<15.2f} {samples:<15,}")
    
    print("-" * 70)
    print(f"Total Data Load Time: {load_time:.2f}s")
    print(f"Total Training Time: {sum(r[1] for r in results):.2f}s ({sum(r[1] for r in results)/60:.2f} min)")
    print("=" * 70)

if __name__ == "__main__":
    benchmark()
