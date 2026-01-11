"use client";

import { useEffect, useState, useRef } from "react";
import { db } from "@/lib/firebase";
import { collection, query, orderBy, limit, onSnapshot } from "firebase/firestore";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Activity, TrendingUp, TrendingDown, Zap, Bell, BellOff, Volume2, VolumeX, Wallet, Target, BarChart3, PieChart } from "lucide-react";

interface Signal {
  id: string;
  symbol: string;
  strategy: string;
  signal: string;
  confidence: number;
  price: number;
  mode: string;
  desc: string;
  created_at: { seconds: number } | null;
}

interface PortfolioStats {
  totalTrades: number;
  winRate: number;
  totalProfit: number;
  todayProfit: number;
  avgConfidence: number;
  bestSymbol: string;
  worstSymbol: string;
  symbolStats: Record<string, { buys: number; sells: number; neutral: number }>;
}

interface Portfolio {
  balance: number;
  initial_balance: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  total_profit: number;
  positions: Record<string, { amount: number; entry_price: number }>;
}

interface TradeRecord {
  id: string;
  type: string;
  symbol: string;
  price: number;
  amount: number;
  value: number;
  profit?: number;
  profit_pct?: number;
  created_at: { seconds: number } | null;
}

export default function Dashboard() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [trades, setTrades] = useState<TradeRecord[]>([]);
  const [portfolio, setPortfolio] = useState<Portfolio>({
    balance: 1000,
    initial_balance: 1000,
    total_trades: 0,
    winning_trades: 0,
    losing_trades: 0,
    total_profit: 0,
    positions: {},
  });
  const [stats, setStats] = useState({
    active_signals: 0,
    buy_signals: 0,
    sell_signals: 0,
  });
  const [portfolioStats, setPortfolioStats] = useState<PortfolioStats>({
    totalTrades: 0,
    winRate: 0,
    totalProfit: 0,
    todayProfit: 0,
    avgConfidence: 0,
    bestSymbol: "-",
    worstSymbol: "-",
    symbolStats: {},
  });
  const [notificationsEnabled, setNotificationsEnabled] = useState(false);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [lastSignalCount, setLastSignalCount] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Request notification permission
  const requestNotificationPermission = async () => {
    if ("Notification" in window) {
      const permission = await Notification.requestPermission();
      setNotificationsEnabled(permission === "granted");
    }
  };

  // Play notification sound
  const playSound = () => {
    if (soundEnabled && audioRef.current) {
      audioRef.current.play().catch(() => {});
    }
  };

  // Send browser notification
  const sendNotification = (title: string, body: string, icon?: string) => {
    if (notificationsEnabled && "Notification" in window) {
      new Notification(title, {
        body,
        icon: icon || "/next.svg",
        badge: "/next.svg",
        tag: "traider-signal",
      });
    }
  };

  useEffect(() => {
    // Listen to real-time signals
    const q = query(
      collection(db, "signals"),
      orderBy("created_at", "desc"),
      limit(100) // Get more signals for stats
    );

    const unsubscribe = onSnapshot(q, (snapshot) => {
      const msgs: Signal[] = [];
      let buy = 0;
      let sell = 0;
      let totalConfidence = 0;
      const symbolStats: Record<string, { buys: number; sells: number; neutral: number }> = {};

      snapshot.forEach((doc) => {
        const data = doc.data() as Signal;
        msgs.push({ ...data, id: doc.id });
        
        if (data.signal === "BUY") buy++;
        if (data.signal === "SELL") sell++;
        totalConfidence += data.confidence || 0;

        // Track symbol stats
        if (!symbolStats[data.symbol]) {
          symbolStats[data.symbol] = { buys: 0, sells: 0, neutral: 0 };
        }
        if (data.signal === "BUY") symbolStats[data.symbol].buys++;
        else if (data.signal === "SELL") symbolStats[data.symbol].sells++;
        else symbolStats[data.symbol].neutral++;
      });

      // Check for new signals
      if (msgs.length > lastSignalCount && lastSignalCount > 0) {
        const newSignal = msgs[0];
        playSound();
        sendNotification(
          `${newSignal.signal} Signal: ${newSignal.symbol}`,
          `${newSignal.strategy} | Confidence: ${newSignal.confidence.toFixed(1)}% | $${newSignal.price.toFixed(4)}`
        );
      }
      setLastSignalCount(msgs.length);

      // Calculate portfolio stats
      const avgConfidence = msgs.length > 0 ? totalConfidence / msgs.length : 0;
      
      // Find best/worst symbols
      let bestSymbol = "-";
      let worstSymbol = "-";
      let maxBuys = 0;
      let maxSells = 0;

      Object.entries(symbolStats).forEach(([symbol, stats]) => {
        if (stats.buys > maxBuys) {
          maxBuys = stats.buys;
          bestSymbol = symbol.replace("/USDT", "");
        }
        if (stats.sells > maxSells) {
          maxSells = stats.sells;
          worstSymbol = symbol.replace("/USDT", "");
        }
      });

      // Today's signals
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const todaySignals = msgs.filter(s => 
        s.created_at && s.created_at.seconds * 1000 >= today.getTime()
      );

      setSignals(msgs.slice(0, 20)); // Show only last 20 in table
      setStats({
        active_signals: msgs.length,
        buy_signals: buy,
        sell_signals: sell,
      });
      setPortfolioStats({
        totalTrades: msgs.length,
        winRate: msgs.length > 0 ? (buy / msgs.length) * 100 : 0,
        totalProfit: 0, // Would come from trades collection
        todayProfit: todaySignals.length,
        avgConfidence,
        bestSymbol,
        worstSymbol,
        symbolStats,
      });
    });

    // Listen to portfolio updates
    const portfolioUnsub = onSnapshot(
      collection(db, "portfolios"),
      (snapshot) => {
        snapshot.forEach((doc) => {
          const data = doc.data() as Portfolio;
          setPortfolio(data);
        });
      }
    );

    // Listen to recent trades
    const tradesQuery = query(
      collection(db, "trades"),
      orderBy("created_at", "desc"),
      limit(20)
    );
    const tradesUnsub = onSnapshot(tradesQuery, (snapshot) => {
      const tradesList: TradeRecord[] = [];
      snapshot.forEach((doc) => {
        tradesList.push({ ...doc.data(), id: doc.id } as TradeRecord);
      });
      setTrades(tradesList);
    });

    return () => {
      unsubscribe();
      portfolioUnsub();
      tradesUnsub();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lastSignalCount]);

  const getSignalColor = (signal: string) => {
    switch (signal) {
      case "BUY": return "from-emerald-500 to-green-600";
      case "SELL": return "from-rose-500 to-red-600";
      default: return "from-slate-500 to-slate-600";
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-50">
      {/* Notification Sound */}
      <audio ref={audioRef} src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" preload="auto" />
      
      {/* Background Pattern */}
      <div className="fixed inset-0 bg-gradient-to-br from-slate-950/50 via-transparent to-slate-900/50 pointer-events-none" />
      
      <div className="relative p-4 md:p-8">
        <div className="max-w-7xl mx-auto space-y-6">
          
          {/* HEADER */}
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div>
              <h1 className="text-3xl md:text-4xl font-bold flex items-center gap-3 bg-gradient-to-r from-yellow-400 via-orange-400 to-red-400 bg-clip-text text-transparent">
                <Zap className="text-yellow-400 h-8 w-8" /> TrAIder Live Pulse
              </h1>
              <p className="text-slate-400 mt-1">Real-time AI Trading Signals & Portfolio Tracking</p>
            </div>
            <div className="flex items-center gap-3">
              {/* Notification Toggle */}
              <button
                onClick={requestNotificationPermission}
                className={`p-2 rounded-lg transition-all ${
                  notificationsEnabled 
                    ? "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30" 
                    : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                }`}
                title={notificationsEnabled ? "Notifications enabled" : "Enable notifications"}
              >
                {notificationsEnabled ? <Bell className="h-5 w-5" /> : <BellOff className="h-5 w-5" />}
              </button>
              
              {/* Sound Toggle */}
              <button
                onClick={() => setSoundEnabled(!soundEnabled)}
                className={`p-2 rounded-lg transition-all ${
                  soundEnabled 
                    ? "bg-blue-500/20 text-blue-400 hover:bg-blue-500/30" 
                    : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                }`}
                title={soundEnabled ? "Sound enabled" : "Sound disabled"}
              >
                {soundEnabled ? <Volume2 className="h-5 w-5" /> : <VolumeX className="h-5 w-5" />}
              </button>
              
              <Badge variant="outline" className="text-green-400 border-green-400/50 bg-green-500/10 animate-pulse px-3 py-1">
                <span className="inline-block w-2 h-2 bg-green-400 rounded-full mr-2 animate-ping" />
                System Online
              </Badge>
            </div>
          </div>

          {/* PORTFOLIO VALUE CARD - MAIN */}
          <Card className="bg-gradient-to-br from-emerald-900/40 to-green-900/20 border-emerald-700/30 backdrop-blur-xl shadow-2xl">
            <CardContent className="p-6">
              <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                  <div className="p-4 bg-emerald-500/20 rounded-2xl">
                    <Wallet className="h-8 w-8 text-emerald-400" />
                  </div>
                  <div>
                    <p className="text-slate-400 text-sm">Portfolio Value</p>
                    <div className="text-4xl font-bold text-white">
                      ${portfolio.balance.toFixed(2)}
                    </div>
                  </div>
                </div>
                <div className="flex gap-6 text-center">
                  <div>
                    <p className="text-slate-400 text-xs">P&L</p>
                    <div className={`text-2xl font-bold ${portfolio.total_profit >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {portfolio.total_profit >= 0 ? '+' : ''}${portfolio.total_profit.toFixed(2)}
                    </div>
                  </div>
                  <div>
                    <p className="text-slate-400 text-xs">ROI</p>
                    <div className={`text-2xl font-bold ${portfolio.total_profit >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {((portfolio.balance - portfolio.initial_balance) / portfolio.initial_balance * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div>
                    <p className="text-slate-400 text-xs">Win Rate</p>
                    <div className="text-2xl font-bold text-cyan-400">
                      {portfolio.total_trades > 0 ? ((portfolio.winning_trades / portfolio.total_trades) * 100).toFixed(0) : 0}%
                    </div>
                  </div>
                  <div>
                    <p className="text-slate-400 text-xs">Trades</p>
                    <div className="text-2xl font-bold text-violet-400">
                      {portfolio.total_trades}
                    </div>
                  </div>
                </div>
              </div>
              {/* Open Positions */}
              {Object.keys(portfolio.positions).length > 0 && (
                <div className="mt-4 pt-4 border-t border-slate-700/50">
                  <p className="text-slate-400 text-xs mb-2">Open Positions</p>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(portfolio.positions).map(([symbol, pos]) => (
                      <Badge key={symbol} className="bg-blue-500/20 text-blue-300 border-blue-500/30">
                        {symbol.replace("/USDT", "")} @ ${pos.entry_price.toFixed(4)}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* PORTFOLIO OVERVIEW CARDS */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {/* Total Signals */}
            <Card className="bg-gradient-to-br from-violet-900/40 to-purple-900/20 border-violet-700/30 backdrop-blur-xl">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xs font-medium text-slate-400">Total Signals</CardTitle>
                <BarChart3 className="h-4 w-4 text-violet-400" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-violet-300">{portfolioStats.totalTrades}</div>
                <p className="text-xs text-slate-500">All time</p>
              </CardContent>
            </Card>

            {/* Win Rate */}
            <Card className="bg-gradient-to-br from-cyan-900/40 to-blue-900/20 border-cyan-700/30 backdrop-blur-xl">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xs font-medium text-slate-400">Buy Rate</CardTitle>
                <Target className="h-4 w-4 text-cyan-400" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-cyan-300">{portfolioStats.winRate.toFixed(1)}%</div>
                <p className="text-xs text-slate-500">Buy vs Total</p>
              </CardContent>
            </Card>

            {/* Average Confidence */}
            <Card className="bg-gradient-to-br from-amber-900/40 to-orange-900/20 border-amber-700/30 backdrop-blur-xl">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xs font-medium text-slate-400">Avg Confidence</CardTitle>
                <PieChart className="h-4 w-4 text-amber-400" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-amber-300">{portfolioStats.avgConfidence.toFixed(1)}%</div>
                <p className="text-xs text-slate-500">Model certainty</p>
              </CardContent>
            </Card>

            {/* Today's Activity */}
            <Card className="bg-gradient-to-br from-pink-900/40 to-rose-900/20 border-pink-700/30 backdrop-blur-xl">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xs font-medium text-slate-400">Today</CardTitle>
                <Wallet className="h-4 w-4 text-pink-400" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-pink-300">{portfolioStats.todayProfit}</div>
                <p className="text-xs text-slate-500">Signals today</p>
              </CardContent>
            </Card>
          </div>

          {/* MAIN STATS CARDS */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Recent Activity Card */}
            <Card className="bg-gradient-to-br from-slate-900/90 to-slate-800/50 border-slate-700/50 backdrop-blur-xl shadow-xl hover:shadow-2xl transition-all hover:scale-[1.02]">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-slate-300">Recent Activity</CardTitle>
                <div className="p-2 bg-blue-500/20 rounded-lg">
                  <Activity className="h-5 w-5 text-blue-400" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
                  {stats.active_signals}
                </div>
                <p className="text-xs text-slate-500 mt-1">Signals in feed</p>
              </CardContent>
            </Card>

            {/* Buy Opportunities Card */}
            <Card className="bg-gradient-to-br from-slate-900/90 to-emerald-900/20 border-emerald-700/30 backdrop-blur-xl shadow-xl hover:shadow-emerald-500/10 transition-all hover:scale-[1.02]">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-slate-300">Buy Signals</CardTitle>
                <div className="p-2 bg-emerald-500/20 rounded-lg">
                  <TrendingUp className="h-5 w-5 text-emerald-400" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-4xl font-bold bg-gradient-to-r from-emerald-400 to-green-400 bg-clip-text text-transparent">
                  {stats.buy_signals}
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Best: <span className="text-emerald-400 font-semibold">{portfolioStats.bestSymbol}</span>
                </p>
              </CardContent>
            </Card>

            {/* Sell Warnings Card */}
            <Card className="bg-gradient-to-br from-slate-900/90 to-rose-900/20 border-rose-700/30 backdrop-blur-xl shadow-xl hover:shadow-rose-500/10 transition-all hover:scale-[1.02]">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-slate-300">Sell Signals</CardTitle>
                <div className="p-2 bg-rose-500/20 rounded-lg">
                  <TrendingDown className="h-5 w-5 text-rose-400" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-4xl font-bold bg-gradient-to-r from-rose-400 to-red-400 bg-clip-text text-transparent">
                  {stats.sell_signals}
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Watch: <span className="text-rose-400 font-semibold">{portfolioStats.worstSymbol}</span>
                </p>
              </CardContent>
            </Card>
          </div>

          {/* SYMBOL BREAKDOWN - NEW! */}
          {Object.keys(portfolioStats.symbolStats).length > 0 && (
            <Card className="bg-gradient-to-br from-slate-900/90 to-slate-800/50 border-slate-700/50 backdrop-blur-xl">
              <CardHeader>
                <CardTitle className="text-lg text-white flex items-center gap-2">
                  <PieChart className="h-5 w-5 text-violet-400" />
                  Symbol Performance
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
                  {Object.entries(portfolioStats.symbolStats).slice(0, 8).map(([symbol, stats]) => (
                    <div key={symbol} className="bg-slate-800/50 rounded-lg p-3 text-center">
                      <div className="font-bold text-white text-sm">{symbol.replace("/USDT", "")}</div>
                      <div className="flex justify-center gap-2 mt-2 text-xs">
                        <span className="text-emerald-400">{stats.buys}↑</span>
                        <span className="text-rose-400">{stats.sells}↓</span>
                      </div>
                      <div className="mt-2 h-1 bg-slate-700 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400"
                          style={{ width: `${(stats.buys / (stats.buys + stats.sells + stats.neutral || 1)) * 100}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* SIGNALS TABLE */}
          <Card className="bg-gradient-to-br from-slate-900/90 to-slate-800/50 border-slate-700/50 backdrop-blur-xl shadow-2xl overflow-hidden">
            <CardHeader className="border-b border-slate-700/50">
              <CardTitle className="text-xl text-white flex items-center gap-2">
                <Activity className="h-5 w-5 text-yellow-400" />
                Live Signal Feed
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="border-slate-700/50 hover:bg-transparent">
                      <TableHead className="text-slate-400 font-semibold">Time</TableHead>
                      <TableHead className="text-slate-400 font-semibold">Symbol</TableHead>
                      <TableHead className="text-slate-400 font-semibold">Strategy</TableHead>
                      <TableHead className="text-slate-400 font-semibold">Signal</TableHead>
                      <TableHead className="text-slate-400 font-semibold">Confidence</TableHead>
                      <TableHead className="text-slate-400 font-semibold">Price</TableHead>
                      <TableHead className="text-slate-400 font-semibold hidden md:table-cell">Context</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {signals.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center py-12 text-slate-500">
                          <div className="flex flex-col items-center gap-2">
                            <Activity className="h-8 w-8 animate-pulse" />
                            <p>Waiting for signals...</p>
                            <p className="text-xs">Trigger a trading cycle to see AI predictions</p>
                          </div>
                        </TableCell>
                      </TableRow>
                    ) : (
                      signals.map((s, index) => (
                        <TableRow 
                          key={s.id} 
                          className={`border-slate-700/30 transition-all hover:bg-slate-800/50 ${
                            index === 0 ? "animate-pulse bg-slate-800/30" : ""
                          }`}
                        >
                          <TableCell className="font-mono text-slate-500 text-xs">
                            {s.created_at?.seconds 
                              ? new Date(s.created_at.seconds * 1000).toLocaleTimeString() 
                              : 'Just now'}
                          </TableCell>
                          <TableCell className="font-bold text-white text-lg">
                            {s.symbol.replace("/USDT", "")}
                            <span className="text-slate-500 text-xs font-normal">/USDT</span>
                          </TableCell>
                          <TableCell>
                            <Badge variant="secondary" className="bg-slate-700/50 text-slate-300 hover:bg-slate-700 font-mono text-xs">
                              {s.strategy}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Badge 
                              className={`bg-gradient-to-r ${getSignalColor(s.signal)} text-white font-bold px-3 py-1 shadow-lg`}
                            >
                              {s.signal}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <div className="h-2 w-20 bg-slate-700 rounded-full overflow-hidden">
                                <div 
                                  className={`h-full rounded-full transition-all duration-500 ${
                                    s.confidence > 80 ? 'bg-gradient-to-r from-emerald-400 to-green-500' : 
                                    s.confidence > 60 ? 'bg-gradient-to-r from-yellow-400 to-orange-500' :
                                    'bg-gradient-to-r from-slate-400 to-slate-500'
                                  }`}
                                  style={{ width: `${s.confidence}%` }}
                                />
                              </div>
                              <span className={`text-xs font-mono ${
                                s.confidence > 80 ? 'text-emerald-400' : 
                                s.confidence > 60 ? 'text-yellow-400' : 
                                'text-slate-400'
                              }`}>
                                {s.confidence.toFixed(1)}%
                              </span>
                            </div>
                          </TableCell>
                          <TableCell className="font-mono text-white">
                            ${s.price < 1 ? s.price.toFixed(6) : s.price.toFixed(2)}
                          </TableCell>
                          <TableCell className="text-slate-500 text-xs italic hidden md:table-cell max-w-[200px] truncate">
                            {s.desc} • {s.mode}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
          {/* RECENT TRADES */}
          {trades.length > 0 && (
            <Card className="bg-gradient-to-br from-slate-900/90 to-slate-800/50 border-slate-700/50 backdrop-blur-xl shadow-2xl overflow-hidden">
              <CardHeader className="border-b border-slate-700/50">
                <CardTitle className="text-xl text-white flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-emerald-400" />
                  Recent Trades
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="border-slate-700/50 hover:bg-transparent">
                        <TableHead className="text-slate-400 font-semibold">Time</TableHead>
                        <TableHead className="text-slate-400 font-semibold">Type</TableHead>
                        <TableHead className="text-slate-400 font-semibold">Symbol</TableHead>
                        <TableHead className="text-slate-400 font-semibold">Price</TableHead>
                        <TableHead className="text-slate-400 font-semibold">Amount</TableHead>
                        <TableHead className="text-slate-400 font-semibold">Value</TableHead>
                        <TableHead className="text-slate-400 font-semibold">P&L</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {trades.slice(0, 10).map((t) => (
                        <TableRow key={t.id} className="border-slate-700/30 hover:bg-slate-800/50">
                          <TableCell className="font-mono text-slate-500 text-xs">
                            {t.created_at?.seconds 
                              ? new Date(t.created_at.seconds * 1000).toLocaleString() 
                              : 'Just now'}
                          </TableCell>
                          <TableCell>
                            <Badge className={`${t.type === 'BUY' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                              {t.type}
                            </Badge>
                          </TableCell>
                          <TableCell className="font-bold text-white">
                            {t.symbol.replace("/USDT", "")}
                          </TableCell>
                          <TableCell className="font-mono text-white">
                            ${t.price < 1 ? t.price.toFixed(6) : t.price.toFixed(2)}
                          </TableCell>
                          <TableCell className="font-mono text-slate-400">
                            {t.amount.toFixed(4)}
                          </TableCell>
                          <TableCell className="font-mono text-white">
                            ${t.value.toFixed(2)}
                          </TableCell>
                          <TableCell className={`font-mono font-bold ${t.profit !== undefined ? (t.profit >= 0 ? 'text-emerald-400' : 'text-rose-400') : 'text-slate-500'}`}>
                            {t.profit !== undefined ? (
                              <>
                                {t.profit >= 0 ? '+' : ''}${t.profit.toFixed(2)}
                                <span className="text-xs ml-1">({t.profit_pct?.toFixed(1)}%)</span>
                              </>
                            ) : '-'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* FOOTER */}
          <div className="text-center text-slate-600 text-xs py-4">
            <p>TrAIder AI Trading System • Paper Trading with $1000 Initial Capital</p>
            <p className="mt-1">Last Updated: {new Date().toLocaleString()}</p>
          </div>

        </div>
      </div>
    </div>
  );
}
