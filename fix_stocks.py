import yfinance as yf
import pandas as pd
import os
from datetime import datetime, timedelta

STOCK_SYMBOLS = {
    'THYAO.IS': 'Turkish Airlines',
    'GARAN.IS': 'Garanti BBVA',
    'AAPL': 'Apple',
    'TSLA': 'Tesla',
    'NVDA': 'NVIDIA',
    'BABA': 'Alibaba',
    '7203.T': 'Toyota'
}

DATA_DIR = 'backend/data/raw'

def fix_and_fetch_stocks():
    start_date = (datetime.now() - timedelta(days=729)).strftime('%Y-%m-%d')
    
    for symbol, name in STOCK_SYMBOLS.items():
        print(f"[*] Fetching {symbol}...")
        df = yf.download(symbol, start=start_date, interval="1h", progress=False)
        if df.empty: continue
        
        df = df.reset_index()
        # Flatten MultiIndex if necessary
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df.columns = [c.lower() for c in df.columns]
        
        # CORRECT TIME CONVERSION
        # yfinance 'datetime' or 'date' is already a proper datetime object
        t_col = 'datetime' if 'datetime' in df.columns else 'date'
        df['time'] = df[t_col].apply(lambda x: int(x.timestamp() * 1000))
        
        df = df[['time', 'open', 'high', 'low', 'close', 'volume']]
        
        safe_symbol = symbol.replace('.', '_')
        file_path = os.path.join(DATA_DIR, f"{safe_symbol}_1h.csv")
        df.to_csv(file_path, index=False)
        print(f"  -> Saved {len(df)} candles to {file_path}")

if __name__ == "__main__":
    fix_and_fetch_stocks()
