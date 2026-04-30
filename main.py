# main.py - SmartPip Deriv AI Trading Bot
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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SmartPipTradingBot:
    """Main trading bot class"""
    
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
        
    async def connect_deriv(self):
        """Connect to Deriv WebSocket"""
        api_token = os.getenv("DERIV_API_TOKEN")
        app_id = os.getenv("DERIV_APP_ID", "1089")
        
        if not api_token:
            logger.error("❌ No API token found! Set DERIV_API_TOKEN environment variable")
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
        """
        AI Trading Signal Generator
        Replace this with your actual AI model
        """
        # Simulated AI analysis - Replace with your real AI
        # This is just for demonstration
        
        # Calculate some indicators (simplified)
        # In production, use your UltimateTradingSystem
        
        # Random confidence between 80-98% for demo
        confidence = random.uniform(80, 98)
        
        # Simple trend detection (replace with your AI)
        if len(self.trades) > 10:
            recent_wins = len([t for t in self.trades[-10:] if t.get('profit', 0) > 0])
            win_rate = recent_wins / 10
            confidence = confidence * (0.8 + win_rate * 0.2)
        
        # Determine direction based on price action (simplified)
        direction = "CALL" if random.random() > 0.5 else "PUT"
        
        return {
            "should_trade": confidence > 85,
            "direction": direction,
            "confidence": round(confidence, 1),
            "reason": f"AI Confidence: {confidence:.1f}%",
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
            
            logger.info(f"🎯 TRADE EXECUTED: {signal['direction']} {symbol}")
            logger.info(f"   Amount: ${amount} | Confidence: {signal['confidence']}%")
            logger.info(f"   Contract ID: {contract_id}")
            
            # Auto close after duration
            asyncio.create_task(self.auto_close_trade(contract_id, duration * 60))
            
            return contract_id
        
        return None
    
    async def auto_close_trade(self, contract_id: int, seconds: int):
        """Auto-close trade after duration"""
        await asyncio.sleep(seconds)
        
        if contract_id not in self.active_trades:
            return
            
        # Get contract status
        portfolio_msg = {"portfolio": 1}
        await self.websocket.send(json.dumps(portfolio_msg))
        response = await self.websocket.recv()
        data = json.loads(response)
        
        profit = 0
        buy_price = 0
        sell_price = 0
        
        if "portfolio" in data:
            for contract in data["portfolio"].get("contracts", []):
                if contract["contract_id"] == contract_id:
                    profit = contract.get("profit", 0)
                    buy_price = contract.get("buy_price", 0)
                    sell_price = contract.get("sell_price", 0)
                    break
        
        # Update stats
        self.total_profit += profit
        if profit > 0:
            self.win_count += 1
            logger.info(f"✅ TRADE WON: +${profit:.2f}")
        else:
            self.loss_count += 1
            logger.info(f"❌ TRADE LOST: ${profit:.2f}")
        
        # Record trade
        if contract_id in self.active_trades:
            trade = self.active_trades[contract_id]
            trade["profit"] = profit
            trade["buy_price"] = buy_price
            trade["sell_price"] = sell_price
            trade["exit_time"] = datetime.now().isoformat()
            self.trades.append(trade)
            del self.active_trades[contract_id]
    
    async def process_tick(self, tick_data: Dict):
        """Process incoming price tick"""
        symbol = tick_data.get("symbol")
        price = tick_data.get("quote")
        
        if not symbol or not price:
            return
        
        # Check if we should trade based on limits
        if len(self.active_trades) >= 3:
            return  # Max 3 concurrent trades
            
        if len(self.trades) >= int(os.getenv("MAX_DAILY_TRADES", "30")):
            return  # Daily limit reached
        
        # Get AI signal
        signal = await self.get_ai_signal(symbol, float(price))
        
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
        
        # Calculate profit factor
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
            "uptime": datetime.now().isoformat()
        }
    
    def stop(self):
        """Stop the bot"""
        self.running = False
        self.connected = False
        if self.websocket:
            asyncio.create_task(self.websocket.close())

# Initialize bot
bot = SmartPipTradingBot()

# FastAPI app with lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 FastAPI starting up...")
    asyncio.create_task(bot.run())
    yield
    # Shutdown
    logger.info("👋 Shutting down...")
    bot.stop()

app = FastAPI(
    title="SmartPip AI Trading System",
    description="Advanced AI Trading Bot for Deriv Volatility Indices",
    version="2.0.0",
    lifespan=lifespan
)

# HTML Dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SmartPip AI Trader</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 3em;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
        }
        
        .stat-label {
            font-size: 14px;
            text-transform: uppercase;
            color: #666;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }
        
        .stat-value {
            font-size: 36px;
            font-weight: bold;
            color: #333;
        }
        
        .profit {
            color: #10b981;
        }
        
        .loss {
            color: #ef4444;
        }
        
        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            margin-top: 10px;
        }
        
        .status-online {
            background: #10b981;
            color: white;
        }
        
        .status-offline {
            background: #ef4444;
            color: white;
        }
        
        .trades-section {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        .trades-section h2 {
            margin-bottom: 20px;
            color: #333;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }
        
        th {
            background: #f9fafb;
            font-weight: 600;
            color: #374151;
        }
        
        tr:hover {
            background: #f9fafb;
        }
        
        .trade-win {
            color: #10b981;
            font-weight: bold;
        }
        
        .trade-loss {
            color: #ef4444;
            font-weight: bold;
        }
        
        .button-group {
            text-align: center;
            margin-top: 20px;
        }
        
        button {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            margin: 0 5px;
            transition: background 0.3s;
        }
        
        button:hover {
            background: #5a67d8;
        }
        
        .websocket-status {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: white;
            padding: 10px 15px;
            border-radius: 10px;
            font-size: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .live {
            animation: pulse 2s infinite;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 SmartPip AI Trader</h1>
            <p>Advanced AI-powered trading for Deriv Volatility Indices</p>
        </div>
        
        <div class="stats-grid">
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
            <div class="stat-card">
                <div class="stat-label">Wins / Losses</div>
                <div class="stat-value" id="wlRatio">0/0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Profit Factor</div>
                <div class="stat-value" id="profitFactor">0</div>
            </div>
        </div>
        
        <div class="trades-section">
            <h2>📊 Recent Trades</h2>
            <div style="overflow-x: auto;">
                <table id="tradesTable">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Symbol</th>
                            <th>Direction</th>
                            <th>Amount</th>
                            <th>Entry Price</th>
                            <th>Exit Price</th>
                            <th>Profit/Loss</th>
                            <th>Confidence</th>
                        </tr>
                    </thead>
                    <tbody id="tradesBody">
                        <tr><td colspan="8" style="text-align: center;">Loading trades...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="button-group">
            <button onclick="refreshData()">🔄 Refresh</button>
            <button onclick="viewAPI()">📡 API Status</button>
            <button onclick="clearData()">🗑️ Clear History</button>
        </div>
    </div>
    
    <div class="websocket-status" id="wsStatus">
        📡 WebSocket: Connecting...
    </div>
    
    <script>
        let ws = null;
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            ws = new WebSocket(wsUrl);
            
            ws.onopen = function() {
                document.getElementById('wsStatus').innerHTML = '✅ WebSocket: Connected';
                document.getElementById('wsStatus').style.background = '#10b981';
                document.getElementById('wsStatus').style.color = 'white';
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            
            ws.onclose = function() {
                document.getElementById('wsStatus').innerHTML = '❌ WebSocket: Disconnected';
                document.getElementById('wsStatus').style.background = '#ef4444';
                setTimeout(connectWebSocket, 3000);
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
            };
        }
        
        function updateDashboard(data) {
            if (data.active_trades !== undefined) {
                document.getElementById('activeTrades').innerText = data.active_trades;
            }
            if (data.win_rate !== undefined) {
                document.getElementById('winRate').innerText = data.win_rate + '%';
            }
            if (data.total_profit !== undefined) {
                const pnlElem = document.getElementById('totalPnl');
                pnlElem.innerText = '$' + data.total_profit.toFixed(2);
                pnlElem.className = 'stat-value ' + (data.total_profit > 0 ? 'profit' : data.total_profit < 0 ? 'loss' : '');
            }
            if (data.total_trades !== undefined) {
                document.getElementById('totalTrades').innerText = data.total_trades;
                document.getElementById('wlRatio').innerText = `${data.wins || 0}/${data.losses || 0}`;
            }
            if (data.profit_factor !== undefined) {
                document.getElementById('profitFactor').innerText = data.profit_factor;
            }
        }
        
        async function refreshData() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                updateDashboard(data);
                
                const tradesResponse = await fetch('/api/trades');
                const trades = await tradesResponse.json();
                updateTradesTable(trades);
            } catch(e) {
                console.error('Refresh error:', e);
            }
        }
        
        function updateTradesTable(trades) {
            const tbody = document.getElementById('tradesBody');
            tbody.innerHTML = '';
            
            if (trades.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No trades yet</td></tr>';
                return;
            }
            
            trades.slice().reverse().forEach(trade => {
                const row = tbody.insertRow();
                row.insertCell(0).innerText = new Date(trade.entry_time).toLocaleString();
                row.insertCell(1).innerText = trade.symbol;
                row.insertCell(2).innerHTML = trade.direction === 'CALL' ? '📈 CALL' : '📉 PUT';
                row.insertCell(3).innerText = '$' + trade.amount;
                row.insertCell(4).innerText = '$' + (trade.entry_price || 0);
                row.insertCell(5).innerText = '$' + (trade.sell_price || 0);
                const profitCell = row.insertCell(6);
                const profit = trade.profit || 0;
                profitCell.innerHTML = profit > 0 ? `+$${profit.toFixed(2)}` : `$${profit.toFixed(2)}`;
                profitCell.className = profit > 0 ? 'trade-win' : profit < 0 ? 'trade-loss' : '';
                row.insertCell(7).innerHTML = `${trade.confidence || 0}%`;
            });
        }
        
        function viewAPI() {
            window.open('/api/status', '_blank');
        }
        
        async function clearData() {
            if (confirm('Are you sure? This will only clear local display.')) {
                document.getElementById('tradesBody').innerHTML = '<tr><td colspan="8" style="text-align: center;">Loading...</td></tr>';
                await refreshData();
            }
        }
        
        // Initial load
        connectWebSocket();
        refreshData();
        setInterval(refreshData, 5000);
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
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "bot_running": bot.connected,
        "active_trades": len(bot.active_trades)
    })

# For local testing
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)