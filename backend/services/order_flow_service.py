
import ccxt
import pandas as pd

class OrderFlowIntelligence:
    """
    Borsadaki derinlik (L2) verisini analiz eder.
    """
    def __init__(self, exchange=None):
        self.exchange = exchange or ccxt.binance()

    def get_market_pressure(self, symbol):
        """
        Alış ve satış duvarları arasındaki güç savaşını ölçer.
        """
        try:
            # Derinlik verisini çek (ilk 50 emir)
            order_book = self.exchange.fetch_order_book(symbol, limit=50)
            
            bids = order_book['bids'] # Alışlar [[price, vol], ...]
            asks = order_book['asks'] # Satışlar
            
            total_bid_vol = sum([b[1] for b in bids])
            total_ask_vol = sum([a[1] for a in asks])
            
            # Imbalance (Dengesizlik) Oranı
            # > 1 ise Alıcılar daha güçlü, < 1 ise Satıcılar
            imbalance = total_bid_vol / total_ask_vol if total_ask_vol > 0 else 1
            
            # Duvar tespiti (Ortalamanın 5 katı büyüklükte emir var mı?)
            avg_bid = total_bid_vol / 50
            big_walls = [b[0] for b in bids if b[1] > avg_bid * 5]
            
            return {
                "imbalance": round(imbalance, 2),
                "is_bullish_pressure": imbalance > 1.5,
                "is_bearish_pressure": imbalance < 0.6,
                "support_walls": big_walls[:3]
            }
        except:
            return {"imbalance": 1.0, "is_bullish_pressure": False, "is_bearish_pressure": False, "support_walls": []}

order_flow_engine = OrderFlowIntelligence()
