"""
Opportunity Scanner
Scans top assets to find the best performers for AI strategies in the last 30 days.
"""

import ccxt
import pandas as pd
from strategies import get_strategy
from utils.data_loader import fetch_macro_data, merge_data
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')

# Top 20+ High Volume & Trending Assets
CANDIDATES = [
    # Majors
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    # L1s
    "ADA/USDT", "AVAX/USDT", "TRX/USDT", "DOT/USDT", "MATIC/USDT",
    "NEAR/USDT", "ATOM/USDT", "FTM/USDT", "SUI/USDT", "SEI/USDT",
    # Meme
    "DOGE/USDT", "SHIB/USDT", "PEPE/USDT", "BONK/USDT",
    # DeFi / AI / Infra
    "UNI/USDT", "LINK/USDT", "LDO/USDT", "RNDR/USDT", "FET/USDT",
    "INJ/USDT", "ARB/USDT", "OP/USDT", "TIA/USDT"
]

def quick_backtest(symbol, df, strategy_name):
    # Train on first half, test on second half (simplified rapid check)
    # Actually for opportunity scanning, we want to see how it would have done recently
    # assuming we had trained it. So we train on full history up to N days ago.
    
    # Let's say we simulate the last 30 days.
    # We train on data BEFORE the last 30 days.
    
    cutoff_date = df.iloc[-1]['date'] - timedelta(days=30)
    
    train_df = df[df['date'] < cutoff_date]
    test_df = df[df['date'] >= cutoff_date].reset_index(drop=True)
    
    if len(train_df) < 100 or len(test_df) < 10:
        return -999 # Not enough data
        
    # Init Strategy
    model_dir = f"data/scanner_{strategy_name}_{symbol.replace('/', '_')}"
    strategy = get_strategy(strategy_name, {"model_dir": model_dir})
    
    # Quick Train
    strategy.train_all(train_df)
    
    # Run
    capital = 1000.0
    position = 0
    trades = 0
    wins = 0
    
    for i in range(len(test_df)):
        # No lookahead: window is all data up to current test day
        # But for speed in scanner, we just pass the row context simply or small window
        # To be accurate we need full window.
        current_date = test_df.iloc[i]['date']
        window = df[df['date'] <= current_date]
        
        result = strategy.analyze(window)
        signal = result.get('signal', 'NEUTRAL')
        price = test_df.iloc[i]['close']
        
        if signal == "BUY" and position == 0:
            position = capital / price
            capital = 0
            entry_price = price
            trades += 1
        elif signal == "SELL" and position > 0:
            capital = position * price
            if price > entry_price: wins += 1
            position = 0
            
    if position > 0:
        capital = position * test_df.iloc[-1]['close']
        
    roi = ((capital - 1000.0) / 1000.0) * 100
    return roi, trades

def main():
    print("\n" + "="*70)
    print("🛰️ MARKET OPPORTUNITY SCANNER (Last 30 Days)")
    print("="*70)
    
    macro_df = fetch_macro_data()
    if macro_df is None: return

    exchange = ccxt.binance()
    results = []
    
    print(f"[*] Scanning {len(CANDIDATES)} assets...")
    
    for sym in CANDIDATES:
        try:
            # Fetch last ~300 days to have enough training data
            ohlcv = exchange.fetch_ohlcv(sym, "1d", limit=365) 
            if not ohlcv: continue
            
            df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            df['date'] = pd.to_datetime(df['time'], unit='ms')
            
            full_df = merge_data(df, macro_df)
            
            # Test All Strategies
            roi_std, trades_std = quick_backtest(sym, full_df, "adaptive_ai")
            roi_pro, trades_pro = quick_backtest(sym, full_df, "proteus")
            roi_neo, trades_neo = quick_backtest(sym, full_df, "proteus_neo")
            
            # Pick Winner
            stats = [
                ("Standard", roi_std, trades_std),
                ("Proteus", roi_pro, trades_pro),
                ("Proteus Neo", roi_neo, trades_neo)
            ]
            best = max(stats, key=lambda x: x[1]) # Max ROI
            
            best_strat, best_roi, best_trades = best
            
            # Volatility Metric
            volatility = df['close'].pct_change().std() * 100
            
            print(f"  > {sym:<10} | Best: {best_roi:>6.2f}% ({best_strat}) | Vol: {volatility:.2f}%")
            
            results.append({
                "Symbol": sym,
                "Best_Strategy": best_strat,
                "ROI_30d": best_roi,
                "Trades": best_trades,
                "Volatility": volatility
            })
            
        except Exception as e:
            print(f"  x {sym}: Error {e}")
            
    # Sort and Report
    results.sort(key=lambda x: x['ROI_30d'], reverse=True)
    top_picks = results[:8] # Top 8
    
    print("\n" + "="*70)
    print(f"🏆 TOP 8 GOLDEN OPPORTUNITIES (Next Month Candidates)")
    print(f"{'Symbol':<10} {'Strategy':<10} {'30d ROI':<10} {'Trades':<8} {'Volaty':<8}")
    print("-" * 70)
    
    for r in top_picks:
        print(f"{r['Symbol']:<10} {r['Best_Strategy']:<10} {r['ROI_30d']:>8.2f}% {r['Trades']:>8} {r['Volatility']:>7.2f}%")
        
    print("-" * 70)
    
    # Save recommendation
    rec_df = pd.DataFrame(top_picks)
    rec_df.to_csv("golden_list.csv", index=False)
    print("[+] Golden List saved to 'golden_list.csv'")

if __name__ == "__main__":
    main()
