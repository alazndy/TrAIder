"""
Unified Backtest Runner
Supports Single, Parallel, and Hybrid modes.
Usage:
  python run_backtest.py --mode hybrid
  python run_backtest.py --mode parallel --symbols BTC/USDT,SOL/USDT
  python run_backtest.py --mode single --symbol BTC/USDT --strategy proteus
"""

import argparse
import pandas as pd
from datetime import datetime
from strategies import get_strategy
from utils.data_loader import fetch_crypto, fetch_macro_data, merge_data
import warnings

warnings.filterwarnings('ignore')

from paper_config import PAPER_PORTFOLIO

# Convert list-based PAPER_PORTFOLIO to group-based format for this runner
# (This is a quick adapter to keep run_backtest logic working)
neo_assets = [p['symbol'] for p in PAPER_PORTFOLIO if p['strategy'] == 'proteus_neo']
std_assets = [p['symbol'] for p in PAPER_PORTFOLIO if p['strategy'] == 'adaptive_ai']

HYBRID_PORTFOLIO = {
    "Golden List (Neo)": {"assets": neo_assets, "strategy": "proteus_neo"},
    "Golden List (Std)": {"assets": std_assets, "strategy": "adaptive_ai"}
}

def run_strategy(df, strategy_name, symbol, start_date, end_date, capital):
    """Run a single strategy backtest"""
    # Filter for test period
    mask = (df['date'] >= start_date) & (df['date'] <= end_date)
    test_df = df[mask].copy().reset_index(drop=True)
    
    if test_df.empty:
        return 0, 0, []
        
    # Initialize Strategy
    model_dir = f"data/{strategy_name}_{symbol.replace('/', '_')}_unified"
    strategy = get_strategy(strategy_name, {"model_dir": model_dir})
    
    # Train on Full History
    print(f"  [{strategy_name}] Training model for {symbol}...")
    strategy.train_all(df) 
    
    # Execution Loop
    position = 0
    current_capital = capital
    trades_log = []
    
    for i in range(20, len(test_df)):
        current_date_val = test_df.iloc[i]['date']
        # Feed data up to current point to prevent lookahead
        window = df[df['date'] <= current_date_val]
        
        result = strategy.analyze(window)
        signal = result.get('signal', 'NEUTRAL')
        confidence = result.get('confidence', 0)
        mode = result.get('mode', 'unknown')
        price = test_df.iloc[i]['close']
        
        if signal == "BUY" and position == 0:
            position = current_capital / price
            trades_log.append({
                "Date": current_date_val,
                "Symbol": symbol,
                "Action": "BUY",
                "Price": price,
                "Amount": position,
                "Balance": 0,
                "Confidence": confidence,
                "Mode": mode
            })
            current_capital = 0
            
        elif signal == "SELL" and position > 0:
            revenue = position * price
            trades_log.append({
                "Date": current_date_val,
                "Symbol": symbol,
                "Action": "SELL",
                "Price": price,
                "Amount": position,
                "Balance": revenue,
                "Confidence": confidence,
                "Mode": mode
            })
            current_capital = revenue
            position = 0
            
    if position > 0:
        final_val = position * test_df.iloc[-1]['close']
        current_capital = final_val
        trades_log.append({ # Mark open position value at end
            "Date": test_df.iloc[-1]['date'],
            "Symbol": symbol,
            "Action": "HOLD (End)",
            "Price": test_df.iloc[-1]['close'],
            "Amount": position,
            "Balance": final_val, 
            "Confidence": 0,
            "Mode": "end"
        })
        
    roi = ((current_capital - capital) / capital) * 100
    profit = current_capital - capital
    return roi, profit, trades_log



def main():
    parser = argparse.ArgumentParser(description="TrAIder Backtest Engine")
    parser.add_argument("--mode", type=str, choices=["single", "parallel", "hybrid"], default="hybrid", help="Backtest mode")
    parser.add_argument("--symbol", type=str, help="Symbol for single/parallel mode (e.g. BTC/USDT)")
    parser.add_argument("--symbols", type=str, help="Comma separated symbols for parallel mode")
    parser.add_argument("--strategy", type=str, default="proteus", help="Strategy for single/parallel mode")
    parser.add_argument("--start", type=str, default="2025-01-01", help="Test Start Date")
    parser.add_argument("--end", type=str, default="2025-12-31", help="Test End Date")
    parser.add_argument("--capital", type=float, default=1000.0, help="Initial Capital per Asset")
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print(f"🚀 BACKTEST RUNNER | Mode: {args.mode.upper()} | Range: {args.start} to {args.end}")
    print("="*70)
    
    # Fetch Macro Data Once
    macro_df = fetch_macro_data()
    if macro_df is None:
        print("[Error] Macro data fetch failed.")
        return

    results = []
    
    # Collect all trades
    all_trades = []

    if args.mode == "hybrid":
        # Run Pre-defined Hybrid Portfolio
        print("[*] Running Hybrid Portfolio Configuration...")
        
        for group_name, config in HYBRID_PORTFOLIO.items():
            strat = config["strategy"]
            for sym in config["assets"]:
                crypto_df = fetch_crypto(sym)
                if crypto_df is None or crypto_df.empty: continue
                
                full_df = merge_data(crypto_df, macro_df)
                roi, profit, t_log = run_strategy(full_df, strat, sym, args.start, args.end, args.capital)
                all_trades.extend(t_log)
                
                results.append({
                    "Symbol": sym,
                    "Strategy": strat,
                    "ROI": roi,
                    "Profit": profit
                })
                
    elif args.mode == "parallel":
        # Run specific strategy on list of symbols
        targets = args.symbols.split(",") if args.symbols else ["BTC/USDT", "SOL/USDT"]
        strat = args.strategy
        
        for sym in targets:
            sym = sym.strip()
            crypto_df = fetch_crypto(sym)
            if crypto_df is None: continue
            
            full_df = merge_data(crypto_df, macro_df)
            roi, profit, t_log = run_strategy(full_df, strat, sym, args.start, args.end, args.capital)
            all_trades.extend(t_log)
            
            results.append({
                "Symbol": sym,
                "Strategy": strat,
                "ROI": roi,
                "Profit": profit
            })
            
    elif args.mode == "single":
        if not args.symbol:
            print("Error: --symbol required for single mode")
            return
            
        crypto_df = fetch_crypto(args.symbol)
        if crypto_df is not None:
            full_df = merge_data(crypto_df, macro_df)
            roi, profit, t_log = run_strategy(full_df, args.strategy, args.symbol, args.start, args.end, args.capital)
            all_trades.extend(t_log)
            
            results.append({
                "Symbol": args.symbol,
                "Strategy": args.strategy,
                "ROI": roi,
                "Profit": profit
            })

    # Save Trades to CSV
    if all_trades:
        trades_df = pd.DataFrame(all_trades)
        trades_df.sort_values(by="Date", inplace=True)
        csv_filename = "trades_log_2025.csv"
        trades_df.to_csv(csv_filename, index=False)
        print(f"\n[+] Trade log saved to: {csv_filename}")

    # Report
    print("\n" + "="*70)
    print(f"{'Symbol':<10} {'Strategy':<15} {'ROI':<10} {'Profit':<10}")
    print("-" * 70)
    
    total_profit = 0
    total_invested = len(results) * args.capital
    
    for r in results:
        print(f"{r['Symbol']:<10} {r['Strategy']:<15} {r['ROI']:>9.2f}% ${r['Profit']:>9.2f}")
        total_profit += r['Profit']
        
    print("-" * 70)
    if total_invested > 0:
        total_roi = (total_profit / total_invested) * 100
        print(f"TOTAL RETURN: {total_roi:.2f}% | NET PROFIT: ${total_profit:.2f}")
    print("=" * 70)

if __name__ == "__main__":
    main()
