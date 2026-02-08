
import sys
import os
import json
import time
import pandas as pd
import numpy as np
import ccxt
import yfinance as yf
from datetime import datetime
from ta.momentum import RSIIndicator

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.order_flow_service import order_flow_engine

# Check for GPU
try:
    import xgboost as xgb
    try:
        tmp = xgb.XGBClassifier(device='cuda')
        GPU_AVAILABLE = True
    except:
        GPU_AVAILABLE = False
except:
    print("[!] XGBoost error")
    sys.exit(1)

# --- THE "PERFECT" SETTINGS ---
CONFIDENCE_THRESHOLD = 0.88  # Ultra-High Precision
STATE_FILE = "hunter_state.json"
MODEL_PATH = "../data/proteus_omega/omega_brain.json"
TARGETS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'NVDA']
INITIAL_CAPITAL = 1000.0
COMMISSION_RATE = 0.001

class PerfectSniperLive:
    def __init__(self):
        self.load_brain()
        self.exchange = ccxt.binance()
        self.load_state()
        
    def load_brain(self):
        print(f"[*] Initializing Omega Brain (Device: {'GPU' if GPU_AVAILABLE else 'CPU'})...")
        self.model = xgb.XGBClassifier(device='cuda' if GPU_AVAILABLE else 'cpu')
        self.model.load_model(MODEL_PATH)

    def load_state(self):
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                self.state = json.load(f)
        else:
            self.state = {"balance": INITIAL_CAPITAL, "current_asset": None, "units": 0, "entry": 0}

    def save_state(self):
        with open(STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=4)

    def analyze(self, sym):
        is_crypto = "USDT" in sym
        try:
            if is_crypto:
                ohlcv = self.exchange.fetch_ohlcv(sym, '1h', limit=100)
                df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            else:
                df = yf.download(sym, period="5d", interval="1h", progress=False)
                df = df.reset_index()
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                df.columns = [str(c).lower() for c in df.columns]
                df = df[['close', 'volume']]

            df['rsi'] = RSIIndicator(df['close']).rsi().fillna(50)
            df['macro_trend'] = df['close'].rolling(24).mean().fillna(df['close'])
            df['micro_vol'] = df['close'].rolling(4).std().fillna(0)
            df['whale'] = (df['volume'] > df['volume'].rolling(24).mean() * 2.5).astype(int)
            df['net_flow'] = (df['close'] - df['open']) * df['whale'] if is_crypto else 0
            
            # Prepare Input (13-Dim placeholder matches training)
            X = pd.DataFrame([[df['rsi'].iloc[-1], df['micro_vol'].iloc[-1], df['macro_trend'].iloc[-1], 
                               df['whale'].iloc[-1], df['net_flow'].iloc[-1] if is_crypto else 0,
                               0, 0, 0, 0, 0, 0, 0, 0]], 
                             columns=['rsi', 'micro_vol', 'macro_trend', 'whale_activity', 'net_flow_proxy', 
                                      'event_HALVING', 'event_PANDEMIC_CRASH', 'event_COINBASE_IPO', 
                                      'event_LUNA_CRASH', 'event_FTX_CRASH', 'event_BTC_ETF_APPROVAL', 
                                      'event_FED_RATE_HIKE_START', 'event_FED_RATE_CUT_START'])
            
            prob = self.model.predict_proba(X)[:, 1][0]
            return prob, df['close'].iloc[-1], df['whale'].iloc[-1]
        except:
            return 0.5, 0, 0

    def tick(self):
        print(f"\n[🎯] SNIPER TICK | {datetime.now().strftime('%H:%M:%S')}")
        
        # 1. Position Check
        if self.state['current_asset']:
            sym = self.state['current_asset']
            prob, price, _ = self.analyze(sym)
            pnl = (price - self.state['entry']) / self.state['entry'] * 100
            print(f"  Pusudayız: {sym} | PnL: {pnl:+.2f}% | AI Güven: {prob:.2f}")
            
            # EXIT if signal turns sour
            if prob < 0.45:
                self.state['balance'] = self.state['units'] * price * (1 - COMMISSION_RATE)
                print(f"  🚨 SİNYAL BOZULDU! {sym} satıldı. Final: ${self.state['balance']:.2f}")
                self.state['current_asset'] = None
                self.save_state()
            return

        # 2. Hunt Mode (If balance > 0)
        print(f"  Piyasalar taranıyor (Eşik: %{CONFIDENCE_THRESHOLD*100})...")
        for sym in TARGETS:
            prob, price, whale = self.analyze(sym)
            if prob > CONFIDENCE_THRESHOLD and whale == 1:
                print(f"  🎯 HEDEF KİLİTLENDİ! {sym} | Güven: {prob:.2%}")
                # ALL-IN EXECUTION
                self.state['units'] = (self.state['balance'] * (1 - COMMISSION_RATE)) / price
                self.state['entry'] = price
                self.state['current_asset'] = sym
                self.state['balance'] = 0
                print(f"  🔥 ATEŞ EDİLDİ! {sym} alındı.")
                self.save_state()
                break

if __name__ == "__main__":
    sniper = PerfectSniperLive()
    while True:
        try:
            sniper.tick()
            time.sleep(3600) # Her saat başı 1 kontrol
        except KeyboardInterrupt: break
        except Exception as e:
            print(f"Hata: {e}")
            time.sleep(60)
