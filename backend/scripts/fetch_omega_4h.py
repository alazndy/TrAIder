
import ccxt
import pandas as pd
import os
import time
from datetime import datetime, timedelta

DATA_DIR = '../data/omega_4h'
SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'SHIB/USDT', 'LINK/USDT', 'MATIC/USDT', 'AVAX/USDT', 'DOT/USDT', 'TRX/USDT', 'UNI/USDT', 'BNB/USDT', 'LTC/USDT']

def fetch_omega_4h():
    if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
    exchange = ccxt.binance()
    
    print("="*60)
    print("🌊 OMEGA SWING (4H) - DATA ACQUISITION")
    print("="*60)

    for symbol in SYMBOLS:
        print(f"[*] Fetching {symbol} 4h data...")
        since = exchange.parse8601('2019-01-01T00:00:00Z')
        all_ohlcv = []
        
        while True:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, '4h', since=since, limit=1000)
                if not ohlcv: break
                all_ohlcv.extend(ohlcv)
                since = ohlcv[-1][0] + 1
                if len(ohlcv) < 1000: break
                time.sleep(0.1)
            except: break
            
        df = pd.DataFrame(all_ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        safe_symbol = symbol.replace('/', '_')
        df.to_csv(os.path.join(DATA_DIR, f"{safe_symbol}_4h.csv"), index=False)
        print(f"  -> Saved {len(df)} candles.")

if __name__ == "__main__":
    fetch_omega_4h()
