import ccxt
import pandas as pd
import os
import time
from datetime import datetime

# Configuration
EXCHANGE_ID = 'binance'
TIMEFRAME = '1h'
SINCE_DATE = '2017-01-01 00:00:00'
DATA_DIR = '../data/raw'
SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT',
    'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT', 'DOT/USDT', 'TRX/USDT',
    'LINK/USDT', 'MATIC/USDT', 'LTC/USDT', 'SHIB/USDT', 'UNI/USDT'
]

def fetch_history():
    exchange = getattr(ccxt, EXCHANGE_ID)({
        'enableRateLimit': True,
    })
    
    start_ts = exchange.parse8601(SINCE_DATE)
    
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    print(f"[*] Starting Historical Data Download from {SINCE_DATE}...")
    
    for symbol in SYMBOLS:
        safe_symbol = symbol.replace('/', '_')
        file_path = os.path.join(DATA_DIR, f"{safe_symbol}_{TIMEFRAME}.csv")
        
        # Resume capability
        if os.path.exists(file_path):
            try:
                existing_df = pd.read_csv(file_path)
                if not existing_df.empty:
                    last_time = existing_df.iloc[-1]['time']
                    current_since = int(last_time + 1)
                    print(f"  [Resume] {symbol} continuing from {datetime.fromtimestamp(current_since/1000)}")
                else:
                    current_since = start_ts
            except:
                current_since = start_ts
        else:
            current_since = start_ts
            print(f"  [New] Fetching {symbol}...")
            
        all_candles = []
        
        while True:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, since=current_since, limit=1000)
                if not ohlcv: break
                
                last_fetched_ts = ohlcv[-1][0]
                if last_fetched_ts == current_since: break
                current_since = int(last_fetched_ts + 1)
                all_candles.extend(ohlcv)
                
                print(f"    -> {symbol}: Fetched up to {datetime.fromtimestamp(last_fetched_ts/1000)}")
                
                if len(all_candles) >= 5000:
                    new_df = pd.DataFrame(all_candles, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                    if not os.path.exists(file_path):
                        new_df.to_csv(file_path, index=False)
                    else:
                        new_df.to_csv(file_path, mode='a', header=False, index=False)
                    all_candles = []
                    
                if last_fetched_ts > (time.time() * 1000) - 7200000: break
                    
            except Exception as e:
                print(f"\n    [!] Error: {e}")
                time.sleep(5)
                continue
        
        if all_candles:
            new_df = pd.DataFrame(all_candles, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            if not os.path.exists(file_path):
                new_df.to_csv(file_path, index=False)
            else:
                new_df.to_csv(file_path, mode='a', header=False, index=False)
        
        print(f"  [Done] {symbol} complete.")

if __name__ == "__main__":
    fetch_history()