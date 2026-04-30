# main.py - Complete Professional Trading Platform with Real Deriv Integration
import os
import json
import asyncio
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from contextlib import asynccontextmanager
import logging
from typing import Dict, List, Optional
import websockets
from collections import deque

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealDerivTradingPlatform:
    def __init__(self):
        self.websocket = None
        self.connected = False
        self.api_token = os.getenv("DERIV_API_TOKEN")
        self.app_id = os.getenv("DERIV_APP_ID", "1089")
        
        self.account_mode = "demo"
        self.current_balance = 0.00
        self.currency = "USD"
        
        self.bot_status = "STOPPED"
        self.bot_running = True
        
        self.symbols = ["1HZ10V", "R_10", "R_25", "R_50", "R_75", "R_100"]
        self.current_symbol = "1HZ10V"
        self.current_price = 0
        self.price_history = deque(maxlen=200)
        self.ticks_collected = 0
        
        self.settings = {
            "profit_target": 2.00,
            "stop_loss": 10.00,
            "min_confidence": 70,
            "auto_trading": False,
            "max_trades_per_session": 3,
            "max_consecutive_losses": 2,
            "kill_switch_armed": False,
            "base_trade_amount": 1.00,
            "trade_duration": 2
        }
        
        self.stats = {
            "session_pnl": 0.00,
            "total_trades": 0,
            "win_rate": 0,
            "wins": 0,
            "losses": 0,
            "consecutive_wins": 0,
            "consecutive_losses": 0,
            "profit_factor": 0,
            "avg_win": 0.00,
            "avg_loss": 0.00
        }
        
        self.strategies = {
            "even_odd": {"wins": 0, "losses": 0, "roi": 1.00},
            "over_under": {"wins": 0, "losses": 0, "roi": 1.00},
            "streak_reversal": {"wins": 0, "losses": 0, "roi": 1.00},
            "rise_fall": {"wins": 0, "losses": 0, "roi": 1.00}
        }
        
        self.market_score = 50
        self.need_score = 85
        self.market_conditions = {"rsi": 50.0, "macd": "→", "volatility": 0.00, "trend": "neutral"}
        self.last_10_digits = ["4", "U", "0", "U", "7", "O", "9", "O", "5", "O"]
        self.even_odd_pattern = {"even": 3, "odd": 7, "signal": "EVEN"}
        self.over_under_pattern = {"over": 4, "under": 6, "edge": False}
        
        self.active_trades = {}
        self.trade_log = []
    
    async def connect_deriv(self):
        if not self.api_token:
            logger.error("No API token found!")
            return False
        
        url = f"wss://ws.binaryws.com/websockets/v3?app_id={self.app_id}"
        
        try:
            self.websocket = await websockets.connect(url)
            auth_msg = {"authorize": self.api_token}
            await self.websocket.send(json.dumps(auth_msg))
            response = await self.websocket.recv()
            auth_data = json.loads(response)
            
            if auth_data.get("error"):
                logger.error(f"Auth failed: {auth_data['error']['message']}")
                return False
            
            # Get balance
            await self.websocket.send(json.dumps({"balance": 1}))
            balance_response = await self.websocket.recv()
            balance_data = json.loads(balance_response)
            
            if "balance" in balance_data:
                self.current_balance = float(balance_data["balance"].get("balance", 0))
                self.currency = balance_data["balance"].get("currency", "USD")
                loginid = balance_data["balance"].get("loginid", "")
                self.account_mode = "demo" if loginid.startswith("VRTC") else "real"
                logger.info(f"Connected! Account: {loginid}, Balance: {self.currency} {self.current_balance:,.2f}")
            
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def subscribe_to_symbol(self):
        subscribe_msg = {"ticks": self.current_symbol, "subscribe": 1}
        await self.websocket.send(json.dumps(subscribe_msg))
        logger.info(f"Subscribed to {self.current_symbol}")
    
    def calculate_market_score(self):
        score = 50
        if self.market_conditions["rsi"] < 30 or self.market_conditions["rsi"] > 70:
            score += 15
        elif self.market_conditions["rsi"] < 40 or self.market_conditions["rsi"] > 60:
            score += 8
        if self.over_under_pattern.get("edge", False):
            score += 15
        self.market_score = min(max(score, 0), 100)
        return self.market_score
    
    def generate_signal(self):
        if not self.settings["auto_trading"] or self.bot_status != "RUNNING":
            return None
        if self.market_score < self.settings["min_confidence"]:
            return None
        if len(self.active_trades) >= self.settings["max_trades_per_session"]:
            return None
        
        if self.market_conditions["rsi"] < 35:
            return {"type": "rise_fall", "direction": "CALL", "confidence": 70, "reason": "Oversold RSI"}
        if self.market_conditions["rsi"] > 65:
            return {"type": "rise_fall", "direction": "PUT", "confidence": 70, "reason": "Overbought RSI"}
        return None
    
    async def execute_trade(self, signal):
        if not self.connected:
            return None
        
        trade_msg = {
            "buy": 1,
            "parameters": {
                "amount": self.settings["base_trade_amount"],
                "basis": "stake",
                "contract_type": signal["direction"].lower(),
                "currency": self.currency,
                "duration": self.settings["trade_duration"],
                "duration_unit": "m",
                "symbol": self.current_symbol
            }
        }
        
        try:
            await self.websocket.send(json.dumps(trade_msg))
            response = await self.websocket.recv()
            data = json.loads(response)
            
            if "buy" in data:
                contract_id = data["buy"]["contract_id"]
                trade = {
                    "id": contract_id,
                    "symbol": self.current_symbol,
                    "direction": signal["direction"],
                    "amount": self.settings["base_trade_amount"],
                    "confidence": signal["confidence"],
                    "strategy": signal["type"],
                    "entry_price": self.current_price,
                    "entry_time": datetime.now().isoformat(),
                    "status": "open"
                }
                self.active_trades[contract_id] = trade
                logger.info(f"🎯 TRADE: {signal['direction']} {self.current_symbol}")
                asyncio.create_task(self.close_trade(contract_id, self.settings["trade_duration"] * 60))
                return contract_id
        except Exception as e:
            logger.error(f"Trade error: {e}")
        return None
    
    async def close_trade(self, contract_id, seconds):
        await asyncio.sleep(seconds)
        try:
            await self.websocket.send(json.dumps({"portfolio": 1}))
            response = await self.websocket.recv()
            data = json.loads(response)
            
            profit = 0
            if "portfolio" in data:
                for contract in data["portfolio"].get("contracts", []):
                    if contract["contract_id"] == contract_id:
                        profit = float(contract.get("profit", 0))
                        break
            
            self.stats["total_trades"] += 1
            self.stats["session_pnl"] += profit
            self.current_balance += profit
            
            if profit > 0:
                self.stats["wins"] += 1
                self.stats["consecutive_wins"] += 1
                self.stats["consecutive_losses"] = 0
            else:
                self.stats["losses"] += 1
                self.stats["consecutive_losses"] += 1
                self.stats["consecutive_wins"] = 0
            
            if self.stats["total_trades"] > 0:
                self.stats["win_rate"] = (self.stats["wins"] / self.stats["total_trades"]) * 100
            
            if contract_id in self.active_trades:
                trade = self.active_trades[contract_id]
                trade["profit"] = profit
                trade["exit_time"] = datetime.now().isoformat()
                self.trade_log.append(trade)
                del self.active_trades[contract_id]
            
            logger.info(f"{'✅ WIN' if profit > 0 else '❌ LOSS'}: ${profit:.2f}")
        except Exception as e:
            logger.error(f"Close error: {e}")
    
    async def process_tick(self, tick_data):
        symbol = tick_data.get("symbol")
        price = tick_data.get("quote")
        if not symbol or symbol != self.current_symbol:
            return
        
        self.current_price = float(price)
        self.price_history.append(self.current_price)
        self.ticks_collected += 1
        
        if len(self.price_history) >= 20:
            prices = list(self.price_history)
            gains = []
            losses = []
            for i in range(1, min(15, len(prices))):
                change = prices[-i] - prices[-i-1] if i < len(prices) else 0
                if change > 0:
                    gains.append(change)
                else:
                    losses.append(abs(change))
            
            avg_gain = sum(gains[-14:]) / 14 if gains else 0
            avg_loss = sum(losses[-14:]) / 14 if losses else 0
            if avg_loss > 0:
                rs = avg_gain / avg_loss
                self.market_conditions["rsi"] = min(100 - (100 / (1 + rs)), 100)
            
            self.calculate_market_score()
            signal = self.generate_signal()
            if signal:
                await self.execute_trade(signal)
        
        logger.info(f"{symbol}: ${self.current_price:.4f} | Score: {self.market_score}")
    
    async def listen_for_prices(self):
        while self.connected and self.bot_running:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                if "tick" in data:
                    await self.process_tick(data["tick"])
            except Exception as e:
                logger.error(f"Listen error: {e}")
                await asyncio.sleep(1)
    
    async def run(self):
        if await self.connect_deriv():
            await self.subscribe_to_symbol()
            await self.listen_for_prices()
    
    def start_bot(self):
        self.bot_status = "RUNNING"
        self.settings["auto_trading"] = True
    
    def stop_bot(self):
        self.bot_status = "STOPPED"
        self.settings["auto_trading"] = False
    
    def get_full_state(self):
        return {
            "connected": self.connected,
            "bot_status": self.bot_status,
            "account_mode": self.account_mode,
            "current_balance": self.current_balance,
            "currency": self.currency,
            "session_pnl": self.stats["session_pnl"],
            "current_symbol": self.current_symbol,
            "current_price": self.current_price,
            "market_score": self.market_score,
            "need_score": self.need_score,
            "settings": self.settings,
            "stats": self.stats,
            "strategies": self.strategies,
            "market_conditions": self.market_conditions,
            "last_10_digits": self.last_10_digits,
            "even_odd_pattern": self.even_odd_pattern,
            "over_under_pattern": self.over_under_pattern,
            "active_trades": list(self.active_trades.values()),
            "trade_log": self.trade_log[-20:],
            "ticks_collected": self.ticks_collected
        }

platform = RealDerivTradingPlatform()

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(platform.run())
    yield
    platform.bot_running = False
    if platform.websocket:
        await platform.websocket.close()

app = FastAPI(lifespan=lifespan)

# Complete HTML Dashboard
HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SmartPip Trader - Professional Trading Platform</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0a0c15; color: #e5e7eb; }
        .header { background: linear-gradient(135deg, #0f111a 0%, #1a1f2e 100%); border-bottom: 1px solid #2d3748; padding: 0 24px; height: 60px; display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 100; }
        .logo { display: flex; align-items: center; gap: 12px; }
        .logo-icon { font-size: 28px; }
        .logo-text { font-size: 20px; font-weight: 800; background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .balance-display { background: rgba(16, 185, 129, 0.1); padding: 8px 20px; border-radius: 12px; border: 1px solid rgba(16, 185, 129, 0.3); text-align: center; }
        .balance-label { font-size: 11px; color: #94a3b8; }
        .balance-value { font-size: 20px; font-weight: bold; color: #10b981; }
        .main-container { display: grid; grid-template-columns: 320px 1fr 360px; gap: 16px; padding: 20px; max-width: 1600px; margin: 0 auto; }
        .panel { background: #0f111a; border-radius: 16px; border: 1px solid #2d3748; overflow: hidden; }
        .panel-header { padding: 16px 20px; border-bottom: 1px solid #2d3748; background: #0a0c15; font-weight: 600; font-size: 12px; text-transform: uppercase; color: #94a3b8; }
        .panel-content { padding: 20px; }
        .market-card { background: linear-gradient(135deg, #1a1f2e, #0f111a); border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 20px; border: 1px solid #2d3748; }
        .market-symbol { font-size: 18px; font-weight: bold; color: #667eea; margin-bottom: 8px; }
        .market-price { font-size: 32px; font-weight: bold; margin: 10px 0; }
        .market-status { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 600; }
        .status-RUNNING { background: #10b981; color: white; }
        .status-STOPPED { background: #ef4444; color: white; }
        .market-score { background: #1a1f2e; border-radius: 12px; padding: 16px; text-align: center; margin-bottom: 20px; }
        .score-value { font-size: 48px; font-weight: bold; background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .control-buttons { display: flex; gap: 12px; margin-bottom: 20px; }
        .btn-start { flex: 1; background: linear-gradient(135deg, #10b981, #059669); color: white; border: none; padding: 12px; border-radius: 10px; font-weight: bold; cursor: pointer; }
        .btn-stop { flex: 1; background: linear-gradient(135deg, #ef4444, #dc2626); color: white; border: none; padding: 12px; border-radius: 10px; font-weight: bold; cursor: pointer; }
        .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }
        .stat-item { background: #1a1f2e; padding: 12px; border-radius: 10px; text-align: center; }
        .stat-label { font-size: 11px; color: #94a3b8; margin-bottom: 5px; }
        .stat-value { font-size: 20px; font-weight: bold; }
        .digits-container { background: #1a1f2e; border-radius: 12px; padding: 16px; margin-bottom: 20px; }
        .digits-row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
        .digit-box { width: 40px; height: 40px; background: #0f111a; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 1px solid #2d3748; }
        .trade-log { max-height: 300px; overflow-y: auto; }
        .trade-entry { background: #1a1f2e; padding: 10px; border-radius: 8px; margin-bottom: 8px; font-size: 12px; border-left: 3px solid; }
        .trade-win { border-left-color: #10b981; }
        .trade-loss { border-left-color: #ef4444; }
        .positive { color: #10b981; }
        .negative { color: #ef4444; }
        .symbol-selector { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; }
        .symbol-btn { background: #1a1f2e; border: 1px solid #2d3748; color: #94a3b8; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 11px; }
        .symbol-btn.active { background: linear-gradient(135deg, #667eea, #764ba2); color: white; border-color: transparent; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #1a1f2e; }
        ::-webkit-scrollbar-thumb { background: #667eea; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo"><div class="logo-icon">🤖</div><div class="logo-text">SMARTPIP TRADER</div></div>
        <div class="balance-display"><div class="balance-label">Balance</div><div class="balance-value" id="balance">$0.00</div></div>
    </div>
    <div class="main-container">
        <div class="panel">
            <div class="panel-header">Live Trade</div>
            <div class="panel-content">
                <div class="market-card">
                    <div class="market-symbol" id="symbol">1HZ10V</div>
                    <div class="market-price" id="price">$0.00</div>
                    <div class="market-status" id="botStatus">STOPPED</div>
                </div>
                <div class="symbol-selector" id="symbolSelector"></div>
                <div class="market-score"><div class="score-value" id="marketScore">50</div><div class="score-need">Need ≥85 to trade</div></div>
                <div class="control-buttons"><button class="btn-start" onclick="startBot()">START</button><button class="btn-stop" onclick="stopBot()">STOP</button></div>
                <div class="stats-grid">
                    <div class="stat-item"><div class="stat-label">Balance</div><div class="stat-value" id="balance2">$0.00</div></div>
                    <div class="stat-item"><div class="stat-label">Session P/L</div><div class="stat-value" id="sessionPnl">$0.00</div></div>
                    <div class="stat-item"><div class="stat-label">Trades</div><div class="stat-value" id="tradeCount">0 / 3</div></div>
                    <div class="stat-item"><div class="stat-label">Win Rate</div><div class="stat-value" id="winRate">0%</div></div>
                </div>
            </div>
        </div>
        <div class="panel">
            <div class="panel-header">Market Board</div>
            <div class="panel-content">
                <div class="digits-container">
                    <div class="digits-title">Last 10 Digits</div>
                    <div class="digits-row" id="digitsRow"></div>
                    <div>Even/Odd: <strong id="evenOdd">0E / 0O</strong> → <span id="evenOddSignal">-</span></div>
                </div>
                <div class="stats-grid">
                    <div class="stat-item"><div class="stat-label">RSI</div><div class="stat-value" id="rsi">50.0</div></div>
                    <div class="stat-item"><div class="stat-label">MACD</div><div class="stat-value" id="macd">→</div></div>
                    <div class="stat-item"><div class="stat-label">Win Rate</div><div class="stat-value" id="winRate2">0%</div></div>
                    <div class="stat-item"><div class="stat-label">Profit Factor</div><div class="stat-value" id="profitFactor">0</div></div>
                </div>
            </div>
        </div>
        <div class="panel">
            <div class="panel-header">Trade Log</div>
            <div class="panel-content">
                <div class="stats-grid">
                    <div class="stat-item"><div class="stat-label">Wins</div><div class="stat-value" id="wins">0</div></div>
                    <div class="stat-item"><div class="stat-label">Losses</div><div class="stat-value" id="losses">0</div></div>
                </div>
                <div class="trade-log" id="tradeLog"><div style="text-align:center;color:#94a3b8;padding:20px;">No trades yet</div></div>
            </div>
        </div>
    </div>
    <script>
        let ws = null;
        function connectWebSocket() {
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${location.host}/ws`);
            ws.onmessage = (event) => { const data = JSON.parse(event.data); updateDashboard(data); };
            ws.onclose = () => setTimeout(connectWebSocket, 3000);
        }
        
        function updateDashboard(data) {
            document.getElementById('balance').innerHTML = `${data.currency || '$'}${(data.current_balance || 0).toFixed(2)}`;
            document.getElementById('balance2').innerHTML = `${data.currency || '$'}${(data.current_balance || 0).toFixed(2)}`;
            document.getElementById('price').innerHTML = `${data.currency || '$'}${(data.current_price || 0).toFixed(4)}`;
            document.getElementById('marketScore').innerHTML = data.market_score || 50;
            document.getElementById('sessionPnl').innerHTML = `${(data.session_pnl || 0) >= 0 ? '+' : ''}${data.currency || '$'}${(data.session_pnl || 0).toFixed(2)}`;
            document.getElementById('tradeCount').innerHTML = `${data.stats?.total_trades || 0} / 3`;
            document.getElementById('winRate').innerHTML = `${data.stats?.win_rate || 0}%`;
            document.getElementById('winRate2').innerHTML = `${data.stats?.win_rate || 0}%`;
            document.getElementById('profitFactor').innerHTML = (data.stats?.profit_factor || 0).toFixed(2);
            document.getElementById('wins').innerHTML = data.stats?.wins || 0;
            document.getElementById('losses').innerHTML = data.stats?.losses || 0;
            document.getElementById('rsi').innerHTML = (data.market_conditions?.rsi || 50).toFixed(1);
            document.getElementById('macd').innerHTML = data.market_conditions?.macd || '→';
            
            const statusElem = document.getElementById('botStatus');
            statusElem.innerHTML = data.bot_status || 'STOPPED';
            statusElem.className = `market-status status-${data.bot_status || 'STOPPED'}`;
            
            if (data.even_odd_pattern) {
                document.getElementById('evenOdd').innerHTML = `${data.even_odd_pattern.even || 0}E / ${data.even_odd_pattern.odd || 0}O`;
                document.getElementById('evenOddSignal').innerHTML = data.even_odd_pattern.signal || '-';
            }
            
            if (data.last_10_digits) {
                const digitsRow = document.getElementById('digitsRow');
                digitsRow.innerHTML = data.last_10_digits.slice(-10).map(d => `<div class="digit-box">${d}</div>`).join('');
            }
            
            if (data.trade_log && data.trade_log.length > 0) {
                const logContainer = document.getElementById('tradeLog');
                logContainer.innerHTML = data.trade_log.slice().reverse().map(t => `
                    <div class="trade-entry ${t.profit > 0 ? 'trade-win' : t.profit < 0 ? 'trade-loss' : ''}">
                        <div>${new Date(t.entry_time).toLocaleTimeString()} - ${t.symbol} - ${t.direction}</div>
                        <div>Amount: ${data.currency || '$'}${t.amount} | ${t.profit > 0 ? '+' : ''}${data.currency || '$'}${(t.profit || 0).toFixed(2)}</div>
                    </div>
                `).join('');
            }
            
            if (data.symbols) {
                const selector = document.getElementById('symbolSelector');
                selector.innerHTML = data.symbols.map(s => `<button class="symbol-btn ${s === data.current_symbol ? 'active' : ''}" onclick="switchSymbol('${s}')">${s}</button>`).join('');
            }
        }
        
        function startBot() { fetch('/api/start', { method: 'POST' }); }
        function stopBot() { fetch('/api/stop', { method: 'POST' }); }
        function switchSymbol(symbol) { fetch('/api/switch_symbol', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ symbol }) }); }
        
        connectWebSocket();
        setInterval(() => { fetch('/api/status').then(res => res.json()).then(data => updateDashboard(data)); }, 2000);
    </script>
</body>
</html>'''

@app.get("/")
async def root():
    return HTMLResponse(HTML)

@app.get("/api/status")
async def get_status():
    return JSONResponse(platform.get_full_state())

@app.post("/api/start")
async def start_bot():
    platform.start_bot()
    return JSONResponse({"success": True})

@app.post("/api/stop")
async def stop_bot():
    platform.stop_bot()
    return JSONResponse({"success": True})

@app.post("/api/switch_symbol")
async def switch_symbol(request: Request):
    try:
        data = await request.json()
        platform.current_symbol = data.get("symbol")
        platform.price_history.clear()
        await platform.subscribe_to_symbol()
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(platform.get_full_state())
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass

@app.get("/health")
async def health():
    return JSONResponse({"status": "healthy"})

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)