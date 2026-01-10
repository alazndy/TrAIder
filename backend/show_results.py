from run_2025_backtest import run_all_backtests

results = run_all_backtests("BTC/USDT")

print("\n\n" + "=" * 50)
print("           *** FINAL RESULTS ***")
print("=" * 50)

for i, r in enumerate(results, 1):
    print(f"\n{i}. {r['strategy']}")
    print(f"   Final Capital: ${r['final_capital']:.2f}")
    print(f"   Total Profit:  ${r['total_profit']:+.2f}")
    print(f"   ROI:           {r['roi_percent']:+.2f}%")
    print(f"   Trades:        {r['total_trades']}")
    print(f"   Win Rate:      {r['win_rate']}%")
