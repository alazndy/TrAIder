import ccxt
import pandas as pd
import os
import time
from datetime import datetime, timedelta

DATA_DIR = '../data/omega'
SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'NVDA', 'AAPL', 'THYAO.IS']
TIMEFRAMES = ['15m', '1h', '1d']

def fetch_omega_data():
    if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
    exchange = ccxt.binance()
    
    print("="*60)
    print("🌌 OMEGA DATA ENGINE - MULTI-TIMEFRAME SYNC (FIXED)")
    print("="*60)

    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            print(f"[*] Fetching {symbol} | {tf}...")
            
            if "/" in symbol: # Crypto
                since = exchange.parse8601('2015-01-01T00:00:00Z') if tf != '15m' else exchange.parse8601((datetime.now() - timedelta(days=365)).isoformat())
                all_ohlcv = []
                while True:
                    try:
                        ohlcv = exchange.fetch_ohlcv(symbol, tf, since=since, limit=1000)
                        if not ohlcv: break
                        all_ohlcv.extend(ohlcv)
                        since = ohlcv[-1][0] + 1
                        if len(ohlcv) < 1000: break
                    except: break
                df = pd.DataFrame(all_ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            
            else: # Stocks
                import yfinance as yf
                period = "max" if tf != '15m' else "60d"
                df = yf.download(symbol, period=period, interval=tf if tf != '15m' else '15m', progress=False)
                if df.empty: continue
                df = df.reset_index()
                
                # SECURE COLUMN FLATTENING
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df.columns = [str(c).lower() for c in df.columns]
                
                t_col = 'datetime' if 'datetime' in df.columns else 'date'
                df['time'] = df[t_col].apply(lambda x: int(x.timestamp() * 1000))
                df = df[['time', 'open', 'high', 'low', 'close', 'volume']]

            safe_symbol = symbol.replace('/', '_').replace('.', '_')
            df.to_csv(os.path.join(DATA_DIR, f"{safe_symbol}_{tf}.csv"), index=False)

if __name__ == "__main__":
    fetch_omega_data()