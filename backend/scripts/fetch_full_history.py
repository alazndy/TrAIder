import ccxt
import yfinance as yf
import pandas as pd
import os
import time
from datetime import datetime, timedelta

# Configuration
EXCHANGE_ID = 'binance'
TIMEFRAME = '1h'
SINCE_DATE = '2015-01-01' # yfinance expects YYYY-MM-DD
DATA_DIR = '../data/raw'

# 1. CRYPTO ASSETS (CCXT)
CRYPTO_SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT',
    'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT', 'DOT/USDT', 'TRX/USDT',
    'LINK/USDT', 'MATIC/USDT', 'LTC/USDT', 'SHIB/USDT', 'UNI/USDT'
]

# 2. GLOBAL STOCKS (YFINANCE)
# Format: {Symbol: Name/Region}
STOCK_SYMBOLS = {
    # 🇹🇷 TURKEY (BIST)
    'THYAO.IS': 'Turkish Airlines',
    'GARAN.IS': 'Garanti BBVA',
    'ASELS.IS': 'Aselsan',
    'EREGL.IS': 'Eregli Demir Celik',
    'KCHOL.IS': 'Koc Holding',
    
    # 🇺🇸 USA (NYSE/NASDAQ)
    'SPY': 'S&P 500 ETF',
    'AAPL': 'Apple',
    'MSFT': 'Microsoft',
    'GOOGL': 'Alphabet',
    'AMZN': 'Amazon',
    'TSLA': 'Tesla',
    'NVDA': 'NVIDIA',
    'AMD': 'AMD',
    
    # 🇨🇳 CHINA (HKEX / US ADRs)
    'BABA': 'Alibaba (US)',
    'JD': 'JD.com',
    'BIDU': 'Baidu',
    '0700.HK': 'Tencent',
    
    # 🇯🇵 JAPAN (TOKYO)
    '7203.T': 'Toyota',
    '6758.T': 'Sony',
    '9984.T': 'SoftBank',
    '7974.T': 'Nintendo'
}

def fetch_crypto():
    print(f"\n[*] --- FETCHING CRYPTO ASSETS (Binance) ---")
    exchange = getattr(ccxt, EXCHANGE_ID)({
        'enableRateLimit': True,
    })
    
    start_ts = exchange.parse8601(f"{SINCE_DATE} 00:00:00")
    
    for symbol in CRYPTO_SYMBOLS:
        safe_symbol = symbol.replace('/', '_')
        file_path = os.path.join(DATA_DIR, f"{safe_symbol}_{TIMEFRAME}.csv")
        
        # Resume logic
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

def fetch_stocks():
    print(f"\n[*] --- FETCHING GLOBAL STOCKS (YFinance) ---")
    
    # YFinance interval mapping
    yf_interval = "1h" # 1h is standard for recent history (last 730 days max usually for hourly)
    # Note: YFinance 1h data is limited to last 730 days. For longer history, we must use 1d.
    # To keep consistency with crypto (1h), we will try 1h, but fallback to 1d if needed?
    # Actually, for deep learning, more granular is better. Let's stick to 1h for recent, maybe 1d for long term?
    # Strategy uses 1h timeframe. Let's get max available 1h data (730 days).
    
    start_date = (datetime.now() - timedelta(days=729)).strftime('%Y-%m-%d')
    print(f"  [Info] Fetching hourly stock data from {start_date} (Max 730 days limit for 1h)")

    for symbol, name in STOCK_SYMBOLS.items():
        safe_symbol = symbol.replace('.', '_')
        file_path = os.path.join(DATA_DIR, f"{safe_symbol}_{TIMEFRAME}.csv")
        
        print(f"  [Stock] Fetching {name} ({symbol})...")
        
        try:
            # Download
            df = yf.download(symbol, start=start_date, interval=yf_interval, progress=False)
            
            if df.empty:
                print(f"    [!] No data found for {symbol}")
                continue
            
            # Format to match CCXT structure: time (ms), open, high, low, close, volume
            # YFinance returns Datetime index with timezone
            df = df.reset_index()
            
            # Fix MultiIndex columns (e.g. ('Close', 'AAPL'))
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # Rename columns
            df.columns = [c.lower() for c in df.columns] # date, open, high, low, close, adj close, volume
            
            # Ensure 'time' column in ms
            if 'date' in df.columns:
                 df['time'] = df['date'].astype('int64') // 10**6 # ns to ms
            elif 'datetime' in df.columns:
                 df['time'] = df['datetime'].astype('int64') // 10**6
                 
            # Select and reorder
            df = df[['time', 'open', 'high', 'low', 'close', 'volume']]
            
            # Save
            df.to_csv(file_path, index=False)
            print(f"    -> Saved {len(df)} candles.")
            
        except Exception as e:
            print(f"    [!] Error fetching {symbol}: {e}")

if __name__ == "__main__":
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    fetch_crypto()
    fetch_stocks()