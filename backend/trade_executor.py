from datetime import datetime
from typing import Dict, Any, Optional

class TradeExecutor:
    def __init__(self, initial_balance: float = 1000.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance # Available USDT
        self.position: Optional[Dict[str, Any]] = None # Current position info
        self.trades = []
        self.is_running = False

    def get_status(self):
        return {
            "is_running": self.is_running,
            "balance": self.balance,
            "position": self.position,
            "total_trades": len(self.trades)
        }

    def execute_signal(self, signal: str, symbol: str, price: float, time: int):
        if not self.is_running:
            return

        # Simple Logic: 
        # BUY if signal is BUY and we have no position.
        # SELL if signal is SELL and we have a position.

        if signal == "BUY" and self.position is None:
            # Buy with all balance
            amount = self.balance / price
            cost = amount * price
            self.balance = 0 # All in
            
            self.position = {
                "symbol": symbol,
                "amount": amount,
                "entry_price": price,
                "entry_time": time,
                "current_price": price,
                "pnl": 0
            }
            
            self.trades.append({
                "type": "BUY",
                "symbol": symbol,
                "price": price,
                "amount": amount,
                "time": time
            })
            print(f"[{datetime.now()}] BUY EXECUTED: {amount:.4f} {symbol} @ ${price}")
            
            # Save to Firebase
            try:
                from services.firebase_service import firebase_client
                firebase_client.save_trade({
                    "type": "BUY",
                    "symbol": symbol,
                    "price": price,
                    "amount": amount,
                    "cost": cost,
                    "time": time
                }, strategy_id="manual_or_bot")
            except ImportError:
                pass

        elif signal == "SELL" and self.position is not None:
            # Sell everything
            amount = self.position["amount"]
            revenue = amount * price
            profit = revenue - (amount * self.position["entry_price"])
            
            self.balance = revenue
            trade_record = {
                "type": "SELL",
                "symbol": symbol,
                "price": price,
                "amount": amount,
                "profit": profit,
                "time": time
            }
            self.trades.append(trade_record)
            
            print(f"[{datetime.now()}] SELL EXECUTED: {amount:.4f} {symbol} @ ${price} (PnL: ${profit:.2f})")
            
            # Save to Firebase
            try:
                from services.firebase_service import firebase_client
                firebase_client.save_trade(trade_record, strategy_id="manual_or_bot")
            except ImportError:
                pass

            self.position = None

    def update_position_value(self, current_price: float):
        if self.position:
            self.position["current_price"] = current_price
            self.position["pnl"] = (current_price - self.position["entry_price"]) * self.position["amount"]
