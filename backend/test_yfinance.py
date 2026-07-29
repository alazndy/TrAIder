
import yfinance as yf
import sys

try:
    print("Fetching BTC-USD from YFinance...")
    data = yf.download("BTC-USD", start="2020-01-01", limit=5)
    if data.empty:
        print("Empty Data")
        sys.exit(1)
    print(data.head())
    print("Success")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
