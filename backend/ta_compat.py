"""
TA Compatibility Wrapper
Provides pandas_ta-like syntax for the 'ta' library.
Usage: import ta_compat as ta
"""
import ta as _ta
import pandas as pd

def rsi(close: pd.Series, length: int = 14) -> pd.Series:
    """Calculate RSI indicator."""
    return _ta.momentum.RSIIndicator(close, window=length).rsi()

def sma(close: pd.Series, length: int = 20) -> pd.Series:
    """Calculate Simple Moving Average."""
    return _ta.trend.SMAIndicator(close, window=length).sma_indicator()

def ema(close: pd.Series, length: int = 20) -> pd.Series:
    """Calculate Exponential Moving Average."""
    return _ta.trend.EMAIndicator(close, window=length).ema_indicator()

def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """Calculate MACD indicator. Returns DataFrame with MACD, histogram, signal."""
    macd_ind = _ta.trend.MACD(close, window_fast=fast, window_slow=slow, window_sign=signal)
    return pd.DataFrame({
        'MACD_12_26_9': macd_ind.macd(),
        'MACDh_12_26_9': macd_ind.macd_diff(),
        'MACDs_12_26_9': macd_ind.macd_signal()
    })

def bbands(close: pd.Series, length: int = 20, std: float = 2.0) -> pd.DataFrame:
    """Calculate Bollinger Bands. Returns DataFrame with upper, middle, lower."""
    bb = _ta.volatility.BollingerBands(close, window=length, window_dev=std)
    return pd.DataFrame({
        f'BBL_{length}_{std}': bb.bollinger_lband(),
        f'BBM_{length}_{std}': bb.bollinger_mavg(),
        f'BBU_{length}_{std}': bb.bollinger_hband()
    })

def atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    """Calculate Average True Range."""
    return _ta.volatility.AverageTrueRange(high, low, close, window=length).average_true_range()

def adx(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.DataFrame:
    """Calculate ADX indicator. Returns DataFrame with ADX, DMP, DMN."""
    adx_ind = _ta.trend.ADXIndicator(high, low, close, window=length)
    return pd.DataFrame({
        f'ADX_{length}': adx_ind.adx(),
        f'DMP_{length}': adx_ind.adx_pos(),
        f'DMN_{length}': adx_ind.adx_neg()
    })

def roc(close: pd.Series, length: int = 10) -> pd.Series:
    """Calculate Rate of Change."""
    return _ta.momentum.ROCIndicator(close, window=length).roc()

def stoch(high: pd.Series, low: pd.Series, close: pd.Series, k: int = 14, d: int = 3) -> pd.DataFrame:
    """Calculate Stochastic Oscillator. Returns DataFrame with STOCHk and STOCHd."""
    stoch_ind = _ta.momentum.StochasticOscillator(high, low, close, window=k, smooth_window=d)
    return pd.DataFrame({
        f'STOCHk_{k}_{d}_3': stoch_ind.stoch(),
        f'STOCHd_{k}_{d}_3': stoch_ind.stoch_signal()
    })

def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """Calculate On-Balance Volume."""
    return _ta.volume.OnBalanceVolumeIndicator(close, volume).on_balance_volume()

def cci(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 20) -> pd.Series:
    """Calculate Commodity Channel Index."""
    return _ta.trend.CCIIndicator(high, low, close, window=length).cci()

def willr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    """Calculate Williams %R."""
    return _ta.momentum.WilliamsRIndicator(high, low, close, lbp=length).williams_r()
