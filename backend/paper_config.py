"""
Paper Trading Configuration (The "Golden List")
Production Portfolio for Live Simulation.
"""

PAPER_PORTFOLIO = [
    # 🚀 MOMENTUM / HYPE (Standard AI)
    {"symbol": "PEPE/USDT", "strategy": "adaptive_ai", "desc": "Meme King"},
    {"symbol": "FET/USDT",  "strategy": "adaptive_ai", "desc": "AI Trend"},
    {"symbol": "DOT/USDT",  "strategy": "adaptive_ai", "desc": "L1 Reversal"},
    
    # 🧠 SMART / DEFENSIVE (Proteus Neo)
    {"symbol": "XRP/USDT",  "strategy": "proteus_neo", "desc": "Market Aware"},
    {"symbol": "ARB/USDT",  "strategy": "proteus_neo", "desc": "L2 Beta"},
    {"symbol": "SHIB/USDT", "strategy": "proteus_neo", "desc": "Defensive Meme"},
    {"symbol": "BONK/USDT", "strategy": "proteus_neo", "desc": "Solana Beta"},
    {"symbol": "TIA/USDT",  "strategy": "proteus_neo", "desc": "New Tech"}
]

CAPITAL_PER_ASSET = 125.0  # $1000 Total
