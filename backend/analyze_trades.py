"""
Trade Log Analyzer
Reads trades_log_2025.csv and calculates performance metrics.
"""
import pandas as pd
import numpy as np

def analyze_log(filename="trades_log_2025.csv"):
    try:
        df = pd.read_csv(filename)
    except FileNotFoundError:
        print(f"Error: {filename} not found.")
        return

    print(f"Analyzing {len(df)} log entries...")
    
    # Group by Symbol to track individual trade cycles
    symbols = df['Symbol'].unique()
    
    overall_stats = {
        "wins": 0, "losses": 0, "total_profit": 0, "total_loss": 0, "trades": 0
    }
    
    symbol_stats = {}

    for sym in symbols:
        sym_df = df[df['Symbol'] == sym].sort_values('Date')
        
        entry_price = 0
        entry_amt = 0
        total_pnl = 0
        wins = 0
        losses = 0
        trades = 0
        
        for index, row in sym_df.iterrows():
            if row['Action'] == 'BUY':
                entry_price = row['Price']
                entry_amt = row['Amount']
            
            elif row['Action'] == 'SELL' or row['Action'] == 'HOLD (End)':
                if entry_price == 0: continue # Skip if sold without buy (shouldn't happen)
                
                exit_price = row['Price']
                pnl = (exit_price - entry_price) * entry_amt
                
                if pnl > 0:
                    wins += 1
                    overall_stats["total_profit"] += pnl
                else:
                    losses += 1
                    overall_stats["total_loss"] += abs(pnl)
                    
                total_pnl += pnl
                trades += 1
                entry_price = 0 # Reset
                
        symbol_stats[sym] = {
            "pnl": total_pnl,
            "wins": wins,
            "losses": losses,
            "trades": trades,
            "win_rate": (wins/trades*100) if trades > 0 else 0
        }
        
        overall_stats["wins"] += wins
        overall_stats["losses"] += losses
        overall_stats["trades"] += trades

    # Report
    print("\n" + "="*60)
    print(f"{'Symbol':<10} {'Trades':<8} {'Win Rate':<10} {'Net PnL':<15}")
    print("-" * 60)
    
    for sym, stats in symbol_stats.items():
        print(f"{sym:<10} {stats['trades']:<8} {stats['win_rate']:>6.1f}%    ${stats['pnl']:>10.2f}")
        
    print("-" * 60)
    
    total_trades = overall_stats["trades"]
    if total_trades > 0:
        avg_win_rate = (overall_stats["wins"] / total_trades) * 100
        gross_profit = overall_stats["total_profit"]
        gross_loss = overall_stats["total_loss"]
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999.0
        
        print(f"TOTAL TRADES: {total_trades}")
        print(f"OVERALL WIN RATE: {avg_win_rate:.2f}%")
        print(f"PROFIT FACTOR: {profit_factor:.2f}")
        print(f"TOTAL NET PROFIT: ${gross_profit - gross_loss:.2f}")
    else:
        print("No completed trades found.")
    print("=" * 60)

if __name__ == "__main__":
    analyze_log()
