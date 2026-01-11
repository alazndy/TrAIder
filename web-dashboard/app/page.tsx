"use client";

import { useEffect, useState, useRef } from "react";
import { db } from "@/lib/firebase";
import { collection, query, orderBy, limit, onSnapshot, doc } from "firebase/firestore";
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
  const [systemLogs, setSystemLogs] = useState<Signal[]>([]);
  
  // Restore settings from localStorage on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      // Check stored sound preference
      const storedSound = localStorage.getItem('traider_sound');
      if (storedSound !== null) {
        setSoundEnabled(storedSound === 'true');
      }
      
      // Check browser notification permission
      if ("Notification" in window && Notification.permission === "granted") {
        setNotificationsEnabled(true);
      }
    }
  }, []);

  // Request notification permission
  const requestNotificationPermission = async () => {
    if ("Notification" in window) {
      const permission = await Notification.requestPermission();
      const isGranted = permission === "granted";
      setNotificationsEnabled(isGranted);
    }
  };

  // Toggle sound with localStorage persistence
  const toggleSound = () => {
    const newValue = !soundEnabled;
    setSoundEnabled(newValue);
    if (typeof window !== 'undefined') {
      localStorage.setItem('traider_sound', String(newValue));
    }
  };

  const audioCtxRef = useRef<AudioContext | null>(null);

  // Initialize and Unlock Audio Context on First Interaction
  useEffect(() => {
    const unlockAudio = () => {
      const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioContext) return;

      if (!audioCtxRef.current) {
        audioCtxRef.current = new AudioContext();
      }

      if (audioCtxRef.current.state === 'suspended') {
        audioCtxRef.current.resume().then(() => {
          console.log("Audio Context Resumed/Unlocked");
        });
      }
      
      // Remove listeners once unlocked
      window.removeEventListener('click', unlockAudio);
      window.removeEventListener('touchstart', unlockAudio);
      window.removeEventListener('keydown', unlockAudio);
    };

    window.addEventListener('click', unlockAudio);
    window.addEventListener('touchstart', unlockAudio);
    window.addEventListener('keydown', unlockAudio);

    return () => {
      window.removeEventListener('click', unlockAudio);
      window.removeEventListener('touchstart', unlockAudio);
      window.removeEventListener('keydown', unlockAudio);
    };
  }, []);

  // Play adaptive notification sound
  const playAdaptiveSound = (type: string, confidence: number, strategy: string) => {
    if (!soundEnabled) return;

    try {
      if (!audioCtxRef.current) {
        const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
        if (AudioContext) {
           audioCtxRef.current = new AudioContext();
        } else {
           return;
        }
      }

      const ctx = audioCtxRef.current;
      if (ctx.state === 'suspended') {
        ctx.resume();
      }

      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.connect(gain);
      gain.connect(ctx.destination);

      const now = ctx.currentTime;
      
      // Hourly Report or System Alert
      if (strategy === 'HOURLY_REPORT') {
        const osc2 = ctx.createOscillator();
        const osc3 = ctx.createOscillator();
        const gain2 = ctx.createGain();
        const gain3 = ctx.createGain();
        
        osc2.connect(gain2);
        osc3.connect(gain3);
        gain2.connect(ctx.destination);
        gain3.connect(ctx.destination);
        
        // Major Chord (C4 - E4 - G4)
        osc.frequency.value = 261.63;
        osc2.frequency.value = 329.63;
        osc3.frequency.value = 392.00;
        
        gain.gain.value = 0.1;
        gain2.gain.value = 0.1;
        gain3.gain.value = 0.1;
        
        osc.start(now);
        osc2.start(now + 0.1);
        osc3.start(now + 0.2);
        
        gain.gain.exponentialRampToValueAtTime(0.001, now + 1.5);
        gain2.gain.exponentialRampToValueAtTime(0.001, now + 1.5);
        gain3.gain.exponentialRampToValueAtTime(0.001, now + 1.5);
        
        osc.stop(now + 1.5);
        osc2.stop(now + 1.5);
        osc3.stop(now + 1.5);
        return;
      }

      // Trading Signals
      gain.gain.setValueAtTime(0.1, now);
      
      const isHighConf = confidence >= 80;

      if (type === 'BUY') {
        // High pitch success tone
        osc.frequency.setValueAtTime(880, now); // A5
        if (isHighConf) {
          // Rapid ascending flourish for high confidence
          osc.frequency.setValueAtTime(880, now);
          osc.frequency.linearRampToValueAtTime(1760, now + 0.1); // A6
        }
      } else if (type === 'SELL') {
        // Lower pitch warning tone
        osc.frequency.setValueAtTime(440, now); // A4
        if (isHighConf) {
          // Descending slide
          osc.frequency.setValueAtTime(440, now);
          osc.frequency.linearRampToValueAtTime(220, now + 0.2); // A3
        }
      } else {
        // Neutral/Other
        osc.frequency.setValueAtTime(330, now); // E4
      }

      osc.start(now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + (isHighConf ? 0.6 : 0.3));
      osc.stop(now + (isHighConf ? 0.6 : 0.3));

    } catch (e) {
      console.error("Audio play failed:", e);
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
      limit(100)
    );

    const unsubscribe = onSnapshot(q, (snapshot) => {
      const allMsgs: Signal[] = [];
      const tradeSignals: Signal[] = [];
      const logs: Signal[] = [];

      let buy = 0;
      let sell = 0;
      let totalConfidence = 0;
      const symbolStats: Record<string, { buys: number; sells: number; neutral: number }> = {};

      snapshot.forEach((doc) => {
        const data = doc.data() as Signal;
        const signalItem = { ...data, id: doc.id };
        allMsgs.push(signalItem);
        
        if (data.strategy === "HEARTBEAT" || data.strategy === "HOURLY_REPORT") {
          logs.push(signalItem);
        } else {
          tradeSignals.push(signalItem);

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
        }
      });

      // Sound & Notification Logic
      // Check for new signals
      if (allMsgs.length > 0 && lastSignalCount > 0 && allMsgs.length > lastSignalCount) {
         const newSignal = allMsgs[0];
         
         // Only play if it's a fresh signal (created in last 30 seconds to avoid spam on reload)
         const isFresh = newSignal.created_at && (Date.now() - newSignal.created_at.seconds * 1000) < 30000;
         
         if (isFresh) {
           if (newSignal.strategy === 'HOURLY_REPORT') {
             playAdaptiveSound('INFO', 100, 'HOURLY_REPORT');
             sendNotification('TrAIder Hourly Report', newSignal.desc);
           } else if (newSignal.strategy !== 'HEARTBEAT') {
             playAdaptiveSound(newSignal.signal, newSignal.confidence, newSignal.strategy);
             sendNotification(
              `${newSignal.signal} Signal: ${newSignal.symbol}`,
              `${newSignal.strategy} | Confidence: ${newSignal.confidence.toFixed(1)}% | $${newSignal.price.toFixed(4)}`
            );
           }
         }
      }
      setLastSignalCount(allMsgs.length);

      // Calculate portfolio stats
      const avgConfidence = tradeSignals.length > 0 ? totalConfidence / tradeSignals.length : 0;
      
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
      const todaySignals = tradeSignals.filter(s => 
        s.created_at && s.created_at.seconds * 1000 >= today.getTime()
      );

      setSignals(tradeSignals.slice(0, 20)); // Show only last 20 in table
      setSystemLogs(logs.slice(0, 5)); // Keep last 5 logs
      setStats({
        active_signals: tradeSignals.length,
        buy_signals: buy,
        sell_signals: sell,
      });
      setPortfolioStats({
        totalTrades: tradeSignals.length,
        winRate: tradeSignals.length > 0 ? (buy / tradeSignals.length) * 100 : 0,
        totalProfit: 0, // Would come from trades collection
        todayProfit: todaySignals.length,
        avgConfidence,
        bestSymbol,
        worstSymbol,
        symbolStats,
      });
    }, (error) => {
      console.error("Error fetching signals:", error);
    });

    // Listen to portfolio updates
    // Listen to specific portfolio document
    const portfolioUnsub = onSnapshot(
      doc(db, "portfolios", "live_portfolio_v1"),
      (docSnapshot) => {
        if (docSnapshot.exists()) {
          const data = docSnapshot.data() as Portfolio;
          setPortfolio(data);
        } else {
          console.log("Waiting for portfolio initialization...");
        }
      },
      (error) => {
        console.error("Error fetching portfolio:", error);
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
    }, (error) => {
      console.error("Error fetching trades:", error);
    });

    return () => {
      unsubscribe();
      portfolioUnsub();
      tradesUnsub();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const getSignalColor = (signal: string) => {
    switch (signal) {
      case "BUY": return "from-emerald-500 to-green-600";
      case "SELL": return "from-rose-500 to-red-600";
      default: return "from-slate-500 to-slate-600";
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-50">
      
      {/* Background Pattern */}
      <div className="fixed inset-0 bg-gradient-to-br from-slate-950/50 via-transparent to-slate-900/50 pointer-events-none" />
      
      <div className="relative p-4 md:p-8">
        <div className="max-w-7xl mx-auto space-y-6">
          
          {/* HEADER */}
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div>
              <h1 className="text-3xl md:text-4xl font-bold flex items-center gap-3 bg-gradient-to-r from-yellow-400 via-orange-400 to-red-400 bg-clip-text text-transparent">
                <Zap className="text-yellow-400 h-8 w-8" /> TrAIder Canlı Akış
              </h1>
              <p className="text-slate-400 mt-1">Gerçek Zamanlı Yapay Zeka Sinyalleri & Portföy Takibi</p>
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
                title={notificationsEnabled ? "Bildirimler açık" : "Bildirimleri aç"}
              >
                {notificationsEnabled ? <Bell className="h-5 w-5" /> : <BellOff className="h-5 w-5" />}
              </button>
              
              {/* Sound Toggle */}
              <button
                onClick={toggleSound}
                className={`p-2 rounded-lg transition-all ${
                  soundEnabled 
                    ? "bg-blue-500/20 text-blue-400 hover:bg-blue-500/30" 
                    : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                }`}
                title={soundEnabled ? "Ses açık" : "Ses kapalı"}
              >
                {soundEnabled ? <Volume2 className="h-5 w-5" /> : <VolumeX className="h-5 w-5" />}
              </button>

              {/* Sound Test Button (Mobile Fix) */}
              {soundEnabled && (
                <button
                  onClick={() => playAdaptiveSound('BUY', 100, 'TEST')}
                  className="p-2 rounded-lg bg-orange-500/10 text-orange-400 hover:bg-orange-500/20 md:hidden"
                  title="Test Sesi Çal"
                >
                  <Activity className="h-5 w-5" />
                </button>
              )}
              
              <Badge variant="outline" className="text-green-400 border-green-400/50 bg-green-500/10 animate-pulse px-3 py-1">
                <span className="inline-block w-2 h-2 bg-green-400 rounded-full mr-2 animate-ping" />
                Sistem Çevrimiçi
              </Badge>
            </div>
          </div>

          {/* PORTFOLIO VALUE CARD - ENHANCED */}
          <Card className="bg-gradient-to-br from-emerald-900/40 to-green-900/20 border-emerald-700/30 backdrop-blur-xl shadow-2xl">
            <CardContent className="p-4 md:p-6">
              {/* Main Stats Row - Mobile Responsive */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4 md:gap-6">
                {/* Total Portfolio Value */}
                <div className="col-span-2 md:col-span-1 flex items-center gap-3">
                  <div className="p-3 bg-emerald-500/20 rounded-xl">
                    <Wallet className="h-6 w-6 text-emerald-400" />
                  </div>
                  <div>
                    <p className="text-slate-400 text-xs">Portföy Değeri</p>
                    <div className="text-2xl md:text-3xl font-bold text-white">
                      ${(portfolio.balance + Object.values(portfolio.positions).reduce((sum, pos) => sum + (pos.amount * pos.entry_price), 0)).toFixed(2)}
                    </div>
                  </div>
                </div>

                {/* Liquid Cash */}
                <div className="text-center md:text-left">
                  <p className="text-slate-400 text-xs">💵 Nakit Varlık</p>
                  <div className="text-xl md:text-2xl font-bold text-green-400">
                    ${portfolio.balance.toFixed(2)}
                  </div>
                  <p className="text-xs text-slate-500">Kullanılabilir</p>
                </div>

                {/* P&L */}
                <div className="text-center md:text-left">
                  <p className="text-slate-400 text-xs">📈 K/Z</p>
                  <div className={`text-xl md:text-2xl font-bold ${portfolio.total_profit >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {portfolio.total_profit >= 0 ? '+' : ''}${portfolio.total_profit.toFixed(2)}
                  </div>
                  <p className={`text-xs ${portfolio.total_profit >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                    {((portfolio.balance - portfolio.initial_balance) / portfolio.initial_balance * 100).toFixed(1)}% Getiri
                  </p>
                </div>

                {/* Win Rate */}
                <div className="text-center md:text-left">
                  <p className="text-slate-400 text-xs">🎯 Kazanma Oranı</p>
                  <div className="text-xl md:text-2xl font-bold text-cyan-400">
                    {portfolio.total_trades > 0 ? ((portfolio.winning_trades / portfolio.total_trades) * 100).toFixed(0) : 0}%
                  </div>
                  <p className="text-xs text-slate-500">{portfolio.winning_trades}W / {portfolio.losing_trades}L</p>
                </div>

                {/* Trades */}
                <div className="text-center md:text-left">
                  <p className="text-slate-400 text-xs">📊 Toplam İşlem</p>
                  <div className="text-xl md:text-2xl font-bold text-violet-400">
                    {portfolio.total_trades}
                  </div>
                  <p className="text-xs text-slate-500">Tamamlanan</p>
                </div>
              </div>

              {/* Allocation Bar */}
              <div className="mt-6">
                <div className="flex justify-between text-xs text-slate-400 mb-1">
                  <span>Portföy Dağılımı</span>
                  <span>
                    Nakit: {((portfolio.balance / portfolio.initial_balance) * 100).toFixed(0)}% | 
                    Yatırım: {((Object.values(portfolio.positions).reduce((sum, pos) => sum + (pos.amount * pos.entry_price), 0) / portfolio.initial_balance) * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="h-3 bg-slate-700 rounded-full overflow-hidden flex">
                  <div 
                    className="bg-gradient-to-r from-green-500 to-emerald-400 transition-all duration-500"
                    style={{ width: `${(portfolio.balance / portfolio.initial_balance) * 100}%` }}
                  />
                  <div 
                    className="bg-gradient-to-r from-blue-500 to-cyan-400 transition-all duration-500"
                    style={{ width: `${(Object.values(portfolio.positions).reduce((sum, pos) => sum + (pos.amount * pos.entry_price), 0) / portfolio.initial_balance) * 100}%` }}
                  />
                </div>
                <div className="flex gap-4 mt-2 text-xs">
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded-full bg-gradient-to-r from-green-500 to-emerald-400" />
                    <span className="text-slate-400">Nakit</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded-full bg-gradient-to-r from-blue-500 to-cyan-400" />
                    <span className="text-slate-400">Yatırım</span>
                  </div>
                </div>
              </div>

              {/* Open Positions Table */}
              {Object.keys(portfolio.positions).length > 0 ? (
                <div className="mt-6 pt-4 border-t border-slate-700/50">
                  <p className="text-white font-semibold mb-3 flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-blue-400" />
                    Açık Pozisyonlar ({Object.keys(portfolio.positions).length})
                  </p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-slate-400 text-xs border-b border-slate-700/50">
                          <th className="text-left py-2">Koin</th>
                          <th className="text-right py-2">Miktar</th>
                          <th className="text-right py-2">Giriş Fiyatı</th>
                          <th className="text-right py-2">Değer</th>
                          <th className="text-right py-2 hidden md:table-cell">Portföy %</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(portfolio.positions).map(([symbol, pos]) => {
                          const value = pos.amount * pos.entry_price;
                          const pctOfPortfolio = (value / portfolio.initial_balance) * 100;
                          return (
                            <tr key={symbol} className="border-b border-slate-700/30 hover:bg-slate-800/30">
                              <td className="py-3">
                                <div className="flex items-center gap-2">
                                  <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center text-blue-400 font-bold text-xs">
                                    {symbol.replace("/USDT", "").slice(0, 3)}
                                  </div>
                                  <div>
                                    <div className="font-semibold text-white">{symbol.replace("/USDT", "")}</div>
                                    <div className="text-xs text-slate-500">USDT</div>
                                  </div>
                                </div>
                              </td>
                              <td className="text-right py-3 font-mono text-white">
                                {pos.amount.toFixed(4)}
                              </td>
                              <td className="text-right py-3 font-mono text-slate-300">
                                ${pos.entry_price < 1 ? pos.entry_price.toFixed(6) : pos.entry_price.toFixed(2)}
                              </td>
                              <td className="text-right py-3 font-mono text-white font-semibold">
                                ${value.toFixed(2)}
                              </td>
                              <td className="text-right py-3 hidden md:table-cell">
                                <div className="flex items-center justify-end gap-2">
                                  <div className="w-16 h-2 bg-slate-700 rounded-full overflow-hidden">
                                    <div 
                                      className="h-full bg-blue-500 rounded-full"
                                      style={{ width: `${Math.min(pctOfPortfolio, 100)}%` }}
                                    />
                                  </div>
                                  <span className="text-blue-400 text-xs w-12">{pctOfPortfolio.toFixed(1)}%</span>
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="mt-6 pt-4 border-t border-slate-700/50 text-center py-6">
                  <Wallet className="h-12 w-12 text-slate-600 mx-auto mb-2" />
                  <p className="text-slate-500 text-sm">Açık pozisyon yok</p>
                  <p className="text-slate-600 text-xs">Yüksek güvenli AL sinyalleri bekleniyor...</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* PORTFOLIO OVERVIEW CARDS */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {/* Total Signals */}
            <Card className="bg-gradient-to-br from-violet-900/40 to-purple-900/20 border-violet-700/30 backdrop-blur-xl">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xs font-medium text-slate-400">Toplam Sinyal</CardTitle>
                <BarChart3 className="h-4 w-4 text-violet-400" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-violet-300">{portfolioStats.totalTrades}</div>
                <p className="text-xs text-slate-500">Tüm zamanlar</p>
              </CardContent>
            </Card>

            {/* Win Rate */}
            <Card className="bg-gradient-to-br from-cyan-900/40 to-blue-900/20 border-cyan-700/30 backdrop-blur-xl">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xs font-medium text-slate-400">Alış Oranı</CardTitle>
                <Target className="h-4 w-4 text-cyan-400" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-cyan-300">{portfolioStats.winRate.toFixed(1)}%</div>
                <p className="text-xs text-slate-500">Alış / Toplam</p>
              </CardContent>
            </Card>

            {/* Average Confidence */}
            <Card className="bg-gradient-to-br from-amber-900/40 to-orange-900/20 border-amber-700/30 backdrop-blur-xl">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xs font-medium text-slate-400">Ort. Güven</CardTitle>
                <PieChart className="h-4 w-4 text-amber-400" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-amber-300">{portfolioStats.avgConfidence.toFixed(1)}%</div>
                <p className="text-xs text-slate-500">Model kesinliği</p>
              </CardContent>
            </Card>

            {/* Today's Activity */}
            <Card className="bg-gradient-to-br from-pink-900/40 to-rose-900/20 border-pink-700/30 backdrop-blur-xl">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-xs font-medium text-slate-400">Bugün</CardTitle>
                <Wallet className="h-4 w-4 text-pink-400" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-pink-300">{portfolioStats.todayProfit}</div>
                <p className="text-xs text-slate-500">Bugünkü sinyaller</p>
              </CardContent>
            </Card>
          </div>

          {/* MAIN STATS CARDS */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Recent Activity Card */}
            <Card className="bg-gradient-to-br from-slate-900/90 to-slate-800/50 border-slate-700/50 backdrop-blur-xl shadow-xl hover:shadow-2xl transition-all hover:scale-[1.02]">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-slate-300">Son Hareketler</CardTitle>
                <div className="p-2 bg-blue-500/20 rounded-lg">
                  <Activity className="h-5 w-5 text-blue-400" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
                  {stats.active_signals}
                </div>
                <p className="text-xs text-slate-500 mt-1">Akıştaki sinyaller</p>
              </CardContent>
            </Card>

            {/* Buy Opportunities Card */}
            <Card className="bg-gradient-to-br from-slate-900/90 to-emerald-900/20 border-emerald-700/30 backdrop-blur-xl shadow-xl hover:shadow-emerald-500/10 transition-all hover:scale-[1.02]">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-slate-300">Alış Sinyalleri</CardTitle>
                <div className="p-2 bg-emerald-500/20 rounded-lg">
                  <TrendingUp className="h-5 w-5 text-emerald-400" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-4xl font-bold bg-gradient-to-r from-emerald-400 to-green-400 bg-clip-text text-transparent">
                  {stats.buy_signals}
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  En İyi: <span className="text-emerald-400 font-semibold">{portfolioStats.bestSymbol}</span>
                </p>
              </CardContent>
            </Card>

            {/* Sell Warnings Card */}
            <Card className="bg-gradient-to-br from-slate-900/90 to-rose-900/20 border-rose-700/30 backdrop-blur-xl shadow-xl hover:shadow-rose-500/10 transition-all hover:scale-[1.02]">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-slate-300">Satış Sinyalleri</CardTitle>
                <div className="p-2 bg-rose-500/20 rounded-lg">
                  <TrendingDown className="h-5 w-5 text-rose-400" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-4xl font-bold bg-gradient-to-r from-rose-400 to-red-400 bg-clip-text text-transparent">
                  {stats.sell_signals}
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Dikkat: <span className="text-rose-400 font-semibold">{portfolioStats.worstSymbol}</span>
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
                  Symbol Performansı
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
                Canlı Sinyal Akışı
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="border-slate-700/50 hover:bg-transparent">
                      <TableHead className="text-slate-400 font-semibold">Zaman</TableHead>
                      <TableHead className="text-slate-400 font-semibold">Sembol</TableHead>
                      <TableHead className="text-slate-400 font-semibold">Strateji</TableHead>
                      <TableHead className="text-slate-400 font-semibold">Sinyal</TableHead>
                      <TableHead className="text-slate-400 font-semibold">Güven</TableHead>
                      <TableHead className="text-slate-400 font-semibold">Fiyat</TableHead>
                      <TableHead className="text-slate-400 font-semibold hidden md:table-cell">Bağlam</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {signals.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center py-12 text-slate-500">
                          <div className="flex flex-col items-center gap-2">
                            <Activity className="h-8 w-8 animate-pulse" />
                            <p>Sinyal bekleniyor...</p>
                            <p className="text-xs">Yapay zeka tahminlerini görmek için işlem döngüsü bekleniyor</p>
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
                              ? new Date(s.created_at.seconds * 1000).toLocaleTimeString('tr-TR', { timeZone: 'Europe/Istanbul' }) 
                              : 'Şimdi'}
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
                  Son İşlemler
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="border-slate-700/50 hover:bg-transparent">
                        <TableHead className="text-slate-400 font-semibold">Tarih</TableHead>
                        <TableHead className="text-slate-400 font-semibold">İşlem</TableHead>
                        <TableHead className="text-slate-400 font-semibold">Sembol</TableHead>
                        <TableHead className="text-slate-400 font-semibold">Fiyat</TableHead>
                        <TableHead className="text-slate-400 font-semibold">Miktar</TableHead>
                        <TableHead className="text-slate-400 font-semibold">Değer</TableHead>
                        <TableHead className="text-slate-400 font-semibold">K/Z</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {trades.slice(0, 10).map((t) => (
                        <TableRow key={t.id} className="border-slate-700/30 hover:bg-slate-800/50">
                          <TableCell className="font-mono text-slate-500 text-xs">
                            {t.created_at?.seconds 
                              ? new Date(t.created_at.seconds * 1000).toLocaleString('tr-TR', { timeZone: 'Europe/Istanbul' }) 
                              : 'Şimdi'}
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

          {/* LOGS TERMINAL */}
          <Card className="bg-slate-950/80 border-slate-800/50 backdrop-blur-xl shadow-2xl font-mono overflow-hidden">
            <CardHeader className="border-b border-slate-800 py-3">
              <CardTitle className="text-sm text-slate-400 flex items-center gap-2">
                Sistem Durumu & Loglar
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 h-48 overflow-y-auto bg-black/50">
              <div className="space-y-2">
                {systemLogs.length === 0 ? (
                  <p className="text-slate-600 text-xs text-center pt-8">Sinyal bekleniyor...</p>
                ) : (
                  systemLogs.map((log) => (
                    <div key={log.id} className="text-xs flex gap-2 animate-in fade-in slide-in-from-left-2 items-start opacity-80 hover:opacity-100 transition-opacity">
                      <span className="text-slate-500 shrink-0">
                        [{log.created_at?.seconds ? new Date(log.created_at.seconds * 1000).toLocaleTimeString('tr-TR', { timeZone: 'Europe/Istanbul' }) : 'Şimdi'}]
                      </span>
                      <span className="text-emerald-400/90">&gt;</span>
                      <span className={log.strategy === 'HOURLY_REPORT' ? "text-blue-400 font-bold" : "text-slate-300 break-words"}>
                        {log.strategy === 'HOURLY_REPORT' ? '[SAATLİK RAPOR] ' : ''}
                        {log.desc}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>

          {/* FOOTER */}
          <div className="text-center text-slate-600 text-xs py-4">
            <p>TrAIder Yapay Zeka Alım-Satım Sistemi • $1000 Başlangıç Sermayeli Sanal İşlem</p>
            <p className="mt-1">Son Güncelleme: {new Date().toLocaleString('tr-TR', { timeZone: 'Europe/Istanbul' })}</p>
          </div>

        </div>
      </div>
    </div>
  );
}
