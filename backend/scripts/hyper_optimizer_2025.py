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

def run_optimization():
    print("="*80)
    print(f"🧬 OMEGA HYPER-OPTIMIZER - SEARCHING FOR THE WINNING RULESET")
    print(f"📅 Test Period: 2025 Full Year | 🧪 Iterations: 10")
    print("="*80)

    model = xgb.XGBClassifier()
    model.load_model(MODEL_PATH)
    
    csv_files = [f for f in glob.glob(os.path.join(DATA_DIR, "*_USDT_1h.csv"))]
    assets_data = {}
    
    print(f"[*] Pre-loading {len(csv_files)} assets into memory...")
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
        df['volatility_index'] = df['close'].rolling(20).std() / df['close'].rolling(20).mean() * 100
        assets_data[symbol] = df[df.index >= START_DATE]

    master_timeline = pd.to_datetime(sorted(list(set().union(*[df.index for df in assets_data.values()]))))

    iterations = [
        {"conf": 0.75, "vol": 1.0, "exit": 0.45, "name": "Aggressive Hunter"},
        {"conf": 0.80, "vol": 1.2, "exit": 0.48, "name": "Balanced Sniper"},
        {"conf": 0.82, "vol": 1.5, "exit": 0.50, "name": "Patient Sniper"},
        {"conf": 0.85, "vol": 1.8, "exit": 0.52, "name": "Elite Sniper"},
        {"conf": 0.88, "vol": 2.0, "exit": 0.55, "name": "Perfect Sniper"},
        {"conf": 0.70, "vol": 0.5, "exit": 0.40, "name": "Market Scalper"},
        {"conf": 0.82, "vol": 1.0, "exit": 0.45, "name": "Optimized Mix A"},
        {"conf": 0.78, "vol": 1.5, "exit": 0.48, "name": "Optimized Mix B"},
        {"conf": 0.84, "vol": 1.2, "exit": 0.50, "name": "Optimized Mix C"},
        {"conf": 0.90, "vol": 2.5, "exit": 0.60, "name": "Ultra Conservative"}
    ]

    all_results = []
    for i, rs in enumerate(iterations):
        print(f"[*] Iteration {i+1}/10: {rs['name']}...")
        bal, current, units, trades = INITIAL_CAPITAL, None, 0, 0
        for ts in master_timeline:
            if current:
                if ts in assets_data[current].index:
                    if assets_data[current].loc[ts, 'prob'] < rs['exit']:
                        bal, current, units = units * assets_data[current].loc[ts, 'close'] * (1 - COMMISSION_RATE), None, 0
            if not current and bal > 10:
                best_s, max_p = None, 0
                for sym, df in assets_data.items():
                    if ts not in df.index: continue
                    r = df.loc[ts]
                    if r['prob'] > rs['conf'] and r['volatility_index'] > rs['vol'] and r['whale'] == 1:
                        if r['prob'] > max_p: max_p, best_s = r['prob'], sym
                if best_s:
                    units = (bal * (1 - COMMISSION_RATE)) / assets_data[best_s].loc[ts, 'close']
                    bal, current, trades = 0, best_s, trades + 1
        if current: bal = units * assets_data[current].iloc[-1]['close']
        all_results.append({"name": rs['name'], "conf": rs['conf'], "vol": rs['vol'], "exit": rs['exit'], "roi": (bal-1000)/10, "trades": trades})

    res_df = pd.DataFrame(all_results).sort_values('roi', ascending=False)
    print("\n" + "="*80)
    print(f"🏆 HYPER-OPTIMIZATION WINNER")
    print("="*80)
    w = res_df.iloc[0]
    print(f"🥇 Name: {w['name']} | ROI: %{w['roi']:,.2f} | Trades: {w['trades']}")
    print(f"⚙️ Ruleset: Conf {w['conf']} | Vol {w['vol']} | Exit {w['exit']}")
    print("-" * 80)
    print(res_df[['name', 'roi', 'trades']])
    print("="*80)

if __name__ == "__main__":
    run_optimization()