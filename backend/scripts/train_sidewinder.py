import sys
import os
import glob
import json
import pandas as pd
import numpy as np
from datetime import datetime
from scipy.stats import pearsonr, spearmanr

# Granger Causality Test from statsmodels
try:
    from statsmodels.tsa.stattools import grangercausalitytests
    STATS_AVAILABLE = True
except ImportError:
    STATS_AVAILABLE = False
    print("[!] Statsmodels not found. Causality tests will be simplified.")

DATA_DIR = '../data/raw'
OUTPUT_FILE = '../data/sidewinder_map.json'
START_DATE = '2023-01-01'

def train_sidewinder():
    print("="*80)
    print(f"🐍 SIDEWINDER - CORRELATION & LEAD/LAG FINDER (DAILY)")
    print(f"📅 Training Period: {START_DATE} to Now")
    print("="*80)

    # 1. Load & Align Data
    csv_files = glob.glob(os.path.join(DATA_DIR, "*_1h.csv"))
    closes = pd.DataFrame()
    
    print(f"[*] Loading and aligning {len(csv_files)} assets...")
    
    for file_path in csv_files:
        symbol = os.path.basename(file_path).replace("_1h.csv", "")
        df = pd.read_csv(file_path)
        df['date'] = pd.to_datetime(df['time'], unit='ms')
        
        # Resample to Daily to fix overlap issues
        df = df.set_index('date').resample('1D').last()
        
        # Filter Date
        df = df[df.index >= START_DATE]
        
        if not df.empty:
            closes[symbol] = df['close']
            
    # Forward fill missing data (e.g. stock holidays) to allow correlation check
    # Then drop rows that still have NaNs (where assets didn't exist yet)
    # Finding common period
    closes = closes.ffill().dropna()
    print(f"[*] Data Matrix Shape: {closes.shape}")
    
    if closes.empty:
        print("[!] Not enough overlapping data found.")
        return

    relationships = []
    
    assets = closes.columns.tolist()
    processed = 0
    
    print("[*] Hunting for relationships (Lead/Lag Analysis)...")
    
    for lead in assets:
        for lag in assets:
            if lead == lag: continue
            
            # Simple Progress
            processed += 1
            if processed % 100 == 0:
                print(f"  -> Analyzed {processed} pairs...", end="\r")
            
            # 1. Correlation Check (Fast Filter)
            # We look for high correlation (Symbiotic) or high negative correlation (Inverse)
            try:
                corr, _ = pearsonr(closes[lead], closes[lag])
            except:
                continue
            
            if abs(corr) < 0.7: continue # Skip weak relationships
            
            # 2. Lead/Lag Analysis (Time Shifted Correlation)
            best_shift = 0
            best_shift_corr = 0
            
            # Check 1 to 4 hours delay
            for shift in range(1, 5):
                shifted_lag = closes[lag].shift(-shift) # Future lag vs Current lead
                # We need to drop NaNs created by shift
                valid_idx = shifted_lag.dropna().index.intersection(closes[lead].index)
                
                if len(valid_idx) < 100: continue
                
                try:
                    s_corr, _ = pearsonr(closes[lead].loc[valid_idx], shifted_lag.loc[valid_idx])
                    if abs(s_corr) > abs(best_shift_corr):
                        best_shift_corr = s_corr
                        best_shift = shift
                except:
                    pass
            
            if abs(best_shift_corr) > 0.75:
                # 3. Granger Causality (Scientific Proof)
                # Only if statsmodels is installed
                p_value = 0.0
                if STATS_AVAILABLE:
                    try:
                        # Test if Lead causes Lag
                        data = pd.concat([closes[lag], closes[lead]], axis=1).dropna()
                        # maxlag must be sufficient
                        test_result = grangercausalitytests(data, maxlag=[best_shift], verbose=False)
                        p_value = test_result[best_shift][0]['ssr_ftest'][1]
                    except:
                        p_value = 1.0 # Fail
                
                # If p_value < 0.05, causality is significant
                is_causal = p_value < 0.05
                
                if is_causal or not STATS_AVAILABLE:
                    relationships.append({
                        "lead": lead,
                        "lag": lag,
                        "correlation": round(best_shift_corr, 3),
                        "delay_hours": best_shift,
                        "type": "Direct" if best_shift_corr > 0 else "Inverse",
                        "strength": "High" if abs(best_shift_corr) > 0.85 else "Medium"
                    })

    # Sort by strength
    relationships.sort(key=lambda x: abs(x['correlation']), reverse=True)
    
    # Save Map
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(relationships, f, indent=4)
        
    print(f"\n✅ Sidewinder Training Complete!")
    print(f"🔗 Found {len(relationships)} predictive relationships.")
    print(f"📂 Saved to: {OUTPUT_FILE}")
    
    # Show Top 5
    print("\n🏆 TOP 5 PREDICTIVE PAIRS:")
    for r in relationships[:5]:
        arrow = "➹" if r['type'] == 'Direct' else "➷"
        print(f"  {r['lead']} {arrow} {r['lag']} (Delay: {r['delay_hours']}h, Corr: {r['correlation']})")

if __name__ == "__main__":
    train_sidewinder()