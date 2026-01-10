from abc import ABC, abstractmethod
from typing import Dict, Any, List
import pandas as pd

class BaseStrategy(ABC):
    def __init__(self, parameters: Dict[str, Any]):
        self.parameters = parameters
        self.name = "BaseStrategy"

    @abstractmethod
    def analyze(self, candles: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyzes the given candles and returns a signal/result.
        candles: DataFrame with columns ['time', 'open', 'high', 'low', 'close', 'volume']
        """
        pass
