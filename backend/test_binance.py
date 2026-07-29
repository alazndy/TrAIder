
import ccxt
import sys

try:
    print("Initializing Binance...")
    binance = ccxt.binance()
    print("Fetching Time...")
    time = binance.fetch_time()
    print(f"Time: {time}")
    print("Fetching BTC/USDT Ticker...")
    ticker = binance.fetch_ticker("BTC/USDT")
    print(f"BTC Price: {ticker['last']}")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
