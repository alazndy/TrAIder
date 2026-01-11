"""
PORTFOLIO MANAGER
Manages virtual paper trading portfolio with $1000 initial balance.
Tracks positions, executes trades, calculates P&L.
"""
import firebase_admin
from firebase_admin import firestore
from datetime import datetime
from typing import Dict, Optional

class PortfolioManager:
    """Manages paper trading portfolio stored in Firestore."""
    
    INITIAL_BALANCE = 1000.0  # $1000 starting capital
    POSITION_SIZE_PCT = 0.20  # 20% per trade (increased from 10%)
    
    def __init__(self, portfolio_id: str = "default"):
        self.portfolio_id = portfolio_id
        self.db = firestore.client()
        self._init_portfolio()
    
    def _init_portfolio(self):
        """Initialize or load portfolio from Firestore."""
        doc_ref = self.db.collection('portfolios').document(self.portfolio_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            # Create new portfolio
            initial_data = {
                'balance': self.INITIAL_BALANCE,
                'initial_balance': self.INITIAL_BALANCE,
                'positions': {},  # {symbol: {amount, entry_price, entry_time}}
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_profit': 0.0,
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
            }
            doc_ref.set(initial_data)
            print(f"[PORTFOLIO] Created new portfolio with ${self.INITIAL_BALANCE}")
        else:
            data = doc.to_dict()
            print(f"[PORTFOLIO] Loaded portfolio: ${data.get('balance', 0):.2f} balance")
    
    def get_portfolio(self) -> Dict:
        """Get current portfolio state."""
        doc_ref = self.db.collection('portfolios').document(self.portfolio_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            print(f"[PORTFOLIO] Warning: Portfolio document missing. Re-initializing...")
            self._init_portfolio()
            doc = doc_ref.get()
            
        return doc.to_dict() if doc.exists else {}
    
    def get_balance(self) -> float:
        """Get current cash balance."""
        portfolio = self.get_portfolio()
        return portfolio.get('balance', 0)
    
    def get_positions(self) -> Dict:
        """Get current open positions."""
        portfolio = self.get_portfolio()
        return portfolio.get('positions', {})
    
    def get_total_value(self, current_prices: Dict[str, float]) -> float:
        """Calculate total portfolio value (cash + positions)."""
        portfolio = self.get_portfolio()
        balance = portfolio.get('balance', 0)
        positions = portfolio.get('positions', {})
        
        position_value = 0
        for symbol, pos in positions.items():
            price = current_prices.get(symbol, pos.get('entry_price', 0))
            position_value += pos.get('amount', 0) * price
        
        return balance + position_value
    
    def execute_trade(self, symbol: str, signal: str, price: float, confidence: float) -> Optional[Dict]:
        """
        Execute a paper trade based on signal.
        Returns trade details or None if trade not executed.
        """
        if signal not in ['BUY', 'SELL']:
            return None
        
        # Only trade on high confidence signals
        if confidence < 60:
            print(f"  [SKIP] {signal} {symbol}: Confidence {confidence:.1f}% < 60%")
            return None
        
        portfolio = self.get_portfolio()
        balance = portfolio.get('balance', 0)
        positions = portfolio.get('positions', {})
        
        trade = None
        
        if signal == 'BUY' and symbol not in positions:
            # Calculate position size (10% of balance)
            trade_amount = balance * self.POSITION_SIZE_PCT
            if trade_amount < 10:  # Minimum $10 trade
                print(f"  [SKIP] BUY {symbol}: Insufficient balance for min trade (${balance:.2f})")
                return None
            
            amount = trade_amount / price
            
            # Update portfolio
            positions[symbol] = {
                'amount': amount,
                'entry_price': price,
                'entry_time': datetime.utcnow().isoformat(),
                'confidence': confidence
            }
            
            new_balance = balance - trade_amount
            
            trade = {
                'type': 'BUY',
                'symbol': symbol,
                'price': price,
                'amount': amount,
                'value': trade_amount,
                'confidence': confidence,
                'balance_after': new_balance,
                'created_at': datetime.utcnow()
            }
            
            # Save trade to Firestore
            self.db.collection('trades').add(trade)
            
            # Update portfolio
            self.db.collection('portfolios').document(self.portfolio_id).update({
                'balance': new_balance,
                'positions': positions,
                'total_trades': portfolio.get('total_trades', 0) + 1,
                'updated_at': datetime.utcnow()
            })
            
            print(f"  [TRADE] BUY {amount:.4f} {symbol} @ ${price:.4f} (${trade_amount:.2f})")
            
        elif signal == 'SELL' and symbol in positions:
            # Close position
            pos = positions[symbol]
            amount = pos['amount']
            entry_price = pos['entry_price']
            
            # Calculate P&L
            exit_value = amount * price
            entry_value = amount * entry_price
            profit = exit_value - entry_value
            profit_pct = (profit / entry_value) * 100
            
            new_balance = balance + exit_value
            
            # Remove position
            del positions[symbol]
            
            trade = {
                'type': 'SELL',
                'symbol': symbol,
                'price': price,
                'amount': amount,
                'value': exit_value,
                'entry_price': entry_price,
                'profit': profit,
                'profit_pct': profit_pct,
                'confidence': confidence,
                'balance_after': new_balance,
                'created_at': datetime.now()
            }
            
            # Save trade to Firestore
            self.db.collection('trades').add(trade)
            
            # Update portfolio stats
            is_win = profit > 0
            self.db.collection('portfolios').document(self.portfolio_id).update({
                'balance': new_balance,
                'positions': positions,
                'total_trades': portfolio.get('total_trades', 0) + 1,
                'winning_trades': portfolio.get('winning_trades', 0) + (1 if is_win else 0),
                'losing_trades': portfolio.get('losing_trades', 0) + (0 if is_win else 1),
                'total_profit': portfolio.get('total_profit', 0) + profit,
                'updated_at': datetime.now()
            })
            
            symbol_indicator = "🟢" if is_win else "🔴"
            print(f"  [TRADE] SELL {amount:.4f} {symbol} @ ${price:.4f} | P&L: {symbol_indicator} ${profit:.2f} ({profit_pct:+.1f}%)")
        
        return trade
    
    def save_snapshot(self, current_prices: Dict[str, float]):
        """Save portfolio snapshot for historical tracking."""
        total_value = self.get_total_value(current_prices)
        portfolio = self.get_portfolio()
        
        snapshot = {
            'portfolio_id': self.portfolio_id,
            'total_value': total_value,
            'balance': portfolio.get('balance', 0),
            'positions_count': len(portfolio.get('positions', {})),
            'total_trades': portfolio.get('total_trades', 0),
            'total_profit': portfolio.get('total_profit', 0),
            'profit_pct': ((total_value - self.INITIAL_BALANCE) / self.INITIAL_BALANCE) * 100,
            'created_at': datetime.now()
        }
        
        self.db.collection('portfolio_snapshots').add(snapshot)
        print(f"[PORTFOLIO] Snapshot: ${total_value:.2f} ({snapshot['profit_pct']:+.1f}%)")
    
    def get_stats(self) -> Dict:
        """Get portfolio statistics."""
        portfolio = self.get_portfolio()
        total_trades = portfolio.get('total_trades', 0)
        winning = portfolio.get('winning_trades', 0)
        
        return {
            'balance': portfolio.get('balance', 0),
            'initial_balance': portfolio.get('initial_balance', self.INITIAL_BALANCE),
            'total_trades': total_trades,
            'winning_trades': winning,
            'losing_trades': portfolio.get('losing_trades', 0),
            'win_rate': (winning / total_trades * 100) if total_trades > 0 else 0,
            'total_profit': portfolio.get('total_profit', 0),
            'positions': portfolio.get('positions', {}),
        }


# Global instance
portfolio_manager = None

def get_portfolio_manager() -> PortfolioManager:
    """Get or create portfolio manager instance."""
    global portfolio_manager
    if portfolio_manager is None:
        portfolio_manager = PortfolioManager()
    return portfolio_manager
