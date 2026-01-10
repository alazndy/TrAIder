"""
Data Loader Utility
Centralizes fetching logic for Crypto (CCXT) and Macro (YFinance) data.
"""

import ccxt
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

def fetch_crypto(symbol, start_date="2020-01-01"):
    """Fetch Crypto OHLCV from Binance"""
    print(f"[*] Fetching Crypto: {symbol}...")
    exchange = ccxt.binance()
    since = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
    all_ohlcv = []
    
    try:
        while True:
            ohlcv = exchange.fetch_ohlcv(symbol, "1d", since=since, limit=1000)
            if not ohlcv: break
            all_ohlcv.extend(ohlcv)
            since = ohlcv[-1][0] + 1
            last_date = datetime.fromtimestamp(ohlcv[-1][0] / 1000)
            if last_date.year >= 2026: break
            
        df = pd.DataFrame(all_ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['time'], unit='ms')
        return df
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

def fetch_macro_data(start_date="2020-01-01"):
    """Fetch Macro Data (DXY, VIX) from YFinance + ETH/BTC from Binance"""
    print("[*] Fetching Macro Data (DXY, VIX, ETH/BTC)...")
    try:
        # 1. YFinance Data (DXY, VIX)
        tickers = ["DX-Y.NYB", "^VIX"] 
        data = yf.download(tickers, start=start_date, end=datetime.now().strftime("%Y-%m-%d"), progress=False)
        
        dxy, vix = None, None
        
        if isinstance(data.columns, pd.MultiIndex):
            if 'DX-Y.NYB' in data['Close']:
                dxy = data['Close']['DX-Y.NYB'].reset_index()
            if '^VIX' in data['Close']:
                vix = data['Close']['^VIX'].reset_index()
        else:
            # Fallback if structure is flat (unlikely with multi-ticker)
            pass 
            
        if dxy is None or vix is None:
             print("  [Error] Failed to parse YFinance Macro Data")
             return None

        dxy.columns = ['date', 'dxy_close']
        vix.columns = ['date', 'vix_close']
        macro = pd.merge(dxy, vix, on='date', how='outer')
        
        # 2. Binance Data (ETH/BTC) - Altseason Indicator
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
            
        eth_btc_df = pd.DataFrame(eth_btc_ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        eth_btc_df['date'] = pd.to_datetime(eth_btc_df['time'], unit='ms').dt.tz_localize(None)
        eth_btc_clean = eth_btc_df[['date', 'close']].rename(columns={'close': 'eth_btc_close'})
        
        # Merge All
        if macro['date'].dt.tz is not None:
            macro['date'] = macro['date'].dt.tz_localize(None)
            
        macro = pd.merge(macro, eth_btc_clean, on='date', how='outer')
        macro = pd.merge(macro, eth_btc_clean, on='date', how='outer')
        
        # 3. GLOBAL MARKET CONTEXT (BTC/USDT)
        # Proteus Neo needs BTC price action to gauge global sentiment
        btc_ohlcv = []
        since = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
        while True:
            ohlcv = binance.fetch_ohlcv("BTC/USDT", "1d", since=since, limit=1000)
            if not ohlcv: break
            btc_ohlcv.extend(ohlcv)
            since = ohlcv[-1][0] + 1
            last_date = datetime.fromtimestamp(ohlcv[-1][0] / 1000)
            if last_date.year >= 2026: break
            
        btc_df = pd.DataFrame(btc_ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        btc_df['date'] = pd.to_datetime(btc_df['time'], unit='ms').dt.tz_localize(None)
        btc_clean = btc_df[['date', 'close', 'volume']].rename(columns={
            'close': 'market_btc_close',
            'volume': 'market_btc_vol'
        })
        
        macro = pd.merge(macro, btc_clean, on='date', how='outer')
        
        macro = macro.sort_values('date').ffill()
        
        return macro
    except Exception as e:
        print(f"Error fetching macro: {e}")
        return None

def merge_data(crypto_df, macro_df):
    """Merge Crypto OHLCV with Macro Data"""
    # Create copies to avoid SettingWithCopy warnings on input dfs
    c_df = crypto_df.copy()
    m_df = macro_df.copy()
    
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
