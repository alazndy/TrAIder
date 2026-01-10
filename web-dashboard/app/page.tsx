"use client";

import { useEffect, useState } from "react";
import { db } from "@/lib/firebase";
import { collection, query, orderBy, limit, onSnapshot } from "firebase/firestore";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Activity, TrendingUp, TrendingDown, DollarSign, Zap } from "lucide-react";

interface Signal {
  id: string;
  symbol: string;
  strategy: string;
  signal: string;
  confidence: number;
  price: number;
  mode: string;
  desc: string;
  created_at: any;
}

export default function Dashboard() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [stats, setStats] = useState({
    active_signals: 0,
    buy_signals: 0,
    sell_signals: 0,
  });

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

      setSignals(msgs);
      setStats({
        active_signals: msgs.length,
        buy_signals: buy,
        sell_signals: sell,
      });
    });

    return () => unsubscribe();
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* HEADER */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              <Zap className="text-yellow-400" /> TrAIder Live Pulse
            </h1>
            <p className="text-slate-400">Real-time AI Trading Signals & Portfolio Tracking</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-green-400 border-green-400 animate-pulse">
              ● System Online
            </Badge>
          </div>
        </div>

        {/* STATS CARDS */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="bg-slate-900 border-slate-800">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-slate-200">Recent Activity</CardTitle>
              <Activity className="h-4 w-4 text-blue-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">{stats.active_signals}</div>
              <p className="text-xs text-slate-400">Signals in last cycle</p>
            </CardContent>
          </Card>

          <Card className="bg-slate-900 border-slate-800">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-slate-200">Buy Opportunities</CardTitle>
              <TrendingUp className="h-4 w-4 text-green-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-400">{stats.buy_signals}</div>
              <p className="text-xs text-slate-400">Actionable Buys</p>
            </CardContent>
          </Card>

          <Card className="bg-slate-900 border-slate-800">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-slate-200">Sell Warnings</CardTitle>
              <TrendingDown className="h-4 w-4 text-red-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-400">{stats.sell_signals}</div>
              <p className="text-xs text-slate-400">Protective Exits</p>
            </CardContent>
          </Card>
        </div>

        {/* SIGNALS TABLE */}
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-white">Live Signal Feed</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow className="border-slate-800 hover:bg-slate-900">
                  <TableHead className="text-slate-400">Time</TableHead>
                  <TableHead className="text-slate-400">Symbol</TableHead>
                  <TableHead className="text-slate-400">Strategy</TableHead>
                  <TableHead className="text-slate-400">Signal</TableHead>
                  <TableHead className="text-slate-400">Confidence</TableHead>
                  <TableHead className="text-slate-400">Price</TableHead>
                  <TableHead className="text-slate-400">Context</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {signals.map((s) => (
                  <TableRow key={s.id} className="border-slate-800 hover:bg-slate-800/50">
                    <TableCell className="font-mono text-slate-500 text-xs">
                       {s.created_at?.seconds ? new Date(s.created_at.seconds * 1000).toLocaleTimeString() : 'Just now'}
                    </TableCell>
                    <TableCell className="font-bold text-white">{s.symbol}</TableCell>
                    <TableCell className="text-slate-300">
                      <Badge variant="secondary" className="bg-slate-800 text-slate-300 hover:bg-slate-700">
                        {s.strategy}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge 
                        variant="outline" 
                        className={
                          s.signal === 'BUY' ? 'bg-green-500/10 text-green-400 border-green-500/50' : 
                          s.signal === 'SELL' ? 'bg-red-500/10 text-red-400 border-red-500/50' : 
                          'bg-slate-800 text-slate-400 border-slate-700'
                        }
                      >
                        {s.signal}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-slate-300">
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-16 bg-slate-800 rounded-full overflow-hidden">
                          <div 
                            className={`h-full ${s.confidence > 80 ? 'bg-green-500' : 'bg-blue-500'}`} 
                            style={{ width: `${s.confidence}%` }}
                          />
                        </div>
                        <span className="text-xs">{s.confidence.toFixed(1)}%</span>
                      </div>
                    </TableCell>
                    <TableCell className="font-mono text-slate-300">${s.price.toFixed(4)}</TableCell>
                    <TableCell className="text-slate-500 italic text-sm">{s.desc} • {s.mode}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

      </div>
    </div>
  );
}
