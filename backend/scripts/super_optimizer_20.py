import sys
import os
import glob
import pandas as pd
import numpy as np
import xgboost as xgb
from datetime import datetime
import warnings

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.event_calendar import event_engine

warnings.filterwarnings('ignore')

DATA_DIR = '../data/raw'
MODEL_PATH = '../data/proteus_omega/omega_brain.json'
START_DATE = '2025-01-01'
INITIAL_CAPITAL = 1000.0
COMMISSION_RATE = 0.001

def run_super_optimization():
    print("="*80)
    print(f"🚀 OMEGA SUPER-OPTIMIZER - 20 ITERATION BLITZ")
    print(f"💰 Searching for the 'Holy Grail' of 2025...")
    print("="*80)

    model = xgb.XGBClassifier()
    model.load_model(MODEL_PATH)
    
    csv_files = [f for f in glob.glob(os.path.join(DATA_DIR, "*_USDT_1h.csv"))]
    assets_data = {}
    
    print(f"[*] Pre-loading {len(csv_files)} assets into high-speed memory...")
    for f in csv_files:
        symbol = os.path.basename(f).replace("_1h.csv", "")
        df = pd.read_csv(f)
        df['date'] = pd.to_datetime(df['time'], unit='ms')
        df = df[df['date'] >= '2024-12-01'].set_index('date').sort_index()
        df['rsi'] = (df['close'].diff().apply(lambda x: max(x,0)).rolling(14).mean() / 
                     df['close'].diff().apply(lambda x: abs(x)).rolling(14).mean() * 100).fillna(50)
        df['micro_vol'] = df['close'].rolling(4).std().fillna(0)
        df['macro_trend'] = df['close'].rolling(24).mean().fillna(df['close'])
        df['whale'] = (df['volume'] > df['volume'].rolling(24).mean() * 2.5).astype(int)
        df['net_flow'] = (df['close'] - df['open']) * df['whale']
        ev = event_engine.get_event_features(df.index)
        df = pd.concat([df, ev], axis=1)
        feats = ['rsi', 'micro_vol', 'macro_trend', 'whale', 'net_flow'] + [col for col in df.columns if 'event_' in col]
        df['prob'] = model.predict_proba(df[feats])[:, 1]
        df['vol_idx'] = df['close'].rolling(20).std() / df['close'].rolling(20).mean() * 100
        assets_data[symbol] = df[df.index >= START_DATE]

    master_timeline = pd.to_datetime(sorted(list(set().union(*[df.index for df in assets_data.values()]))))

    dna_grid = []
    for c in [0.70, 0.75, 0.80, 0.85]:
        for v in [0.5, 1.2, 2.0]:
            for ts in [0.03, 0.05]:
                dna_grid.append({"conf": c, "vol": v, "trailing": ts, "long_only": True})
    
    dna_grid.append({"conf": 0.82, "vol": 1.5, "trailing": 0.04, "long_only": False})
    dna_grid.append({"conf": 0.78, "vol": 1.0, "trailing": 0.03, "long_only": False})
    dna_grid = dna_grid[:20]

    all_results = []
    for idx, dna in enumerate(dna_grid):
        name = f"DNA_{idx+1}"
        print(f"[*] Testing {name}...", end="\r")
        bal, slots, active_pos, trades = INITIAL_CAPITAL, 3, {}, 0
        for ts in master_timeline:
            to_close = []
            for sym, pos in active_pos.items():
                if ts in assets_data[sym].index:
                    row = assets_data[sym].loc[ts]
                    p, prob = row['close'], row['prob']
                    pnl = (p - pos['entry'])/pos['entry'] if pos['type'] == 'long' else (pos['entry'] - p)/pos['entry']
                    if pos['type'] == 'long':
                        pos['hi'] = max(pos['hi'], p)
                        if p < pos['hi'] * (1 - dna['trailing']) or prob < 0.48:
                            bal += pos['size'] * (1 + pnl) * (1 - COMMISSION_RATE)
                            to_close.append(sym)
                            trades += 1
                    else:
                        pos['lo'] = min(pos['lo'], p)
                        if p > pos['lo'] * (1 + dna['trailing']) or prob > 0.52:
                            bal += pos['size'] * (1 + pnl) * (1 - COMMISSION_RATE)
                            to_close.append(sym)
                            trades += 1
            for s in to_close: del active_pos[s]

            if len(active_pos) < slots and bal > 50:
                slot_size = bal / (slots - len(active_pos))
                best_s, best_t, max_p = None, None, 0
                for sym, df in assets_data.items():
                    if sym in active_pos or ts not in df.index: continue
                    r = df.loc[ts]
                    if r['prob'] > dna['conf'] and r['vol_idx'] > dna['vol'] and r['whale'] == 1:
                        if r['prob'] > max_p: max_p, best_s, best_t = r['prob'], sym, 'long'
                    elif not dna['long_only'] and r['prob'] < (1 - dna['conf']) and r['vol_idx'] > dna['vol'] and r['whale'] == 1:
                        if (1 - r['prob']) > max_p: max_p, best_s, best_t = (1 - r['prob']), sym, 'short'
                if best_s:
                    active_pos[best_s] = {'type': best_t, 'entry': assets_data[best_s].loc[ts, 'close'], 'hi': assets_data[best_s].loc[ts, 'close'], 'lo': assets_data[best_s].loc[ts, 'close'], 'size': slot_size}
                    bal -= slot_size

        for s, pos in active_pos.items():
            p = assets_data[s].iloc[-1]['close']
            pnl = (p - pos['entry'])/pos['entry'] if pos['type'] == 'long' else (pos['entry'] - p)/pos['entry']
            bal += pos['size'] * (1 + pnl)
        all_results.append({"name": name, "roi": (bal-1000)/10, "trades": trades, "dna": dna})

    res_df = pd.DataFrame(all_results).sort_values('roi', ascending=False)
    print("\n" + "="*80)
    print(f"🏆 OMEGA EVOLUTION WINNER")
    print("="*80)
    best = res_df.iloc[0]
    print(f"🥇 Name: {best['name']} | ROI: %{best['roi']:,.2f} | Trades: {best['trades']}")
    print(f"⚙️ DNA: {best['dna']}")
    print("-" * 80)
    print(res_df[['name', 'roi', 'trades']].head(10))
    print("="*80)

if __name__ == "__main__":
    run_super_optimization()