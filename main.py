# main.py - Professional Trading Platform (FIXED)
import os
import json
import asyncio
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from contextlib import asynccontextmanager
import logging
from typing import Dict, List
import websockets
from collections import deque

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProfessionalTradingBot:
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
        self.account_balance = 10000.0
        self.equity_curve = []
        self.price_history = {symbol: deque(maxlen=100) for symbol in self.symbols}
        
        # Initialize market data
        self.market_data = {}
        for symbol in self.symbols:
            self.market_data[symbol] = {
                "price": 0,
                "change": 0,
                "change_pct": 0,
                "high": 0,
                "low": 0,
                "spread": 0,
                "last_update": None
            }
        
        # Settings
        self.settings = {
            "default_amount": 10,
            "default_duration": 5,
            "auto_trade": True
        }
        
        self.performance = {
            "best_trade": 0,
            "worst_trade": 0,
            "max_drawdown": 0
        }
    
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
            
            # Get balance
            await self.websocket.send(json.dumps({"balance": 1}))
            balance_response = await self.websocket.recv()
            balance_data = json.loads(balance_response)
            if "balance" in balance_data:
                self.account_balance = balance_data["balance"]["balance"]
            
            logger.info(f"Connected! Balance: ${self.account_balance:,.2f}")
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
    
    async def process_tick(self, tick_data: Dict):
        symbol = tick_data.get("symbol")
        price = tick_data.get("quote")
        
        if not symbol or not price:
            return
        
        # Update market data
        old_price = self.market_data[symbol]["price"]
        self.market_data[symbol]["price"] = price
        self.market_data[symbol]["change"] = price - old_price
        self.market_data[symbol]["change_pct"] = ((price - old_price) / old_price * 100) if old_price > 0 else 0
        self.market_data[symbol]["last_update"] = datetime.now().isoformat()
        
        # Update high/low
        if price > self.market_data[symbol]["high"] or self.market_data[symbol]["high"] == 0:
            self.market_data[symbol]["high"] = price
        if price < self.market_data[symbol]["low"] or self.market_data[symbol]["low"] == 0:
            self.market_data[symbol]["low"] = price
        
        # Store price history
        self.price_history[symbol].append(price)
        
        logger.info(f"{symbol}: ${price:.4f} ({self.market_data[symbol]['change_pct']:+.2f}%)")
        
        # Auto trading logic
        if self.settings["auto_trade"] and len(self.active_trades) < 3:
            await self.check_auto_trade(symbol, price)
    
    async def check_auto_trade(self, symbol: str, price: float):
        """Simple trading logic - replace with your AI"""
        # Get price history
        prices = list(self.price_history.get(symbol, []))
        if len(prices) < 20:
            return
        
        # Calculate simple moving average
        sma = sum(prices[-20:]) / 20
        
        # Calculate volatility
        volatility = 0
        if len(prices) >= 20:
            returns = [prices[i] - prices[i-1] for i in range(-19, 0)]
            volatility = sum(abs(r) for r in returns) / len(returns) if returns else 0
        
        # Signal generation
        if price > sma and volatility > 0.001:
            confidence = 75 + min(volatility * 1000, 20)
            direction = "CALL"
            reason = "Price above SMA with momentum"
            await self.execute_trade(symbol, direction, confidence, reason)
        elif price < sma and volatility > 0.001:
            confidence = 75 + min(volatility * 1000, 20)
            direction = "PUT"
            reason = "Price below SMA with momentum"
            await self.execute_trade(symbol, direction, confidence, reason)
    
    async def execute_trade(self, symbol: str, direction: str, confidence: float, reason: str):
        amount = self.settings["default_amount"]
        duration = self.settings["default_duration"]
        
        trade_msg = {
            "buy": 1,
            "parameters": {
                "amount": amount,
                "basis": "stake",
                "contract_type": direction.lower(),
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
                self.active_trades[contract_id] = {
                    "symbol": symbol,
                    "direction": direction,
                    "amount": amount,
                    "confidence": confidence,
                    "entry_price": self.market_data[symbol]["price"],
                    "entry_time": datetime.now().isoformat(),
                    "duration": duration,
                    "reason": reason
                }
                
                logger.info(f"🎯 TRADE: {direction} {symbol} | ${amount} | {confidence:.0f}%")
                asyncio.create_task(self.auto_close_trade(contract_id, duration * 60))
        except Exception as e:
            logger.error(f"Trade error: {e}")
    
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
            self.account_balance += profit
            
            if profit > 0:
                self.win_count += 1
                if profit > self.performance["best_trade"]:
                    self.performance["best_trade"] = profit
            else:
                self.loss_count += 1
                if profit < self.performance["worst_trade"]:
                    self.performance["worst_trade"] = profit
            
            if contract_id in self.active_trades:
                trade = self.active_trades[contract_id]
                trade["profit"] = profit
                trade["exit_time"] = datetime.now().isoformat()
                self.trades.append(trade)
                del self.active_trades[contract_id]
                
                # Update equity curve
                self.equity_curve.append({
                    "time": datetime.now().isoformat(),
                    "equity": self.account_balance,
                    "profit": profit
                })
                
                # Calculate drawdown
                if self.equity_curve:
                    equities = [e["equity"] for e in self.equity_curve]
                    peak = max(equities)
                    current = equities[-1]
                    drawdown = (peak - current) / peak * 100
                    if drawdown > self.performance["max_drawdown"]:
                        self.performance["max_drawdown"] = drawdown
                
                logger.info(f"{'✅ WIN' if profit > 0 else '❌ LOSS'}: ${profit:.2f}")
        except Exception as e:
            logger.error(f"Close error: {e}")
    
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
        if await self.connect_deriv():
            await self.subscribe_to_symbols()
            await self.listen_for_prices()
    
    def get_full_state(self) -> Dict:
        total_trades = self.win_count + self.loss_count
        win_rate = (self.win_count / total_trades * 100) if total_trades > 0 else 0
        
        return {
            "connected": self.connected,
            "account_balance": self.account_balance,
            "active_trades": len(self.active_trades),
            "total_trades": total_trades,
            "win_rate": round(win_rate, 1),
            "total_profit": round(self.total_profit, 2),
            "wins": self.win_count,
            "losses": self.loss_count,
            "market_data": self.market_data,
            "settings": self.settings,
            "performance": self.performance,
            "active_trades_list": list(self.active_trades.values())
        }
    
    def stop(self):
        self.running = False
        if self.websocket:
            asyncio.create_task(self.websocket.close())

# Initialize bot
bot = ProfessionalTradingBot()

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(bot.run())
    yield
    bot.stop()

app = FastAPI(lifespan=lifespan)

# HTML Dashboard (simplified but professional)
HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SmartPip Pro - Trading Platform</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0e27;
            color: #e2e8f0;
        }
        .header {
            background: linear-gradient(135deg, #0f1235, #1a1f4e);
            padding: 15px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #2d3748;
        }
        .logo { font-size: 20px; font-weight: bold; background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .balance-card { background: rgba(16, 185, 129, 0.1); padding: 8px 16px; border-radius: 10px; border: 1px solid rgba(16, 185, 129, 0.3); }
        .balance-value { font-size: 20px; font-weight: bold; color: #10b981; }
        .container { display: grid; grid-template-columns: 300px 1fr 320px; gap: 20px; padding: 20px; min-height: calc(100vh - 70px); }
        .panel { background: #0f1235; border-radius: 15px; padding: 20px; border: 1px solid #2d3748; }
        .panel-title { font-size: 14px; text-transform: uppercase; color: #94a3b8; margin-bottom: 20px; }
        .market-item { padding: 12px; border-bottom: 1px solid #1e2345; cursor: pointer; }
        .market-item:hover { background: rgba(102, 126, 234, 0.1); border-radius: 8px; }
        .market-price { font-size: 18px; font-weight: bold; }
        .positive { color: #10b981; }
        .negative { color: #ef4444; }
        .chart-container { padding: 20px; height: 400px; }
        .trade-buttons { display: flex; gap: 15px; margin-bottom: 20px; }
        .btn-call, .btn-put { flex: 1; padding: 12px; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; transition: transform 0.2s; }
        .btn-call { background: linear-gradient(135deg, #10b981, #059669); color: white; }
        .btn-put { background: linear-gradient(135deg, #ef4444, #dc2626); color: white; }
        .btn-call:hover, .btn-put:hover { transform: translateY(-2px); }
        .param-input { background: #1a1f4e; border: 1px solid #2d3748; color: white; padding: 8px 12px; border-radius: 6px; width: 100%; }
        .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px; }
        .stat-card { background: #1a1f4e; padding: 12px; border-radius: 10px; text-align: center; }
        .stat-value { font-size: 20px; font-weight: bold; }
        .active-trades { max-height: 300px; overflow-y: auto; }
        .trade-item { background: #1a1f4e; padding: 10px; border-radius: 8px; margin-bottom: 10px; }
        .status-dot { width: 8px; height: 8px; background: #10b981; border-radius: 50%; display: inline-block; animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">🤖 SmartPip Pro Trading Platform</div>
        <div class="balance-card">
            <div>Account Balance</div>
            <div class="balance-value" id="balance">$10,000</div>
        </div>
    </div>
    
    <div class="container">
        <div class="panel">
            <div class="panel-title">📊 Market Overview</div>
            <div id="marketList"></div>
        </div>
        
        <div class="panel">
            <div class="chart-container">
                <canvas id="priceChart"></canvas>
            </div>
            <div style="padding: 20px; border-top: 1px solid #2d3748;">
                <div class="trade-buttons">
                    <button class="btn-call" onclick="manualTrade('CALL')">📈 CALL</button>
                    <button class="btn-put" onclick="manualTrade('PUT')">📉 PUT</button>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                    <div>
                        <div style="font-size: 12px; color: #94a3b8;">Amount ($)</div>
                        <input type="number" id="amount" class="param-input" value="10">
                    </div>
                    <div>
                        <div style="font-size: 12px; color: #94a3b8;">Duration (min)</div>
                        <input type="number" id="duration" class="param-input" value="5">
                    </div>
                </div>
            </div>
        </div>
        
        <div class="panel">
            <div class="panel-title">💰 Portfolio</div>
            <div class="stats-grid">
                <div class="stat-card"><div>Win Rate</div><div class="stat-value" id="winRate">0%</div></div>
                <div class="stat-card"><div>Total P&L</div><div class="stat-value" id="pnl">$0</div></div>
                <div class="stat-card"><div>Active</div><div class="stat-value" id="activeTrades">0</div></div>
                <div class="stat-card"><div>Total Trades</div><div class="stat-value" id="totalTrades">0</div></div>
            </div>
            <div class="panel-title">📋 Active Positions</div>
            <div class="active-trades" id="activeTradesList"><div style="text-align: center;">No active trades</div></div>
        </div>
    </div>
    
    <script>
        let ws = null, chart = null, chartData = { labels: [], prices: [] };
        
        function initChart() {
            const ctx = document.getElementById('priceChart').getContext('2d');
            chart = new Chart(ctx, {
                type: 'line',
                data: { labels: [], datasets: [{ label: 'R_100 Price', data: [], borderColor: '#667eea', backgroundColor: 'rgba(102,126,234,0.1)', borderWidth: 2, fill: true }] },
                options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { labels: { color: '#e2e8f0' } } }, scales: { y: { grid: { color: '#2d3748' }, ticks: { color: '#e2e8f0' } }, x: { grid: { color: '#2d3748' }, ticks: { color: '#e2e8f0' } } } }
            });
        }
        
        function connectWebSocket() {
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${location.host}/ws`);
            ws.onmessage = (event) => { const data = JSON.parse(event.data); updateDashboard(data); };
            ws.onclose = () => setTimeout(connectWebSocket, 3000);
        }
        
        function updateDashboard(data) {
            document.getElementById('balance').innerHTML = `$${(data.account_balance || 10000).toLocaleString()}`;
            document.getElementById('winRate').innerHTML = `${data.win_rate || 0}%`;
            const pnl = data.total_profit || 0;
            const pnlElem = document.getElementById('pnl');
            pnlElem.innerHTML = `$${pnl.toFixed(2)}`;
            pnlElem.style.color = pnl >= 0 ? '#10b981' : '#ef4444';
            document.getElementById('activeTrades').innerHTML = data.active_trades || 0;
            document.getElementById('totalTrades').innerHTML = data.total_trades || 0;
            
            if (data.market_data) {
                const container = document.getElementById('marketList');
                container.innerHTML = '';
                for (const [symbol, info] of Object.entries(data.market_data)) {
                    if (info.price > 0) {
                        const changeClass = info.change_pct >= 0 ? 'positive' : 'negative';
                        container.innerHTML += `<div class="market-item"><div>${symbol}</div><div class="market-price">$${info.price.toFixed(4)}</div><div class="${changeClass}">${info.change_pct >= 0 ? '+' : ''}${info.change_pct.toFixed(2)}%</div></div>`;
                    }
                }
            }
            
            if (data.active_trades_list && data.active_trades_list.length > 0) {
                const container = document.getElementById('activeTradesList');
                container.innerHTML = '';
                for (const trade of data.active_trades_list) {
                    container.innerHTML += `<div class="trade-item"><div><strong>${trade.symbol}</strong> - ${trade.direction}</div><div>Amount: $${trade.amount}</div><div>Entry: $${trade.entry_price?.toFixed(4)}</div></div>`;
                }
            }
            
            if (data.market_data?.R_100?.price > 0) {
                const price = data.market_data.R_100.price;
                const time = new Date().toLocaleTimeString();
                chartData.labels.push(time);
                chartData.prices.push(price);
                if (chartData.labels.length > 50) { chartData.labels.shift(); chartData.prices.shift(); }
                if (chart) { chart.data.labels = chartData.labels; chart.data.datasets[0].data = chartData.prices; chart.update(); }
            }
        }
        
        function manualTrade(direction) {
            const amount = parseFloat(document.getElementById('amount').value);
            const duration = parseInt(document.getElementById('duration').value);
            fetch('/api/manual_trade', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ direction, amount, duration, symbol: 'R_100' })
            }).then(res => res.json()).then(data => { if (data.success) alert(`Trade executed: ${direction} for $${amount}`); else alert('Trade failed'); });
        }
        
        initChart();
        connectWebSocket();
        setInterval(() => { fetch('/api/status').then(res => res.json()).then(data => updateDashboard(data)); }, 2000);
    </script>
</body>
</html>
"""

@app.get("/")
async def root():
    return HTMLResponse(HTML_DASHBOARD)

@app.get("/api/status")
async def get_status():
    return JSONResponse(bot.get_full_state())

@app.post("/api/manual_trade")
async def manual_trade(request: Request):
    try:
        data = await request.json()
        await bot.execute_trade(data.get("symbol", "R_100"), data.get("direction"), 100, "Manual trade")
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(bot.get_full_state())
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass

@app.get("/health")
async def health():
    return JSONResponse({"status": "healthy", "timestamp": datetime.now().isoformat()})

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)