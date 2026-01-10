import axios from 'axios';

const API_URL = 'http://localhost:8000';

export interface HealthStatus {
  status: string;
}

export interface RSIResponse {
  name: string;
  value: number;
  signal: 'BUY' | 'SELL' | 'NEUTRAL';
}

export interface TickerResponse {
  symbol: string;
  price: number;
  timestamp: number;
}

export const api = {
  checkHealth: async (): Promise<HealthStatus> => {
    try {
      const response = await axios.get(`${API_URL}/`);
      return response.data;
    } catch (error) {
      console.error('Backend connection failed:', error);
      return { status: 'Disconnected' };
    }
  },

  calculateRSI: async (prices: number[], period: number = 14): Promise<RSIResponse> => {
    const response = await axios.post(`${API_URL}/api/v1/indicators/rsi`, {
      prices,
      period,
    });
    return response.data;
  },

  getTicker: async (symbol: string): Promise<TickerResponse> => {
    const response = await axios.get(`${API_URL}/api/v1/market/ticker/${symbol}`);
    return response.data;
  },

  getCandles: async (symbol: string, timeframe: string = '1h'): Promise<Candle[]> => {
    const response = await axios.get(`${API_URL}/api/v1/market/candles/${symbol}`, {
      params: { timeframe }
    });
    return response.data;
  },

  runStrategy: async (strategyId: string, symbol: string, parameters: any = {}): Promise<StrategyResult> => {
    const response = await axios.post(`${API_URL}/api/v1/strategy/run`, {
      strategy_id: strategyId,
      symbol,
      timeframe: '1h',
      parameters
    });
    return response.data;
  },

  runBacktest: async (strategyId: string, symbol: string): Promise<BacktestResult> => {
    const response = await axios.post(`${API_URL}/api/v1/backtest/run`, {
      strategy_id: strategyId,
      symbol,
      timeframe: '1h',
      limit: 500
    });
    return response.data;
  },

  startBot: async (symbol: string): Promise<any> => {
    return (await axios.post(`${API_URL}/api/v1/bot/start`, null, { params: { symbol } })).data;
  },

  stopBot: async (): Promise<any> => {
    return (await axios.post(`${API_URL}/api/v1/bot/stop`)).data;
  },

  getBotStatus: async (): Promise<BotStatus> => {
    return (await axios.get(`${API_URL}/api/v1/bot/status`)).data;
  }
};

export interface BotStatus {
  is_running: boolean;
  balance: number;
  position: {
    symbol: string;
    amount: number;
    entry_price: number;
    current_price: number;
    pnl: number;
  } | null;
  total_trades: number;
}


export interface BacktestResult {
  symbol: string;
  results: {
    initial_capital: number;
    final_equity: number;
    total_trades: number;
    win_rate: number;
    trades: any[];
  };
}

export interface StrategyResult {
  strategy: string;
  symbol: string;
  result: {
    signal: 'BUY' | 'SELL' | 'NEUTRAL';
    reason: string;
    fast_sma?: number;
    slow_sma?: number;
  };
}

export interface Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}
