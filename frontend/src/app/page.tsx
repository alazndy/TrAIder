'use client';

import { useEffect, useState } from 'react';
import { ChartComponent } from '@/components/ChartComponent';
import { api, HealthStatus, RSIResponse, TickerResponse, Candle, StrategyResult, BacktestResult, BotStatus } from '@/services/api';

export default function Home() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [rsi, setRsi] = useState<RSIResponse | null>(null);
  const [ticker, setTicker] = useState<TickerResponse | null>(null);
  const [chartData, setChartData] = useState<Candle[]>([]);
  const [strategyResult, setStrategyResult] = useState<StrategyResult | null>(null);
  const [backtestResult, setBacktestResult] = useState<BacktestResult | null>(null);
  const [botStatus, setBotStatus] = useState<BotStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [symbol, setSymbol] = useState('BTC');
  const [selectedStrategy, setSelectedStrategy] = useState('sma_crossover');

  useEffect(() => {
    // Check Backend Connection on Mount
    api.checkHealth().then(setHealth);
    // Also get bot status
    api.getBotStatus().then(setBotStatus).catch(() => {});
  }, []);

  // Polling for bot status when running
  useEffect(() => {
    if (botStatus?.is_running) {
      const interval = setInterval(() => {
        api.getBotStatus().then(setBotStatus).catch(() => {});
      }, 3000); // Poll every 3 seconds
      return () => clearInterval(interval);
    }
  }, [botStatus?.is_running]);

  const handleStartBot = async () => {
    try {
      await api.startBot(symbol);
      const status = await api.getBotStatus();
      setBotStatus(status);
    } catch (err) {
      console.error(err);
    }
  };

  const handleStopBot = async () => {
    try {
      await api.stopBot();
      const status = await api.getBotStatus();
      setBotStatus(status);
    } catch (err) {
      console.error(err);
    }
  };

  const handleRunStrategy = async () => {
    try {
        const result = await api.runStrategy(selectedStrategy, symbol);
        setStrategyResult(result);
    } catch (err) {
        console.error(err);
    }
  };

  const handleRunBacktest = async () => {
    try {
        setLoading(true);
        const result = await api.runBacktest('sma_crossover', symbol);
        setBacktestResult(result);
    } catch (err) {
        console.error(err);
    } finally {
        setLoading(false);
    }
  };


  const fetchData = async () => {
    try {
      setLoading(true);
      const [tickerData, candlesData] = await Promise.all([
        api.getTicker(symbol),
        api.getCandles(symbol)
      ]);
      setTicker(tickerData);
      setChartData(candlesData);
    } catch (err) {
      console.error("Failed to fetch data", err);
    } finally {
        setLoading(false);
    }
  };

  const handleTestRSI = async () => {
    setLoading(true);
    // Mock Data (Random Walk)
    const mockPrices = Array.from({ length: 50 }, () => Math.random() * 100 + 100);
    try {
      const result = await api.calculateRSI(mockPrices);
      setRsi(result);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24 bg-zinc-950 text-white font-sans">
      <div className="z-10 max-w-5xl w-full items-center justify-center font-mono text-sm lg:flex flex-col gap-8">
        
        <h1 className="text-4xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
          TrAIder Hybrid Platform
        </h1>

        <div className="grid grid-cols-2 gap-8 w-full">
          {/* Backend Status Card */}
          <div className="p-6 rounded-xl border border-zinc-800 bg-zinc-900/50 backdrop-blur-sm">
            <h2 className="text-xl font-semibold mb-4 text-zinc-400">System Status</h2>
            <div className="flex items-center gap-2">
              <span className="text-zinc-500">Backend Engine:</span>
              <span className={`px-2 py-1 rounded text-xs font-bold ${
                health?.status === 'Active' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'
              }`}>
                {health?.status || 'Checking...'}
              </span>
            </div>
          </div>

          {/* RSI Test Card */}
          <div className="p-6 rounded-xl border border-zinc-800 bg-zinc-900/50 backdrop-blur-sm">
            <h2 className="text-xl font-semibold mb-4 text-zinc-400">Indicator Test (RSI)</h2>
            <button
              onClick={handleTestRSI}
              disabled={loading || health?.status !== 'Active'}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Calculating...' : 'Run RSI Calculation'}
            </button>

            {rsi && (
              <div className="mt-4 p-4 rounded bg-zinc-800/50 border border-zinc-700">
                <div className="flex justify-between mb-2">
                  <span>Value:</span>
                  <span className="font-mono text-yellow-400">{rsi.value}</span>
                </div>
                <div className="flex justify-between">
                  <span>Signal:</span>
                  <span className={`font-bold ${
                    rsi.signal === 'BUY' ? 'text-emerald-400' : 
                    rsi.signal === 'SELL' ? 'text-red-400' : 'text-zinc-400'
                  }`}>
                    {rsi.signal}
                  </span>
                </div>
              </div>
            )}

          </div>
          
          {/* Market Data Card */}
          <div className="p-6 rounded-xl border border-zinc-800 bg-zinc-900/50 backdrop-blur-sm">
            <h2 className="text-xl font-semibold mb-4 text-zinc-400">Live Market</h2>
            <div className="flex gap-2 mb-4">
              <input
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                className="bg-zinc-800 border-zinc-700 border rounded px-3 py-1 text-white w-24 text-center font-mono"
              />
              <button
                onClick={fetchData}
                className="px-4 py-1 bg-emerald-600 hover:bg-emerald-500 rounded text-white transition-colors"
                disabled={health?.status !== 'Active' || loading}
              >
                {loading ? 'Thinking...' : 'Fetch'}
              </button>
            </div>
            {ticker && (
              <div className="flex flex-col items-center p-4 bg-zinc-800/50 rounded border border-zinc-700">
                <span className="text-sm text-zinc-500">{ticker.symbol}</span>
                <span className="text-3xl font-mono font-bold text-white tracking-tighter">
                  ${ticker.price.toLocaleString()}
                </span>
                <span className="text-xs text-zinc-600 mt-2">
                  {new Date(ticker.timestamp).toLocaleTimeString()}
                </span>
              </div>
            )}

          </div>
          
          {/* Market Data & Chart */}
          <div className="col-span-2 p-6 rounded-xl border border-zinc-800 bg-zinc-900/50 backdrop-blur-sm">
             <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold text-zinc-400">Live Chart ({symbol})</h2>
                <div className="flex gap-2">
                  <span className="text-xs text-zinc-500 self-center">1H Timeframe</span>
                </div>
             </div>
             
             {chartData.length > 0 ? (
                <ChartComponent data={chartData} />
             ) : (
                <div className="h-[400px] flex items-center justify-center text-zinc-600 bg-zinc-950/30 rounded-lg">
                  Load data to see chart...
                </div>
             )}
          </div>

          {/* Strategy Runner Card */}
          <div className="col-span-2 p-6 rounded-xl border border-zinc-800 bg-zinc-900/50 backdrop-blur-sm">
            <h2 className="text-xl font-semibold mb-4 text-zinc-400">Strategy Engine</h2>
            <div className="flex gap-4 items-end">
               <div className="flex flex-col gap-1">
                 <label className="text-xs text-zinc-500">Strategy</label>
                 <select 
                   value={selectedStrategy}
                   onChange={(e) => setSelectedStrategy(e.target.value)}
                   className="bg-zinc-800 border-zinc-700 border rounded px-3 py-2 text-white w-64"
                 >
                    <optgroup label="Trend Following">
                      <option value="sma_crossover">SMA Crossover (10/20)</option>
                      <option value="supertrend">SuperTrend (EMA)</option>
                      <option value="macd">MACD Crossover</option>
                      <option value="breakout">Breakout (N-Day)</option>
                    </optgroup>
                    <optgroup label="Mean Reversion">
                      <option value="mean_reversion">Mean Reversion (RSI)</option>
                      <option value="dip_hunter">Dip Hunter</option>
                      <option value="bollinger">Bollinger Bands</option>
                    </optgroup>
                    <optgroup label="Other Strategies">
                      <option value="momentum">Momentum (ROC)</option>
                      <option value="grid">Grid Trading</option>
                      <option value="dca">DCA (Avg Down)</option>
                    </optgroup>
                     <optgroup label="AI / Machine Learning">
                       <option value="ai">🤖 AI Strategy (Basic)</option>
                       <option value="adaptive_ai">🧠 Adaptive AI (Multi-Mode)</option>
                     </optgroup>
                 </select>
               </div>
               <button 
                 onClick={handleRunStrategy}
                 disabled={loading}
                 className="px-6 py-2 bg-purple-600 hover:bg-purple-500 rounded text-white transition-colors h-[42px]"
               >
                 Analyze Market
               </button>
            </div>

            {strategyResult && (
               <div className="mt-6 p-4 bg-zinc-800/50 border border-zinc-700 rounded-lg flex justify-between items-center">
                  <div>
                    <div className="text-zinc-400 text-sm">Signal Reason</div>
                    <div className="font-mono text-yellow-400">{strategyResult.result.reason}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-zinc-400 text-sm">Action</div>
                    <div className={`text-2xl font-bold ${
                        strategyResult.result.signal === 'BUY' ? 'text-emerald-400' : 
                        strategyResult.result.signal === 'SELL' ? 'text-red-400' : 'text-zinc-500'
                    }`}>
                        {strategyResult.result.signal}
                    </div>
                  </div>
               </div>
            )}
          </div>

          {/* Backtest Runner Card */}
          <div className="col-span-2 p-6 rounded-xl border border-zinc-800 bg-zinc-900/50 backdrop-blur-sm">
            <h2 className="text-xl font-semibold mb-4 text-zinc-400">Backtest Engine</h2>
            <div className="flex gap-4 items-end">
               <div className="flex flex-col gap-1">
                 <label className="text-xs text-zinc-500">Strategy</label>
                 <select className="bg-zinc-800 border-zinc-700 border rounded px-3 py-2 text-white w-48">
                    <option value="sma_crossover">SMA Crossover (10/20)</option>
                 </select>
               </div>
               <button 
                 onClick={handleRunBacktest}
                 disabled={loading}
                 className="px-6 py-2 bg-orange-600 hover:bg-orange-500 rounded text-white transition-colors h-[42px]"
               >
                 Run Backtest (500h)
               </button>
            </div>

            {backtestResult && (
               <div className="mt-6 grid grid-cols-4 gap-4">
                  <div className="p-4 bg-zinc-800/50 border border-zinc-700 rounded-lg">
                    <div className="text-zinc-400 text-xs">Total Trades</div>
                    <div className="text-xl font-mono text-white">{backtestResult.results.total_trades}</div>
                  </div>
                  <div className="p-4 bg-zinc-800/50 border border-zinc-700 rounded-lg">
                    <div className="text-zinc-400 text-xs">Win Rate</div>
                    <div className="text-xl font-mono text-emerald-400">{backtestResult.results.win_rate}%</div>
                  </div>
                  <div className="p-4 bg-zinc-800/50 border border-zinc-700 rounded-lg">
                    <div className="text-zinc-400 text-xs">Initial Capital</div>
                    <div className="text-xl font-mono text-zinc-500">${backtestResult.results.initial_capital}</div>
                  </div>
                  <div className="p-4 bg-zinc-800/50 border border-zinc-700 rounded-lg">
                    <div className="text-zinc-400 text-xs">Final Equity</div>
                    <div className={`text-xl font-mono font-bold ${
                        backtestResult.results.final_equity >= backtestResult.results.initial_capital 
                        ? 'text-emerald-400' : 'text-red-400'
                    }`}>
                        ${backtestResult.results.final_equity}
                    </div>
                  </div>
               </div>
            )}
          </div>

          {/* Bot Control Panel */}
          <div className="col-span-2 p-6 rounded-xl border-2 border-cyan-800 bg-zinc-900/50 backdrop-blur-sm">
            <h2 className="text-xl font-semibold mb-4 text-cyan-400">🤖 Paper Trading Bot</h2>
            <div className="flex gap-4 items-center">
               <button 
                 onClick={handleStartBot}
                 disabled={botStatus?.is_running}
                 className="px-6 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded text-white transition-colors"
               >
                 Start Bot
               </button>
               <button 
                 onClick={handleStopBot}
                 disabled={!botStatus?.is_running}
                 className="px-6 py-2 bg-red-600 hover:bg-red-500 disabled:opacity-50 rounded text-white transition-colors"
               >
                 Stop Bot
               </button>
               <span className={`px-3 py-1 rounded-full text-sm font-bold ${
                   botStatus?.is_running ? 'bg-green-500/20 text-green-400 animate-pulse' : 'bg-zinc-700 text-zinc-400'
               }`}>
                   {botStatus?.is_running ? '● RUNNING' : '○ STOPPED'}
               </span>
            </div>

            {botStatus && (
               <div className="mt-6 grid grid-cols-3 gap-4">
                  <div className="p-4 bg-zinc-800/50 border border-zinc-700 rounded-lg">
                    <div className="text-zinc-400 text-xs">Available Balance</div>
                    <div className="text-xl font-mono text-white">${botStatus.balance.toFixed(2)}</div>
                  </div>
                  <div className="p-4 bg-zinc-800/50 border border-zinc-700 rounded-lg">
                    <div className="text-zinc-400 text-xs">Total Trades</div>
                    <div className="text-xl font-mono text-white">{botStatus.total_trades}</div>
                  </div>
                  {botStatus.position && (
                    <div className="p-4 bg-cyan-900/30 border border-cyan-700 rounded-lg">
                      <div className="text-cyan-400 text-xs">Active Position ({botStatus.position.symbol})</div>
                      <div className="text-lg font-mono text-white">
                        {botStatus.position.amount.toFixed(4)} @ ${botStatus.position.entry_price.toFixed(2)}
                      </div>
                      <div className={`text-sm font-bold ${botStatus.position.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        PnL: ${botStatus.position.pnl.toFixed(2)}
                      </div>
                    </div>
                  )}
               </div>
            )}
          </div>
        </div>

      </div>
    </main>
  );
}
