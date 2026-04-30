# main.py - SmartPip Deriv AI Trading Bot with REAL Market Data
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
import random

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SmartPipTradingBot:
    """Main trading bot class with real market data"""
    
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
        
        # Store real market data
        self.market_data = {
            "R_10": {"price": 0, "change": 0, "spread": 0, "last_update": None},
            "R_25": {"price": 0, "change": 0, "spread": 0, "last_update": None},
            "R_50": {"price": 0, "change": 0, "spread": 0, "last_update": None},
            "R_75": {"price": 0, "change": 0, "spread": 0, "last_update": None},
            "R_100": {"price": 0, "change": 0, "spread": 0, "last_update": None}
        }
        self.price_history = {symbol: [] for symbol in self.symbols}
        
    async def connect_deriv(self):
        """Connect to Deriv WebSocket"""
        api_token = os.getenv("DERIV_API_TOKEN")
        app_id = os.getenv("DERIV_APP_ID", "1089")
        
        if not api_token:
            logger.error("❌ No API token found!")
            return False
            
        url = f"wss://ws.binaryws.com/websockets/v3?app_id={app_id}"
        
        try:
            logger.info("🔌 Connecting to Deriv...")
            self.websocket = await websockets.connect(url)
            
            # Authorize
            await self.websocket.send(json.dumps({"authorize": api_token}))
            response = await self.websocket.recv()
            data = json.loads(response)
            
            if data.get("error"):
                logger.error(f"❌ Auth failed: {data['error']['message']}")
                return False
                
            logger.info("✅ Connected to Deriv successfully!")
            self.connected = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return False
    
    async def subscribe_to_symbols(self):
        """Subscribe to all volatility indices"""
        for symbol in self.symbols:
            subscribe_msg = {
                "ticks": symbol,
                "subscribe": 1
            }
            await self.websocket.send(json.dumps(subscribe_msg))
            logger.info(f"📡 Subscribed to {symbol}")
    
    async def get_ai_signal(self, symbol: str, price: float) -> Dict:
        """AI Trading Signal Generator - Replace with your actual AI"""
        # Get recent prices for analysis
        recent_prices = self.price_history.get(symbol, [])[-20:]
        
        # Simple trend detection (replace with your AI)
        confidence = 85.0  # Base confidence
        
        if len(recent_prices) > 5:
            # Calculate short-term momentum
            momentum = (price - recent_prices[-5]) / recent_prices[-5] * 100
            if abs(momentum) > 0.1:
                confidence += min(abs(momentum) * 10, 10)
        
        # Determine direction based on price action
        direction = "CALL" if price > recent_prices[-1] if recent_prices else True else "PUT"
        
        return {
            "should_trade": confidence > 85,
            "direction": direction,
            "confidence": round(confidence, 1),
            "reason": f"AI Analysis: {direction} signal",
            "price": price,
            "timestamp": datetime.now().isoformat()
        }
    
    async def execute_trade(self, symbol: str, signal: Dict):
        """Execute trade on Deriv"""
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
        
        await self.websocket.send(json.dumps(trade_msg))
        response = await self.websocket.recv()
        data = json.loads(response)
        
        if "buy" in data:
            contract_id = data["buy"]["contract_id"]
            self.active_trades[contract_id] = {
                "symbol": symbol,
                "direction": signal['direction'],
                "amount": amount,
                "confidence": signal['confidence'],
                "entry_price": signal['price'],
                "entry_time": datetime.now().isoformat(),
                "duration": duration
            }
            
            logger.info(f"🎯 TRADE EXECUTED: {signal['direction']} {symbol} at ${signal['price']}")
            logger.info(f"   Amount: ${amount} | Confidence: {signal['confidence']}%")
            
            asyncio.create_task(self.auto_close_trade(contract_id, duration * 60))
            return contract_id
        
        return None
    
    async def auto_close_trade(self, contract_id: int, seconds: int):
        """Auto-close trade after duration"""
        await asyncio.sleep(seconds)
        
        if contract_id not in self.active_trades:
            return
            
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
            logger.info(f"✅ TRADE WON: +${profit:.2f}")
        else:
            self.loss_count += 1
            logger.info(f"❌ TRADE LOST: ${profit:.2f}")
        
        if contract_id in self.active_trades:
            trade = self.active_trades[contract_id]
            trade["profit"] = profit
            trade["exit_time"] = datetime.now().isoformat()
            self.trades.append(trade)
            del self.active_trades[contract_id]
    
    async def process_tick(self, tick_data: Dict):
        """Process incoming price tick and update market data"""
        symbol = tick_data.get("symbol")
        price = tick_data.get("quote")
        
        if not symbol or not price:
            return
        
        # Update market data
        old_price = self.market_data[symbol]["price"]
        self.market_data[symbol]["price"] = price
        self.market_data[symbol]["change"] = ((price - old_price) / old_price * 100) if old_price > 0 else 0
        self.market_data[symbol]["last_update"] = datetime.now().isoformat()
        
        # Update price history
        self.price_history[symbol].append(price)
        if len(self.price_history[symbol]) > 100:
            self.price_history[symbol] = self.price_history[symbol][-100:]
        
        # Calculate spread (simulated - Deriv doesn't provide direct spread in ticks)
        self.market_data[symbol]["spread"] = abs(price * 0.0001)  # Estimated 0.01% spread
        
        logger.info(f"📊 {symbol}: ${price:.4f} | Change: {self.market_data[symbol]['change']:+.2f}%")
        
        # Check trading conditions
        if len(self.active_trades) >= 3:
            return
            
        if len(self.trades) >= int(os.getenv("MAX_DAILY_TRADES", "30")):
            return
        
        # Get AI signal
        signal = await self.get_ai_signal(symbol, price)
        
        if signal['should_trade']:
            await self.execute_trade(symbol, signal)
    
    async def listen_for_prices(self):
        """Main listening loop"""
        logger.info("👂 Listening for price ticks...")
        
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
                logger.error(f"Error in listen loop: {e}")
                await asyncio.sleep(1)
    
    async def reconnect(self):
        """Reconnect to Deriv"""
        while not self.connected and self.running:
            logger.info("🔄 Attempting to reconnect...")
            if await self.connect_deriv():
                await self.subscribe_to_symbols()
                await self.listen_for_prices()
                break
            await asyncio.sleep(5)
    
    async def run(self):
        """Main bot entry point"""
        logger.info("🤖 SmartPip AI Trading Bot Starting...")
        
        if await self.connect_deriv():
            await self.subscribe_to_symbols()
            await self.listen_for_prices()
    
    def get_stats(self) -> Dict:
        """Get trading statistics"""
        total_trades = self.win_count + self.loss_count
        win_rate = (self.win_count / total_trades * 100) if total_trades > 0 else 0
        
        gross_profit = sum(t.get('profit', 0) for t in self.trades if t.get('profit', 0) > 0)
        gross_loss = abs(sum(t.get('profit', 0) for t in self.trades if t.get('profit', 0) < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        return {
            "connected": self.connected,
            "active_trades": len(self.active_trades),
            "total_trades": total_trades,
            "win_rate": round(win_rate, 1),
            "total_profit": round(self.total_profit, 2),
            "wins": self.win_count,
            "losses": self.loss_count,
            "profit_factor": round(profit_factor, 2),
            "uptime": datetime.now().isoformat(),
            "market_data": self.market_data
        }
    
    def stop(self):
        """Stop the bot"""
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

# HTML Dashboard with REAL Market Data
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SmartPip AI Trader - Real Market Data</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            min-height: 100vh;
            padding: 20px;
            color: #fff;
        }
        
        .container {
            max-width: 1600px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5em;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        
        .market-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .market-card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.2);
            transition: transform 0.3s;
        }
        
        .market-card:hover {
            transform: translateY(-5px);
            background: rgba(255,255,255,0.15);
        }
        
        .symbol {
            font-size: 1.5em;
            font-weight: bold;
            margin-bottom: 15px;
            color: #667eea;
        }
        
        .price {
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }
        
        .change {
            font-size: 1.1em;
            margin: 5px 0;
        }
        
        .positive {
            color: #10b981;
        }
        
        .negative {
            color: #ef4444;
        }
        
        .spread {
            font-size: 0.9em;
            opacity: 0.7;
            margin-top: 10px;
        }
        
        .update-time {
            font-size: 0.8em;
            opacity: 0.5;
            margin-top: 10px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
        }
        
        .stat-label {
            font-size: 0.9em;
            opacity: 0.7;
            margin-bottom: 10px;
        }
        
        .stat-value {
            font-size: 1.8em;
            font-weight: bold;
        }
        
        .trades-section {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            margin-top: 20px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        
        th {
            background: rgba(102,126,234,0.3);
            font-weight: 600;
        }
        
        .live-badge {
            display: inline-block;
            width: 10px;
            height: 10px;
            background: #10b981;
            border-radius: 50%;
            animation: pulse 2s infinite;
            margin-right: 10px;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
        
        .websocket-status {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: rgba(0,0,0,0.8);
            padding: 10px 15px;
            border-radius: 10px;
            font-size: 12px;
            font-family: monospace;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 SmartPip AI Trader</h1>
            <p>Real-time Deriv Volatility Index Market Data</p>
        </div>
        
        <div class="market-grid" id="marketGrid">
            <div style="text-align: center; grid-column: 1/-1;">Loading market data...</div>
        </div>
        
        <div class="stats-grid" id="statsGrid">
            <div class="stat-card">
                <div class="stat-label">Active Trades</div>
                <div class="stat-value" id="activeTrades">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Win Rate</div>
                <div class="stat-value" id="winRate">0%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total P&L</div>
                <div class="stat-value" id="totalPnl">$0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Trades</div>
                <div class="stat-value" id="totalTrades">0</div>
            </div>
        </div>
        
        <div class="trades-section">
            <h2>📊 Recent Trades</h2>
            <div style="overflow-x: auto;">
                <table id="tradesTable">
                    <thead>
                        <tr><th>Time</th><th>Symbol</th><th>Direction</th><th>Entry Price</th><th>Profit</th><th>Confidence</th></tr>
                    </thead>
                    <tbody id="tradesBody">
                        <tr><td colspan="6" style="text-align: center;">No trades yet</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    
    <div class="websocket-status" id="wsStatus">
        <span class="live-badge"></span> WebSocket: Connecting...
    </div>
    
    <script>
        let ws = null;
        
        const symbols = ['R_10', 'R_25', 'R_50', 'R_75', 'R_100'];
        const symbolNames = {
            'R_10': 'Volatility 10',
            'R_25': 'Volatility 25', 
            'R_50': 'Volatility 50',
            'R_75': 'Volatility 75',
            'R_100': 'Volatility 100'
        };
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            ws = new WebSocket(wsUrl);
            
            ws.onopen = function() {
                document.getElementById('wsStatus').innerHTML = '<span class="live-badge"></span> WebSocket: Connected ✅';
                document.getElementById('wsStatus').style.background = 'rgba(16,185,129,0.9)';
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            
            ws.onclose = function() {
                document.getElementById('wsStatus').innerHTML = '<span class="live-badge"></span> WebSocket: Disconnected ❌';
                document.getElementById('wsStatus').style.background = 'rgba(239,68,68,0.9)';
                setTimeout(connectWebSocket, 3000);
            };
        }
        
        function updateDashboard(data) {
            // Update market data grid
            if (data.market_data) {
                const marketGrid = document.getElementById('marketGrid');
                marketGrid.innerHTML = '';
                
                for (const symbol of symbols) {
                    const market = data.market_data[symbol];
                    if (market && market.price > 0) {
                        const changeClass = market.change >= 0 ? 'positive' : 'negative';
                        const changeSign = market.change >= 0 ? '+' : '';
                        
                        const card = document.createElement('div');
                        card.className = 'market-card';
                        card.innerHTML = `
                            <div class="symbol">${symbolNames[symbol]} (${symbol})</div>
                            <div class="price">$${market.price.toFixed(4)}</div>
                            <div class="change ${changeClass}">Change: ${changeSign}${market.change.toFixed(2)}%</div>
                            <div class="spread">Spread: $${market.spread.toFixed(4)}</div>
                            <div class="update-time">Updated: ${market.last_update ? new Date(market.last_update).toLocaleTimeString() : 'Never'}</div>
                        `;
                        marketGrid.appendChild(card);
                    }
                }
            }
            
            // Update stats
            if (data.active_trades !== undefined) {
                document.getElementById('activeTrades').innerText = data.active_trades;
            }
            if (data.win_rate !== undefined) {
                document.getElementById('winRate').innerText = data.win_rate + '%';
            }
            if (data.total_profit !== undefined) {
                const pnlElem = document.getElementById('totalPnl');
                pnlElem.innerText = '$' + data.total_profit.toFixed(2);
                pnlElem.style.color = data.total_profit >= 0 ? '#10b981' : '#ef4444';
            }
            if (data.total_trades !== undefined) {
                document.getElementById('totalTrades').innerText = data.total_trades;
            }
        }
        
        async function loadTrades() {
            try {
                const response = await fetch('/api/trades');
                const trades = await response.json();
                const tbody = document.getElementById('tradesBody');
                tbody.innerHTML = '';
                
                if (trades.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No trades yet</td></tr>';
                    return;
                }
                
                trades.slice().reverse().forEach(trade => {
                    const row = tbody.insertRow();
                    row.insertCell(0).innerText = new Date(trade.entry_time).toLocaleTimeString();
                    row.insertCell(1).innerText = trade.symbol;
                    row.insertCell(2).innerHTML = trade.direction === 'CALL' ? '📈 CALL' : '📉 PUT';
                    row.insertCell(3).innerText = '$' + (trade.entry_price || 0);
                    const profitCell = row.insertCell(4);
                    const profit = trade.profit || 0;
                    profitCell.innerHTML = profit >= 0 ? `+$${profit.toFixed(2)}` : `-$${Math.abs(profit).toFixed(2)}`;
                    profitCell.style.color = profit >= 0 ? '#10b981' : '#ef4444';
                    row.insertCell(5).innerHTML = `${trade.confidence || 0}%`;
                });
            } catch(e) {
                console.error('Error loading trades:', e);
            }
        }
        
        // Initial load
        connectWebSocket();
        loadTrades();
        setInterval(loadTrades, 10000);
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
            await asyncio.sleep(1)  # Update every second for real-time
    except WebSocketDisconnect:
        pass

@app.get("/health")
async def health():
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "bot_running": bot.connected,
        "active_trades": len(bot.active_trades)
    })

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)