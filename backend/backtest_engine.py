import pandas as pd
from typing import List, Dict, Any
from strategies import get_strategy

class BacktestEngine:
    def __init__(self, initial_balance: float = 1000.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.trades = []
        self.current_position = None # None or 'BUY'

    def run(self, strategy_id: str, parameters: dict, candles: pd.DataFrame):
        strategy = get_strategy(strategy_id, parameters)
        if not strategy:
            raise ValueError(f"Strategy {strategy_id} not found")

        # Simulate iterating through data
        # Note: Real backtesting needs to step through time. 
        # For simplicity and speed in this version, we will re-calculate indicators mostly via pandas_ta in valid windows
        # But to simulate signal generation correctly, we iterate row by row.
        
        # Pre-calculation (Vectorized) - usually done inside strategy.analyze in a real vectorized engine
        # But our strategy.analyze currently takes the whole DF. 
        # So we have to simulate the "growing" dataframe or just pass the full DF 
        # and be careful not to look ahead.
        
        # Strategy `analyze` method currently calculates on the WHOLE dataframe.
        # This is efficient. We just need to check the signals row by row.
        
        full_analysis = strategy.analyze(candles)
        
        # We need the signals aligned with time
        # The strategy 'analyze' currently returns the LATEST signal. 
        # We need to modifier strategy to return SERIES of signals or we simulate step-by-step.
        
        # For Phase 3 MVP: We will modify Strategy to return columns in DF.
        
        # Let's do a simple iteration for now (slow but accurate logic).
        # Optimization can come later.
        
        # NOTE: To use the existing 'analyze' which returns a SINGLE dict, we would have to loop.
        # LOOPING IS SLOW.
        # Better approach: Update BaseStrategy to allow returning the modified DataFrame with columns 'signal'.
        
        pass

    def calculate_stats(self):
        df_trades = pd.DataFrame(self.trades)
        if df_trades.empty:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "total_profit": 0,
                "final_balance": self.initial_balance
            }
        
        wins = df_trades[df_trades['profit'] > 0]
        total_profit = df_trades['profit'].sum()
        
        return {
            "total_trades": len(df_trades),
            "win_rate": len(wins) / len(df_trades),
            "total_profit": round(total_profit, 2),
            "final_balance": round(self.initial_balance + total_profit, 2),
            "trades": self.trades
        }

# Simple Event-Driven Backtester
class SimpleBacktester:
    def __init__(self, initial_capital=1000, fee_rate=0.001):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.fee_rate = fee_rate
        self.position = 0 # 0 = Flat, >0 = Asset Amount
        self.trades = []
        self.equity_curve = []

    def run(self, strategy, df: pd.DataFrame):
        # We assume the strategy has added 'signal' (1=Buy, -1=Sell, 0=Neutral) column or similar logic
        # But our current strategy returns a Dict for the *latest* candle.
        # We need to wrap it to work on history.
        
        # Hack for MVP: Calculate indicators on full DF first (Vectorized)
        
        # 1. Calculate Indicators
        df = self._calculate_indicators(strategy, df)
        
        # 2. Iterate
        for i in range(strategy.slow_period, len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            price = row['close']
            date = row['time'] # timestamp
            
            # Logic from SMACrossoverStrategy reproduced for backtesting sequence
            # (Ideally we'd share this logic better)
            
            signal = 0
            # Golden Cross
            if prev_row['fast_sma'] <= prev_row['slow_sma'] and row['fast_sma'] > row['slow_sma']:
                signal = 1
            # Death Cross
            elif prev_row['fast_sma'] >= prev_row['slow_sma'] and row['fast_sma'] < row['slow_sma']:
                signal = -1
                
            # Execute Trade
            if signal == 1 and self.position == 0:
                # BUY
                amount = (self.capital * (1 - self.fee_rate)) / price
                cost = amount * price
                self.capital -= cost # should be near 0
                self.position = amount
                self.trades.append({
                    "type": "BUY",
                    "price": price,
                    "time": date,
                    "balance": self.capital
                })
                
            elif signal == -1 and self.position > 0:
                # SELL
                revenue = (self.position * price) * (1 - self.fee_rate)
                profit = revenue - (self.trades[-1]['price'] * self.trades[-1]['type']=='BUY') # Simplified logic, need better tracking
                
                # Correct Profit calc:
                entry_price = self.trades[-1]['price']
                trade_profit = (price - entry_price) * self.position
                
                self.capital += revenue
                self.position = 0
                self.trades.append({
                    "type": "SELL",
                    "price": price,
                    "time": date,
                    "balance": self.capital,
                    "profit": trade_profit
                })
                
            self.equity_curve.append({"time": date, "equity": self.get_equity(price)})
            
        return self._get_results()

    def get_equity(self, current_price):
        if self.position > 0:
            return self.capital + (self.position * current_price)
        return self.capital

    def _calculate_indicators(self, strategy, df):
        import ta_compat as ta
        # Apply strategy logic to full DF
        df["fast_sma"] = ta.sma(df["close"], length=strategy.fast_period)
        df["slow_sma"] = ta.sma(df["close"], length=strategy.slow_period)
        return df

    def _get_results(self):
        total_trades = len([t for t in self.trades if t['type'] == 'SELL'])
        wins = len([t for t in self.trades if t.get('profit', 0) > 0])
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        return {
            "initial_capital": self.initial_capital,
            "final_equity": round(self.equity_curve[-1]['equity'] if self.equity_curve else self.initial_capital, 2),
            "total_trades": total_trades,
            "win_rate": round(win_rate, 2),
            "trades": self.trades[-10:] # Last 10 trades
        }
