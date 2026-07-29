"""
Data Loader Utility
Centralizes fetching logic for Crypto (CCXT) and Macro (YFinance) data.
"""

import ccxt
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime


def fetch_from_yfinance(symbol, start_date):
    """Fallback fetcher using YFinance"""
    try:
        # Convert CCXT format to YFinance (BTC/USDT -> BTC-USD)
        yf_sym = symbol.replace("/USDT", "-USD").replace("/BTC", "-BTC")
        print(f"  [Fallback] Fetching {yf_sym} from YFinance...")
        
        df = yf.download(yf_sym, start=start_date, progress=False, auto_adjust=True) # auto_adjust for splits/divs
        
        if df.empty: return None
        
        # Reset index to get Date column
        df = df.reset_index()
        
        if isinstance(df.columns, pd.MultiIndex):
            # Flatten: ('Close', 'BTC-USD') -> 'Close'
            # Or just take the first level if the second is ticker
            df.columns = df.columns.get_level_values(0)
        
        # Lowercase columns
        df.columns = [str(c).lower() for c in df.columns]
        
        # Ensure 'date' exists (older yfinance ver might index differently)
        if 'date' not in df.columns and 'datetime' in df.columns:
             df = df.rename(columns={'datetime': 'date'})
             
        # Create 'time' (ms timestamp) for compatibility
        df['time'] = df['date'].astype(np.int64) // 10**6 
        
        return df[['time', 'open', 'high', 'low', 'close', 'volume', 'date']]
    except Exception as e:
        print(f"  [Fallback Error] {e}")
        return None

def fetch_crypto(symbol, start_date="2020-01-01"):
    """Fetch Crypto OHLCV from Binance with YFinance Fallback"""
    print(f"[*] Fetching Crypto: {symbol}...")
    
    # 1. Try Binance
    try:
        exchange = ccxt.binance()
        since = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
        all_ohlcv = []
        
        while True:
            ohlcv = exchange.fetch_ohlcv(symbol, "1d", since=since, limit=1000)
            if not ohlcv: break
            all_ohlcv.extend(ohlcv)
            since = ohlcv[-1][0] + 1
            last_date = datetime.fromtimestamp(ohlcv[-1][0] / 1000)
            if last_date.year >= 2026: break
            
        if all_ohlcv:
            df = pd.DataFrame(all_ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            df['date'] = pd.to_datetime(df['time'], unit='ms')
            return df
    except Exception as e:
        print(f"  [Binance Error] {e}")

    # 2. Fallback to YFinance
    return fetch_from_yfinance(symbol, start_date)

def fetch_macro_data(start_date="2020-01-01"):
    """Fetch Macro Data with Fallbacks"""
    print("[*] Fetching Macro Data (DXY, VIX, ETH/BTC)...")
    try:
        # 1. YFinance Data (DXY, VIX)
        tickers = ["DX-Y.NYB", "^VIX"] 
        data = yf.download(tickers, start=start_date, end=datetime.now().strftime("%Y-%m-%d"), progress=False)
        
        dxy, vix = None, None
        
        # Handle MultiIndex headers in newer Pandas/YF
        if isinstance(data.columns, pd.MultiIndex):
            try:
                if 'DX-Y.NYB' in data['Close'].columns:
                    dxy = data['Close']['DX-Y.NYB'].reset_index()
                if '^VIX' in data['Close'].columns:
                    vix = data['Close']['^VIX'].reset_index()
            except:
                pass # Structure might vary
        else:
            # Flat structure (if single ticker or flattened)
            pass 

        # DXY fallback/mock if missing
        if dxy is None:
             # Create dummy DXY flat (100)
             dates = pd.date_range(start=start_date, end=datetime.now())
             dxy = pd.DataFrame({'date': dates, 'dxy_close': 100.0})
        else:
             dxy.columns = ['date', 'dxy_close']

        if vix is None:
             # Create dummy VIX flat (20)
             dates = pd.date_range(start=start_date, end=datetime.now())
             vix = pd.DataFrame({'date': dates, 'vix_close': 20.0})
        else:
             vix.columns = ['date', 'vix_close']
             
        # Normalize timezones
        if dxy['date'].dt.tz is not None: dxy['date'] = dxy['date'].dt.tz_localize(None)
        if vix['date'].dt.tz is not None: vix['date'] = vix['date'].dt.tz_localize(None)

        macro = pd.merge(dxy, vix, on='date', how='outer')
        
        # 2. ETH/BTC (Altseason) - Try Binance -> Fallback YF
        eth_btc_df = None
        try:
            binance = ccxt.binance()
            since = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
            eth_btc_ohlcv = []
            while True:
                ohlcv = binance.fetch_ohlcv("ETH/BTC", "1d", since=since, limit=1000)
                if not ohlcv: break
                eth_btc_ohlcv.extend(ohlcv)
                since = ohlcv[-1][0] + 1
                last_date = datetime.fromtimestamp(ohlcv[-1][0] / 1000)
                if last_date.year >= 2026: break
            
            if eth_btc_ohlcv:
                df = pd.DataFrame(eth_btc_ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                df['date'] = pd.to_datetime(df['time'], unit='ms').dt.tz_localize(None)
                eth_btc_df = df[['date', 'close']].rename(columns={'close': 'eth_btc_close'})
        except:
            pass
            
        if eth_btc_df is None:
             # Fallback
             yf_eth = fetch_from_yfinance("ETH/BTC", start_date)
             if yf_eth is not None:
                 if yf_eth['date'].dt.tz is not None: yf_eth['date'] = yf_eth['date'].dt.tz_localize(None)
                 eth_btc_df = yf_eth[['date', 'close']].rename(columns={'close': 'eth_btc_close'})

        if eth_btc_df is not None:
             macro = pd.merge(macro, eth_btc_df, on='date', how='outer')

        # 3. GLOBAL MARKET BTC - Try Binance -> Fallback YF
        btc_df = None
        try:
            since = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
            btc_ohlcv = []
            # Reuse binance instance if alive? No, just try/except block
            binance = ccxt.binance() 
            while True:
                ohlcv = binance.fetch_ohlcv("BTC/USDT", "1d", since=since, limit=1000)
                if not ohlcv: break
                btc_ohlcv.extend(ohlcv)
                since = ohlcv[-1][0] + 1
                last_date = datetime.fromtimestamp(ohlcv[-1][0] / 1000)
                if last_date.year >= 2026: break
                
            if btc_ohlcv:
                df = pd.DataFrame(btc_ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                df['date'] = pd.to_datetime(df['time'], unit='ms').dt.tz_localize(None)
                btc_df = df[['date', 'close', 'volume']].rename(columns={'close': 'market_btc_close', 'volume': 'market_btc_vol'})
        except:
             pass

        if btc_df is None:
             yf_btc = fetch_from_yfinance("BTC/USDT", start_date)
             if yf_btc is not None:
                 if yf_btc['date'].dt.tz is not None: yf_btc['date'] = yf_btc['date'].dt.tz_localize(None)
                 btc_df = yf_btc[['date', 'close', 'volume']].rename(columns={'close': 'market_btc_close', 'volume': 'market_btc_vol'})

        if btc_df is not None:
             macro = pd.merge(macro, btc_df, on='date', how='outer')
        
        macro = macro.sort_values('date').ffill()
        
        return macro
    except Exception as e:
        print(f"Error fetching macro: {e}")
        return None

def merge_data(crypto_df, macro_df):
    """Merge Crypto OHLCV with Macro Data"""
    c_df = crypto_df.copy()
    m_df = macro_df.copy()
    
    # Timezone normalization
    if c_df['date'].dt.tz is not None: c_df['date'] = c_df['date'].dt.tz_localize(None)
    if m_df['date'].dt.tz is not None: m_df['date'] = m_df['date'].dt.tz_localize(None)

    c_df['date_only'] = c_df['date'].dt.normalize()
    m_df['date_only'] = m_df['date'].dt.normalize()
    
    m_clean = m_df.drop(columns=['date'])
    merged = pd.merge(c_df, m_clean, on='date_only', how='left')
    
    merged['dxy_close'] = merged['dxy_close'].ffill()
    merged['vix_close'] = merged['vix_close'].ffill()
    if 'eth_btc_close' in merged.columns:
        merged['eth_btc_close'] = merged['eth_btc_close'].ffill()
        
    if 'market_btc_close' in merged.columns:
        merged['market_btc_close'] = merged['market_btc_close'].ffill()
        merged['market_btc_vol'] = merged['market_btc_vol'].ffill()
        
    if 'date' not in merged.columns and 'date_x' in merged.columns:
         merged = merged.rename(columns={'date_x': 'date'})
         
    return merged
