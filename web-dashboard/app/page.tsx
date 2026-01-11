"use client";

import { useEffect, useState, useRef } from "react";
import { db } from "@/lib/firebase";
import { collection, query, orderBy, limit, onSnapshot } from "firebase/firestore";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Activity, TrendingUp, TrendingDown, Zap, Bell, BellOff, Volume2, VolumeX } from "lucide-react";

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

export default function Dashboard() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [stats, setStats] = useState({
    active_signals: 0,
    buy_signals: 0,
    sell_signals: 0,
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
      limit(20)
    );

    const unsubscribe = onSnapshot(q, (snapshot) => {
      const msgs: Signal[] = [];
      let buy = 0;
      let sell = 0;

      snapshot.forEach((doc) => {
        const data = doc.data() as Signal;
        msgs.push({ ...data, id: doc.id });
        if (data.signal === "BUY") buy++;
        if (data.signal === "SELL") sell++;
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

      setSignals(msgs);
      setStats({
        active_signals: msgs.length,
        buy_signals: buy,
        sell_signals: sell,
      });
    });

    return () => unsubscribe();
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

          {/* STATS CARDS */}
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
                <p className="text-xs text-slate-500 mt-1">Signals in last cycle</p>
              </CardContent>
            </Card>

            {/* Buy Opportunities Card */}
            <Card className="bg-gradient-to-br from-slate-900/90 to-emerald-900/20 border-emerald-700/30 backdrop-blur-xl shadow-xl hover:shadow-emerald-500/10 transition-all hover:scale-[1.02]">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-slate-300">Buy Opportunities</CardTitle>
                <div className="p-2 bg-emerald-500/20 rounded-lg">
                  <TrendingUp className="h-5 w-5 text-emerald-400" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-4xl font-bold bg-gradient-to-r from-emerald-400 to-green-400 bg-clip-text text-transparent">
                  {stats.buy_signals}
                </div>
                <p className="text-xs text-slate-500 mt-1">Actionable Buys</p>
              </CardContent>
            </Card>

            {/* Sell Warnings Card */}
            <Card className="bg-gradient-to-br from-slate-900/90 to-rose-900/20 border-rose-700/30 backdrop-blur-xl shadow-xl hover:shadow-rose-500/10 transition-all hover:scale-[1.02]">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-slate-300">Sell Warnings</CardTitle>
                <div className="p-2 bg-rose-500/20 rounded-lg">
                  <TrendingDown className="h-5 w-5 text-rose-400" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-4xl font-bold bg-gradient-to-r from-rose-400 to-red-400 bg-clip-text text-transparent">
                  {stats.sell_signals}
                </div>
                <p className="text-xs text-slate-500 mt-1">Protective Exits</p>
              </CardContent>
            </Card>
          </div>

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

          {/* FOOTER */}
          <div className="text-center text-slate-600 text-xs py-4">
            <p>TrAIder AI Trading System • Powered by Adaptive AI Models</p>
            <p className="mt-1">Last Updated: {new Date().toLocaleString()}</p>
          </div>

        </div>
      </div>
    </div>
  );
}
