from strategies.sma_crossover import SMACrossoverStrategy
from strategies.mean_reversion import MeanReversionStrategy
from strategies.momentum import MomentumStrategy
from strategies.bollinger import BollingerBandStrategy
from strategies.grid import GridStrategy
from strategies.dca import DCAStrategy
from strategies.supertrend import SuperTrendStrategy
from strategies.dip_hunter import DipHunterStrategy
from strategies.macd import MACDStrategy
from strategies.breakout import BreakoutStrategy
from strategies.ai_strategy import AIStrategy
from strategies.adaptive_ai import AdaptiveAIStrategy
from strategies.adaptive_ai_enhanced import ProteusAI

# Registry of available strategies
from .proteus_neo import ProteusNeo

STRATEGIES = {
    "sma_crossover": SMACrossoverStrategy,
    "mean_reversion": MeanReversionStrategy,
    "momentum": MomentumStrategy,
    "bollinger": BollingerBandStrategy,
    "grid": GridStrategy,
    "dca": DCAStrategy,
    "supertrend": SuperTrendStrategy,
    "dip_hunter": DipHunterStrategy,
    "macd": MACDStrategy,
    "breakout": BreakoutStrategy,
    "ai": AIStrategy,
    "adaptive_ai": AdaptiveAIStrategy,
    "proteus": ProteusAI,
    "proteus_neo": ProteusNeo
}

def get_strategy(strategy_id: str, parameters: dict):
    strategy_class = STRATEGIES.get(strategy_id)
    if strategy_class:
        return strategy_class(parameters)
    return None




