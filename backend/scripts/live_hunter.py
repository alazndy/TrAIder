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
from strategies.proteus_neo import ProteusNeo

# Configuration
STATE_FILE = "hunter_state.json"
MODEL_DIR = "../data/proteus_neo"
INITIAL_CAPITAL = 10.0

# Assets to Hunt
CRYPTO_SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT',
    'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT', 'DOT/USDT', 'TRX/USDT',
    'LINK/USDT', 'MATIC/USDT', 'LTC/USDT', 'SHIB/USDT', 'UNI/USDT'
]

STOCK_SYMBOLS = {
    'THYAO.IS': 'THY', 'GARAN.IS': 'Garanti', 
    'AAPL': 'Apple', 'TSLA': 'Tesla', 'NVDA': 'Nvidia', 'BABA': 'Alibaba'
}

class LiveHunter:
    def __init__(self):
        self.strategy = ProteusNeo({"model_dir": MODEL_DIR})
        self.exchange = ccxt.binance()
        self.load_state()
        
    def load_state(self):
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                self.state = json.load(f)
            print(f"[*] State Loaded. Balance: ${self.state['balance']:.2f} | Asset: {self.state['current_asset']}")
        else:
            self.state = {
                "balance": INITIAL_CAPITAL,
                "current_asset": None,
                "units": 0,
                "entry_price": 0,
                "history": []
            }
            print(f"[*] New Hunter Started. Budget: ${INITIAL_CAPITAL}")

    def save_state(self):
        with open(STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=4)

    def fetch_live_data(self, symbol, is_crypto):
        try:
            if is_crypto:
                ohlcv = self.exchange.fetch_ohlcv(symbol, '1h', limit=100)
                df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            else:
                # yfinance live fetch
                df = yf.download(symbol, period="5d", interval="1h", progress=False)
                if df.empty: return None
                df = df.reset_index()
                # Fix columns
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df.columns = [c.lower() for c in df.columns]
                # Fix Close column if 'adj close' exists? Just use Close.
                df = df[['close', 'volume']].copy() # Minimal needed
                
            return df
        except Exception as e:
            # print(f"  [!] Error fetching {symbol}: {e}")
            return None

    def analyze_asset(self, df, is_crypto):
        # 1. Indicators
        df['rsi'] = RSIIndicator(df['close']).rsi()
        df['sma_ratio'] = df['close'].rolling(10).mean() / df['close'].rolling(30).mean()
        df = df.fillna(0)
        
        # 2. Mode
        current = df.iloc[-1]
        trend = df['close'].pct_change(20).iloc[-1] * 100
        vol = (df['close'].rolling(20).std() / df['close'].rolling(20).mean() * 100).iloc[-1]
        
        t_thresh = 0.5 if not is_crypto else 1.0
        v_thresh = 1.0 if not is_crypto else 2.0
        
        mode = "sideways"
        if trend > t_thresh and vol < v_thresh: mode = "bull"
        elif trend < -t_thresh and vol < v_thresh: mode = "bear"
        
        # 3. Predict
        if self.strategy.models[mode]:
            # XGBoost expects 2D array
            X = pd.DataFrame([[current['rsi'], current['sma_ratio']]], columns=['rsi', 'sma_ratio'])
            pred = self.strategy.models[mode].predict(X)[0]
            # Map: 1 -> BUY, 0 -> SELL (approx)
            return 1 if pred == 1 else -1, current['close']
            
        return 0, current['close']

    def hunt(self):
        print("\n" + "="*60)
        print(f"🦅 GLOBAL HUNTER SCAN | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("="*60)
        
        best_opportunity = None
        
        # 1. Check Current Position (Exit?)
        if self.state['current_asset']:
            symbol = self.state['current_asset']
            is_crypto = "USDT" in symbol
            print(f"[*] Checking Holding: {symbol}...")
            
            df = self.fetch_live_data(symbol, is_crypto)
            if df is not None:
                signal, price = self.analyze_asset(df, is_crypto)
                
                # Dynamic PnL
                current_value = self.state['units'] * price
                roi = (current_value - self.state['balance']) / self.state['balance'] * 100 if self.state['balance'] > 0 else 0
                print(f"  -> Current Price: ${price:.2f} | Value: ${current_value:.2f} ({roi:+.2f}%)")
                
                if signal == -1:
                    print(f"  🚨 SELL SIGNAL DETECTED! Liquidation initiated.")
                    self.state['balance'] = current_value
                    self.state['history'].append(f"SOLD {symbol} at ${price:.2f} (+{roi:.1f}%)")
                    self.state['current_asset'] = None
                    self.state['units'] = 0
                    self.save_state()
                else:
                    print(f"  🔒 HOLDING STRONG.")
                    return # Stay in position, don't look for new ones
            else:
                print("  [!] Market Closed or No Data. Holding.")
                return

        # 2. Scan for New Opportunities (If Cash)
        if not self.state['current_asset']:
            print("[*] Scanning Market for Prey...")
            candidates = []
            
            # Combine Lists
            all_assets = [(s, True) for s in CRYPTO_SYMBOLS] + [(s, False) for s in STOCK_SYMBOLS.keys()]
            
            for symbol, is_crypto in all_assets:
                df = self.fetch_live_data(symbol, is_crypto)
                if df is None or len(df) < 30: continue
                
                signal, price = self.analyze_asset(df, is_crypto)
                
                if signal == 1:
                    print(f"  Found Opportunity: {symbol} at ${price:.2f}")
                    # In a real engine, we might score them confidence.
                    # Here we take the first/best logic from backtest.
                    self.state['current_asset'] = symbol
                    self.state['entry_price'] = price
                    self.state['units'] = self.state['balance'] / price
                    
                    print(f"  🎯 SNIPER SHOT! Buying {symbol}...")
                    self.state['history'].append(f"BOUGHT {symbol} at ${price:.2f}")
                    self.save_state()
                    return

            print("  💤 No suitable prey found. Waiting...")

if __name__ == "__main__":
    hunter = LiveHunter()
    while True:
        try:
            hunter.hunt()
            print("[*] Sleeping for 60 minutes...")
            time.sleep(3600) # Run every hour
        except KeyboardInterrupt:
            print("\n🛑 Hunter stopped.")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)