
"""
Proteus Live Signal Check
"""
import ccxt
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from strategies import get_strategy
import warnings
warnings.filterwarnings('ignore')

SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "AVAX/USDT"]

def fetch_live_data():
    print("[*] Fetching LIVE Market Data...")
    
    # 1. Macro Data (Real-time-ish)
    macro = yf.download(["DX-Y.NYB", "^VIX"], period="5d", interval="1d", progress=False)
    
    if isinstance(macro.columns, pd.MultiIndex):
        dxy = macro['Close']['DX-Y.NYB'].iloc[-1]
        vix = macro['Close']['^VIX'].iloc[-1]
    else:
        dxy = macro['Close'].iloc[-1] # Fallback
        vix = 0
        
    print(f"  [MACRO] DXY: {dxy:.2f} | VIX: {vix:.2f}")
    
    # 2. Altseason Indicator (ETH/BTC)
    binance = ccxt.binance()
    eth_btc = binance.fetch_ohlcv("ETH/BTC", "1d", limit=50)
    eth_btc_close = eth_btc[-1][4]
    
    # Calculate ROC for Altseason manually since we just have list
    eth_btc_closes = pd.Series([x[4] for x in eth_btc])
    alt_season_strength = eth_btc_closes.pct_change(20).iloc[-1] * 100
    
    print(f"  [ALT] ETH/BTC: {eth_btc_close:.5f} | Strength: {alt_season_strength:.2f}%")
    
    return dxy, vix, eth_btc_closes

def check_signal(symbol, dxy_val, vix_val, eth_btc_series):
    exchange = ccxt.binance()
    ohlcv = exchange.fetch_ohlcv(symbol, "1d", limit=200)
    
    df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['time'], unit='ms')
    
    # Inject Macro Data into DF (Simulating as if we have history)
    # For a simple 'NOW' check, we just fill the column with current value
    # Ideally we'd fetch full history, but for 'decision now' this approximation works for the indicator calculation
    df['dxy_close'] = dxy_val
    df['vix_close'] = vix_val
    df['eth_btc_close'] = eth_btc_series.iloc[-1] # Simplification
    
    # Load Strategy
    proteus = get_strategy("proteus", {"model_dir": f"data/adaptive_ai_{symbol.replace('/', '_')}"})
    
    # We need to re-train or load? 
    # Since we are just checking signal, we assume models exist from previous backtest tasks.
    # If not, it will default to Neutral.
    
    result = proteus.analyze(df)
    return result

def main():
    dxy, vix, eth_btc_series = fetch_live_data()
    
    print("\n" + "="*50)
    print("🤖 PROTEUS AI: CURRENT DECISION ($100)")
    print("="*50)
    
    active_action = "WAIT (CASH)"
    
    for sym in SYMBOLS:
        res = check_signal(sym, dxy, vix, eth_btc_series)
        signal = res.get('signal')
        conf = res.get('confidence', 0)
        mode = res.get('mode', 'unknown')
        pred = res.get('prediction')
        
        icon = "⚪"
        if signal == "BUY": icon = "🟢"
        elif signal == "SELL": icon = "🔴"
        
        print(f"{icon} {sym:<10} | Signal: {signal:<4} ({conf:>5.1f}%) | Mode: {mode.upper()}")
        
        if signal == "BUY" and active_action == "WAIT (CASH)":
            active_action = f"BUY {sym}"
            
    print("-" * 50)
    print(f"💰 FINAL ACTION: {active_action}")
    print("-" * 50)

if __name__ == "__main__":
    main()
