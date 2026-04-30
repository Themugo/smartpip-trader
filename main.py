# main.py - SmartPip Deriv AI Trading Bot (FIXED VERSION)
import os
import json
import asyncio
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from contextlib import asynccontextmanager
import logging
from typing import Dict, List
import websockets

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SmartPipTradingBot:
    def __init__(self):
        self.connected = False
        self.websocket = None
        self.trades = []
        self.active_trades = {}
        self.total_profit = 0.0
        self.win_count = 0
        self.loss_count = 0
        self.symbols = ["R_10", "R_25", "R_50", "R_75", "R_100"]
        self.running = True
        self.market_data = {}
        self.price_history = {}
        
        # Initialize market data structures
        for symbol in self.symbols:
            self.market_data[symbol] = {
                "price": 0,
                "change": 0,
                "spread": 0,
                "last_update": None
            }
            self.price_history[symbol] = []
    
    async def connect_deriv(self):
        api_token = os.getenv("DERIV_API_TOKEN")
        app_id = os.getenv("DERIV_APP_ID", "1089")
        
        if not api_token:
            logger.error("No API token found!")
            return False
            
        url = f"wss://ws.binaryws.com/websockets/v3?app_id={app_id}"
        
        try:
            logger.info("Connecting to Deriv...")
            self.websocket = await websockets.connect(url)
            await self.websocket.send(json.dumps({"authorize": api_token}))
            response = await self.websocket.recv()
            data = json.loads(response)
            
            if data.get("error"):
                logger.error(f"Auth failed: {data['error']['message']}")
                return False
                
            logger.info("Connected to Deriv successfully!")
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def subscribe_to_symbols(self):
        for symbol in self.symbols:
            subscribe_msg = {"ticks": symbol, "subscribe": 1}
            await self.websocket.send(json.dumps(subscribe_msg))
            logger.info(f"Subscribed to {symbol}")
    
    async def get_ai_signal(self, symbol: str, price: float) -> Dict:
        # Simple AI - replace with your actual AI
        confidence = 85.0
        direction = "CALL" if price > 0 else "PUT"  # Simplified
        return {
            "should_trade": confidence > 85,
            "direction": direction,
            "confidence": round(confidence, 1),
            "reason": "AI analysis",
            "price": price,
            "timestamp": datetime.now().isoformat()
        }
    
    async def execute_trade(self, symbol: str, signal: Dict):
        amount = float(os.getenv("BASE_TRADE_AMOUNT", "1"))
        duration = int(os.getenv("TRADE_DURATION", "2"))
        
        trade_msg = {
            "buy": 1,
            "parameters": {
                "amount": amount,
                "basis": "stake",
                "contract_type": signal['direction'].lower(),
                "currency": "USD",
                "duration": duration,
                "duration_unit": "m",
                "symbol": symbol
            }
        }
        
        try:
            await self.websocket.send(json.dumps(trade_msg))
            response = await self.websocket.recv()
            data = json.loads(response)
            
            if "buy" in data:
                contract_id = data["buy"]["contract_id"]
                logger.info(f"Trade executed: {signal['direction']} {symbol}")
                
                # Store trade (simplified)
                self.active_trades[contract_id] = {
                    "symbol": symbol,
                    "direction": signal['direction'],
                    "amount": amount,
                    "entry_time": datetime.now().isoformat()
                }
                
                # Auto close after duration
                asyncio.create_task(self.auto_close_trade(contract_id, duration * 60))
                return contract_id
        except Exception as e:
            logger.error(f"Trade execution error: {e}")
        
        return None
    
    async def auto_close_trade(self, contract_id: int, seconds: int):
        await asyncio.sleep(seconds)
        
        try:
            portfolio_msg = {"portfolio": 1}
            await self.websocket.send(json.dumps(portfolio_msg))
            response = await self.websocket.recv()
            data = json.loads(response)
            
            profit = 0
            if "portfolio" in data:
                for contract in data["portfolio"].get("contracts", []):
                    if contract["contract_id"] == contract_id:
                        profit = contract.get("profit", 0)
                        break
            
            self.total_profit += profit
            if profit > 0:
                self.win_count += 1
                logger.info(f"Trade won: +${profit}")
            else:
                self.loss_count += 1
                logger.info(f"Trade lost: ${profit}")
            
            if contract_id in self.active_trades:
                trade = self.active_trades[contract_id]
                trade["profit"] = profit
                trade["exit_time"] = datetime.now().isoformat()
                self.trades.append(trade)
                del self.active_trades[contract_id]
        except Exception as e:
            logger.error(f"Auto close error: {e}")
    
    async def process_tick(self, tick_data: Dict):
        symbol = tick_data.get("symbol")
        price = tick_data.get("quote")
        
        if not symbol or not price:
            return
        
        # Update market data
        old_price = self.market_data.get(symbol, {}).get("price", 0)
        if symbol in self.market_data:
            self.market_data[symbol]["price"] = price
            self.market_data[symbol]["change"] = ((price - old_price) / old_price * 100) if old_price > 0 else 0
            self.market_data[symbol]["last_update"] = datetime.now().isoformat()
            self.market_data[symbol]["spread"] = abs(price * 0.0001)
        
        # Store price history
        if symbol in self.price_history:
            self.price_history[symbol].append(price)
            if len(self.price_history[symbol]) > 100:
                self.price_history[symbol] = self.price_history[symbol][-100:]
        
        logger.info(f"{symbol}: ${price:.4f}")
        
        # Check trading conditions
        if len(self.active_trades) >= 3:
            return
        
        if len(self.trades) >= int(os.getenv("MAX_DAILY_TRADES", "30")):
            return
        
        # Get and execute signal
        signal = await self.get_ai_signal(symbol, price)
        if signal['should_trade']:
            await self.execute_trade(symbol, signal)
    
    async def listen_for_prices(self):
        logger.info("Listening for price ticks...")
        while self.running and self.connected:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                if "tick" in data:
                    await self.process_tick(data["tick"])
                elif "error" in data:
                    logger.error(f"Deriv error: {data['error']}")
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Connection closed, reconnecting...")
                self.connected = False
                await self.reconnect()
                break
            except Exception as e:
                logger.error(f"Listen error: {e}")
                await asyncio.sleep(1)
    
    async def reconnect(self):
        while not self.connected and self.running:
            logger.info("Reconnecting...")
            if await self.connect_deriv():
                await self.subscribe_to_symbols()
                await self.listen_for_prices()
                break
            await asyncio.sleep(5)
    
    async def run(self):
        logger.info("Starting SmartPip AI Trading Bot...")
        if await self.connect_deriv():
            await self.subscribe_to_symbols()
            await self.listen_for_prices()
    
    def get_stats(self) -> Dict:
        total_trades = self.win_count + self.loss_count
        win_rate = (self.win_count / total_trades * 100) if total_trades > 0 else 0
        
        return {
            "connected": self.connected,
            "active_trades": len(self.active_trades),
            "total_trades": total_trades,
            "win_rate": round(win_rate, 1),
            "total_profit": round(self.total_profit, 2),
            "wins": self.win_count,
            "losses": self.loss_count,
            "profit_factor": 0,
            "uptime": datetime.now().isoformat(),
            "market_data": self.market_data
        }
    
    def stop(self):
        self.running = False
        self.connected = False
        if self.websocket:
            asyncio.create_task(self.websocket.close())

# Initialize bot
bot = SmartPipTradingBot()

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(bot.run())
    yield
    bot.stop()

app = FastAPI(lifespan=lifespan)

# HTML Dashboard (simplified to ensure it works)
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>SmartPip AI Trader</title>
    <style>
        body {
            font-family: monospace;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            color: white;
        }
        .container {
            max-width: 1200px;
            margin: auto;
            background: rgba(0,0,0,0.8);
            border-radius: 20px;
            padding: 30px;
        }
        h1 { text-align: center; }
        .stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin: 30px 0;
        }
        .stat-card {
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-value {
            font-size: 32px;
            font-weight: bold;
            margin-top: 10px;
        }
        .profit { color: #4caf50; }
        .loss { color: #f44336; }
        .status {
            text-align: center;
            padding: 10px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .online { background: #4caf50; }
        .offline { background: #f44336; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 SmartPip AI Trader</h1>
        <div class="status online" id="status">🟢 Bot Active</div>
        
        <div class="stats">
            <div class="stat-card">
                <div>Active Trades</div>
                <div class="stat-value" id="active">0</div>
            </div>
            <div class="stat-card">
                <div>Win Rate</div>
                <div class="stat-value" id="winrate">0%</div>
            </div>
            <div class="stat-card">
                <div>Total P&L</div>
                <div class="stat-value" id="pnl">$0</div>
            </div>
            <div class="stat-card">
                <div>Total Trades</div>
                <div class="stat-value" id="totaltrades">0</div>
            </div>
        </div>
        
        <div style="text-align: center;">
            <button onclick="location.reload()" style="background:#667eea; color:white; padding:10px 20px; border:none; border-radius:5px; cursor:pointer;">🔄 Refresh</button>
        </div>
    </div>
    
    <script>
        async function loadStats() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                document.getElementById('active').innerText = data.active_trades || 0;
                document.getElementById('winrate').innerText = (data.win_rate || 0) + '%';
                const pnl = document.getElementById('pnl');
                pnl.innerText = '$' + (data.total_profit || 0);
                document.getElementById('totaltrades').innerText = data.total_trades || 0;
            } catch(e) {
                console.error(e);
            }
        }
        loadStats();
        setInterval(loadStats, 3000);
    </script>
</body>
</html>
"""

@app.get("/")
async def root():
    return HTMLResponse(DASHBOARD_HTML)

@app.get("/api/status")
async def get_status():
    return JSONResponse(bot.get_stats())

@app.get("/api/trades")
async def get_trades():
    return JSONResponse(bot.trades[-50:])

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            stats = bot.get_stats()
            await websocket.send_json(stats)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass

@app.get("/health")
async def health():
    return JSONResponse({"status": "healthy", "timestamp": datetime.now().isoformat()})

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)