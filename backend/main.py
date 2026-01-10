from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import pandas as pd
import pandas_ta as ta
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("[SYSTEM] Starting up...")
    if os.environ.get("AUTO_START") == "true":
        print("[SYSTEM] AUTO_START enabled. Launching Bot...")
        # Start bot in background
        await start_bot()
    yield
    # Shutdown
    print("[SYSTEM] Shutting down...")
    await stop_bot()

app = FastAPI(title="TrAIder Engine", version="1.0.0", lifespan=lifespan)

# CORS Setup - Frontend port 3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3005", "http://localhost:3006"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class HealthCheck(BaseModel):
    status: str = "OK"

class PriceData(BaseModel):
    prices: List[float]
    period: int = 14

class IndicatorResponse(BaseModel):
    name: str
    value: float
    signal: str # BUY, SELL, NEUTRAL

@app.get("/", response_model=HealthCheck)
def health_check():
    return HealthCheck(status="Active")

@app.post("/api/v1/indicators/rsi", response_model=IndicatorResponse)
def calculate_rsi(data: PriceData):
    if len(data.prices) < data.period:
        raise HTTPException(status_code=400, detail="Not enough data points")
    
    # Create Series
    series = pd.Series(data.prices)
    
    # Calculate RSI using pandas_ta
    rsi_series = series.ta.rsi(length=data.period)
    
    if rsi_series is None or rsi_series.empty:
        raise HTTPException(status_code=500, detail="Calculation failed")
        
    latest_rsi = rsi_series.iloc[-1]
    
    # Simple Signal Logic (Standard)
    signal = "NEUTRAL"
    if latest_rsi < 30:
        signal = "BUY"
    elif latest_rsi > 70:
        signal = "SELL"
        
    return {
        "name": "RSI",
        "value": round(latest_rsi, 2),
        "signal": signal
    }

import ccxt

# Initialize Exchange (Binance)
exchange = ccxt.binance()

class TickerResponse(BaseModel):
    symbol: str
    price: float
    timestamp: int

@app.get("/api/v1/market/ticker/{symbol}", response_model=TickerResponse)
async def get_ticker(symbol: str):
    try:
        # standardizing symbol (e.g. btc -> BTC/USDT)
        formatted_symbol = f"{symbol.upper()}/USDT"
        ticker = exchange.fetch_ticker(formatted_symbol)
        return {
            "symbol": formatted_symbol,
            "price": ticker['last'],
            "timestamp": ticker['timestamp']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class Candle(BaseModel):
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float

@app.get("/api/v1/market/candles/{symbol}", response_model=List[Candle])
async def get_candles(symbol: str, timeframe: str = "1h", limit: int = 100):
    try:
        formatted_symbol = f"{symbol.upper()}/USDT"
        # CCXT returns list of lists: [timestamp, open, high, low, close, volume]
        ohlcv = exchange.fetch_ohlcv(formatted_symbol, timeframe, limit=limit)
        
        candles = []
        for candle in ohlcv:
            candles.append({
                "time": int(candle[0] / 1000), # TV Charts expect seconds
                "open": candle[1],
                "high": candle[2],
                "low": candle[3],
                "close": candle[4],
                "volume": candle[5]
            })
        return candles
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from strategies import get_strategy

class StrategyRequest(BaseModel):
    strategy_id: str
    symbol: str
    timeframe: str = "1h"
    parameters: dict = {}

@app.post("/api/v1/strategy/run")
async def run_strategy(req: StrategyRequest):
    try:
        # 1. Fetch Data
        formatted_symbol = f"{req.symbol.upper()}/USDT"
        # Fetch enough data for indicators (limit=200 is safe for EMA200 etc.)
        ohlcv = exchange.fetch_ohlcv(formatted_symbol, req.timeframe, limit=200)
        
        # Convert to DataFrame
        df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        
        # 2. Load Strategy
        strategy = get_strategy(req.strategy_id, req.parameters)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
            
        # 3. Analyze
        result = strategy.analyze(df)
        
        return {
            "strategy": strategy.name,
            "symbol": req.symbol,
            "result": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from backtest_engine import SimpleBacktester

class BacktestRequest(BaseModel):
    strategy_id: str
    symbol: str
    timeframe: str = "1h"
    limit: int = 500 # More data for backtest
    parameters: dict = {}

@app.post("/api/v1/backtest/run")
async def run_backtest(req: BacktestRequest):
    try:
        # 1. Fetch Data
        formatted_symbol = f"{req.symbol.upper()}/USDT"
        ohlcv = exchange.fetch_ohlcv(formatted_symbol, req.timeframe, limit=req.limit)
        df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        
        # 2. Load Strategy
        strategy = get_strategy(req.strategy_id, req.parameters)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
            
        # 3. Run Backtest
        tester = SimpleBacktester()
        results = tester.run(strategy, df)
        
        # 4. Save to Firebase
        from services.firebase_service import firebase_client
        firebase_id = firebase_client.save_backtest({
            "symbol": req.symbol,
            "strategy": req.strategy_id,
            "results": results,
            "params": req.parameters
        })
        
        return {
            "symbol": req.symbol,
            "results": results,
            "firebase_id": firebase_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from paper_trader import run_live_cycle
import threading

@app.post("/api/v1/trade/trigger")
async def trigger_trade_cycle():
    """
    Endpoint for Cron Job to trigger a single trading cycle.
    """
    try:
        # Run in a separate thread to not block the request? 
        # Actually for a cron job, blocking is fine (it waits for 200 OK).
        print("[API] Trigger received. Running cycle...")
        run_live_cycle()
        return {"status": "Cycle completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Ensure PORT is read from env for Render
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)



