# main.py - Complete Professional Trading Platform
import os
import json
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import logging
from typing import Dict, List, Optional
import websockets
import random
import pandas as pd
import numpy as np
from collections import deque

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Trading Bot Class
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
        self.indicators = {symbol: {} for symbol in self.symbols}
        
        # Initialize market data
        self.market_data = {}
        for symbol in self.symbols:
            self.market_data[symbol] = {
                "price": 0,
                "change": 0,
                "change_pct": 0,
                "high": 0,
                "low": 0,
                "volume": 0,
                "spread": 0,
                "bid": 0,
                "ask": 0,
                "last_update": None
            }
        
        # User settings
        self.settings = {
            "default_amount": float(os.getenv("BASE_TRADE_AMOUNT", 10)),
            "default_duration": int(os.getenv("TRADE_DURATION", 5)),
            "risk_level": "MODERATE",
            "auto_trade": os.getenv("AUTO_TRADE", "true").lower() == "true",
            "notifications": True,
            "dark_mode": True
        }
        
        # Performance metrics
        self.performance = {
            "daily_pnl": 0,
            "weekly_pnl": 0,
            "monthly_pnl": 0,
            "best_trade": 0,
            "worst_trade": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "consecutive_wins": 0,
            "consecutive_losses": 0,
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
                
            # Get account balance
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
        
        # Calculate simple indicators
        if len(self.price_history[symbol]) >= 20:
            prices = list(self.price_history[symbol])
            self.indicators[symbol]["sma_20"] = sum(prices[-20:]) / 20
            self.indicators[symbol]["sma_50"] = sum(prices[-50:]) / 50 if len(prices) >= 50 else self.indicators[symbol]["sma_20"]
            self.indicators[symbol]["volatility"] = np.std(prices[-20:]) if len(prices) >= 20 else 0
        
        logger.info(f"{symbol}: ${price:.4f} ({self.market_data[symbol]['change_pct']:+.2f}%)")
        
        # Auto trading logic
        if self.settings["auto_trade"] and len(self.active_trades) < 3:
            await self.check_auto_trade(symbol, price)
    
    async def check_auto_trade(self, symbol: str, price: float):
        """Enhanced AI trading logic"""
        if symbol not in self.indicators or "sma_20" not in self.indicators[symbol]:
            return
        
        sma = self.indicators[symbol]["sma_20"]
        volatility = self.indicators[symbol].get("volatility", 0)
        
        # Advanced signal generation
        if price > sma * 1.002 and volatility > 0.001:
            confidence = 75 + min(volatility * 1000, 20)
            direction = "CALL"
            reason = "Price above SMA with momentum"
        elif price < sma * 0.998 and volatility > 0.001:
            confidence = 75 + min(volatility * 1000, 20)
            direction = "PUT"
            reason = "Price below SMA with momentum"
        else:
            return
        
        if confidence >= 70:
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
                self.performance["consecutive_wins"] += 1
                self.performance["consecutive_losses"] = 0
                if profit > self.performance["best_trade"]:
                    self.performance["best_trade"] = profit
            else:
                self.loss_count += 1
                self.performance["consecutive_losses"] += 1
                self.performance["consecutive_wins"] = 0
                if profit < self.performance["worst_trade"]:
                    self.performance["worst_trade"] = profit
            
            # Update performance metrics
            self.update_performance_metrics()
            
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
        except Exception as e:
            logger.error(f"Close error: {e}")
    
    def update_performance_metrics(self):
        total_trades = self.win_count + self.loss_count
        if total_trades > 0:
            wins = [t["profit"] for t in self.trades if t.get("profit", 0) > 0]
            losses = [t["profit"] for t in self.trades if t.get("profit", 0) < 0]
            
            self.performance["avg_win"] = sum(wins) / len(wins) if wins else 0
            self.performance["avg_loss"] = sum(losses) / len(losses) if losses else 0
            
            # Calculate drawdown
            if self.equity_curve:
                equities = [e["equity"] for e in self.equity_curve]
                peak = max(equities)
                current = equities[-1]
                drawdown = (peak - current) / peak * 100
                if drawdown > self.performance["max_drawdown"]:
                    self.performance["max_drawdown"] = drawdown
    
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
            except Exception as e:
                logger.error(f"Listen error: {e}")
                await asyncio.sleep(1)
    
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
            "indicators": self.indicators,
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

# Professional Trading Dashboard HTML
PROFESSIONAL_DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SmartPip Pro - Professional Trading Platform</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
            background: #0a0e27;
            color: #e2e8f0;
            overflow-x: hidden;
        }
        
        /* Header */
        .header {
            background: linear-gradient(135deg, #0f1235 0%, #1a1f4e 100%);
            padding: 15px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #2d3748;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .logo-icon {
            font-size: 28px;
        }
        
        .logo-text {
            font-size: 20px;
            font-weight: bold;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .account-info {
            display: flex;
            gap: 20px;
            align-items: center;
        }
        
        .balance-card {
            background: rgba(16, 185, 129, 0.1);
            padding: 8px 16px;
            border-radius: 10px;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }
        
        .balance-label {
            font-size: 12px;
            color: #94a3b8;
        }
        
        .balance-value {
            font-size: 20px;
            font-weight: bold;
            color: #10b981;
        }
        
        .status-badge {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: rgba(16, 185, 129, 0.2);
            border-radius: 20px;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            background: #10b981;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
        
        /* Main Container */
        .container {
            display: grid;
            grid-template-columns: 280px 1fr 320px;
            gap: 20px;
            padding: 20px;
            min-height: calc(100vh - 70px);
        }
        
        /* Left Panel - Market Overview */
        .market-panel {
            background: #0f1235;
            border-radius: 15px;
            padding: 20px;
            border: 1px solid #2d3748;
        }
        
        .panel-title {
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #94a3b8;
            margin-bottom: 20px;
        }
        
        .market-item {
            padding: 12px;
            border-bottom: 1px solid #1e2345;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .market-item:hover {
            background: rgba(102, 126, 234, 0.1);
            border-radius: 8px;
        }
        
        .market-symbol {
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .market-price {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .market-change {
            font-size: 12px;
        }
        
        .positive {
            color: #10b981;
        }
        
        .negative {
            color: #ef4444;
        }
        
        /* Center Panel - Chart & Trading */
        .trading-panel {
            background: #0f1235;
            border-radius: 15px;
            border: 1px solid #2d3748;
            overflow: hidden;
        }
        
        .chart-container {
            padding: 20px;
            height: 400px;
        }
        
        .trading-controls {
            padding: 20px;
            border-top: 1px solid #2d3748;
            background: #0a0e27;
        }
        
        .trade-buttons {
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .btn-call {
            flex: 1;
            background: linear-gradient(135deg, #10b981, #059669);
            color: white;
            border: none;
            padding: 12px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        .btn-put {
            flex: 1;
            background: linear-gradient(135deg, #ef4444, #dc2626);
            color: white;
            border: none;
            padding: 12px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        .btn-call:hover, .btn-put:hover {
            transform: translateY(-2px);
        }
        
        .trade-params {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 15px;
        }
        
        .param-group {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        
        .param-label {
            font-size: 12px;
            color: #94a3b8;
        }
        
        .param-input {
            background: #1a1f4e;
            border: 1px solid #2d3748;
            color: white;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 14px;
        }
        
        .auto-trade-switch {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            background: #1a1f4e;
            border-radius: 8px;
            margin-top: 10px;
        }
        
        .switch {
            position: relative;
            display: inline-block;
            width: 50px;
            height: 24px;
        }
        
        .switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }
        
        .slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #4a5568;
            transition: 0.4s;
            border-radius: 24px;
        }
        
        .slider:before {
            position: absolute;
            content: "";
            height: 18px;
            width: 18px;
            left: 3px;
            bottom: 3px;
            background-color: white;
            transition: 0.4s;
            border-radius: 50%;
        }
        
        input:checked + .slider {
            background-color: #667eea;
        }
        
        input:checked + .slider:before {
            transform: translateX(26px);
        }
        
        /* Right Panel - Portfolio & Trades */
        .portfolio-panel {
            background: #0f1235;
            border-radius: 15px;
            padding: 20px;
            border: 1px solid #2d3748;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .stat-card {
            background: #1a1f4e;
            padding: 12px;
            border-radius: 10px;
            text-align: center;
        }
        
        .stat-label {
            font-size: 11px;
            color: #94a3b8;
            margin-bottom: 5px;
        }
        
        .stat-value {
            font-size: 20px;
            font-weight: bold;
        }
        
        .active-trades {
            max-height: 250px;
            overflow-y: auto;
        }
        
        .trade-item {
            background: #1a1f4e;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 10px;
        }
        
        .trade-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
        }
        
        .trade-symbol {
            font-weight: bold;
        }
        
        .trade-direction {
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
        }
        
        .trade-call {
            background: rgba(16, 185, 129, 0.2);
            color: #10b981;
        }
        
        .trade-put {
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
        }
        
        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        
        ::-webkit-scrollbar-track {
            background: #1a1f4e;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #667eea;
            border-radius: 3px;
        }
        
        /* Responsive */
        @media (max-width: 1200px) {
            .container {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">
            <div class="logo-icon">🤖</div>
            <div class="logo-text">SmartPip Pro Trading Platform</div>
        </div>
        <div class="account-info">
            <div class="balance-card">
                <div class="balance-label">Account Balance</div>
                <div class="balance-value" id="balance">$10,000</div>
            </div>
            <div class="status-badge">
                <div class="status-dot"></div>
                <span id="status-text">Live Trading</span>
            </div>
        </div>
    </div>
    
    <div class="container">
        <!-- Left Panel - Market Overview -->
        <div class="market-panel">
            <div class="panel-title">📊 Market Overview</div>
            <div id="market-list"></div>
        </div>
        
        <!-- Center Panel - Chart & Trading -->
        <div class="trading-panel">
            <div class="chart-container">
                <canvas id="priceChart"></canvas>
            </div>
            <div class="trading-controls">
                <div class="trade-buttons">
                    <button class="btn-call" onclick="manualTrade('CALL')">📈 CALL</button>
                    <button class="btn-put" onclick="manualTrade('PUT')">📉 PUT</button>
                </div>
                <div class="trade-params">
                    <div class="param-group">
                        <div class="param-label">Amount ($)</div>
                        <input type="number" id="tradeAmount" class="param-input" value="10">
                    </div>
                    <div class="param-group">
                        <div class="param-label">Duration (minutes)</div>
                        <input type="number" id="tradeDuration" class="param-input" value="5">
                    </div>
                </div>
                <div class="auto-trade-switch">
                    <span>🤖 AI Auto-Trading</span>
                    <label class="switch">
                        <input type="checkbox" id="autoTrade" checked>
                        <span class="slider"></span>
                    </label>
                </div>
            </div>
        </div>
        
        <!-- Right Panel - Portfolio -->
        <div class="portfolio-panel">
            <div class="panel-title">💰 Portfolio & Stats</div>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Win Rate</div>
                    <div class="stat-value" id="winRate">0%</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Total P&L</div>
                    <div class="stat-value" id="totalPnl" style="color: #10b981;">$0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Active Trades</div>
                    <div class="stat-value" id="activeTrades">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Total Trades</div>
                    <div class="stat-value" id="totalTrades">0</div>
                </div>
            </div>
            
            <div class="panel-title" style="margin-top: 20px;">📋 Active Positions</div>
            <div class="active-trades" id="activeTradesList">
                <div style="text-align: center; color: #94a3b8;">No active trades</div>
            </div>
            
            <div class="panel-title" style="margin-top: 20px;">📈 Performance</div>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Best Trade</div>
                    <div class="stat-value" id="bestTrade">$0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Max Drawdown</div>
                    <div class="stat-value" id="maxDrawdown">0%</div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let ws = null;
        let priceChart = null;
        let chartData = {
            labels: [],
            prices: []
        };
        
        // Initialize Chart
        function initChart() {
            const ctx = document.getElementById('priceChart').getContext('2d');
            priceChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'R_100 Price',
                        data: [],
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            labels: { color: '#e2e8f0' }
                        }
                    },
                    scales: {
                        y: {
                            grid: { color: '#2d3748' },
                            ticks: { color: '#e2e8f0' }
                        },
                        x: {
                            grid: { color: '#2d3748' },
                            ticks: { color: '#e2e8f0' }
                        }
                    }
                }
            });
        }
        
        // Connect WebSocket
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            
            ws.onclose = function() {
                setTimeout(connectWebSocket, 3000);
            };
        }
        
        // Update Dashboard
        function updateDashboard(data) {
            // Update balance
            if (data.account_balance) {
                document.getElementById('balance').innerHTML = `$${data.account_balance.toLocaleString()}`;
            }
            
            // Update stats
            document.getElementById('winRate').innerHTML = `${data.win_rate || 0}%`;
            const pnlElem = document.getElementById('totalPnl');
            const pnl = data.total_profit || 0;
            pnlElem.innerHTML = `$${pnl.toFixed(2)}`;
            pnlElem.style.color = pnl >= 0 ? '#10b981' : '#ef4444';
            document.getElementById('activeTrades').innerHTML = data.active_trades || 0;
            document.getElementById('totalTrades').innerHTML = data.total_trades || 0;
            
            // Update performance
            if (data.performance) {
                document.getElementById('bestTrade').innerHTML = `$${data.performance.best_trade?.toFixed(2) || 0}`;
                document.getElementById('maxDrawdown').innerHTML = `${data.performance.max_drawdown?.toFixed(1) || 0}%`;
            }
            
            // Update market list
            if (data.market_data) {
                updateMarketList(data.market_data);
            }
            
            // Update active trades
            if (data.active_trades_list) {
                updateActiveTrades(data.active_trades_list);
            }
            
            // Update chart with latest price
            if (data.market_data && data.market_data.R_100) {
                const price = data.market_data.R_100.price;
                const time = new Date().toLocaleTimeString();
                
                chartData.labels.push(time);
                chartData.prices.push(price);
                
                if (chartData.labels.length > 50) {
                    chartData.labels.shift();
                    chartData.prices.shift();
                }
                
                if (priceChart) {
                    priceChart.data.labels = chartData.labels;
                    priceChart.data.datasets[0].data = chartData.prices;
                    priceChart.update();
                }
            }
        }
        
        function updateMarketList(marketData) {
            const container = document.getElementById('market-list');
            container.innerHTML = '';
            
            const symbols = ['R_10', 'R_25', 'R_50', 'R_75', 'R_100'];
            for (const symbol of symbols) {
                const data = marketData[symbol];
                if (data && data.price > 0) {
                    const changeClass = data.change_pct >= 0 ? 'positive' : 'negative';
                    const changeSign = data.change_pct >= 0 ? '+' : '';
                    
                    const item = document.createElement('div');
                    item.className = 'market-item';
                    item.innerHTML = `
                        <div class="market-symbol">${symbol}</div>
                        <div class="market-price">$${data.price.toFixed(4)}</div>
                        <div class="market-change ${changeClass}">${changeSign}${data.change_pct.toFixed(2)}%</div>
                    `;
                    container.appendChild(item);
                }
            }
        }
        
        function updateActiveTrades(trades) {
            const container = document.getElementById('activeTradesList');
            if (!trades || trades.length === 0) {
                container.innerHTML = '<div style="text-align: center; color: #94a3b8;">No active trades</div>';
                return;
            }
            
            container.innerHTML = '';
            for (const trade of trades) {
                const tradeDiv = document.createElement('div');
                tradeDiv.className = 'trade-item';
                tradeDiv.innerHTML = `
                    <div class="trade-header">
                        <span class="trade-symbol">${trade.symbol}</span>
                        <span class="trade-direction trade-${trade.direction.toLowerCase()}">${trade.direction}</span>
                    </div>
                    <div>Amount: $${trade.amount}</div>
                    <div>Entry: $${trade.entry_price?.toFixed(4)}</div>
                    <div>Confidence: ${trade.confidence?.toFixed(0)}%</div>
                `;
                container.appendChild(tradeDiv);
            }
        }
        
        function manualTrade(direction) {
            const amount = document.getElementById('tradeAmount').value;
            const duration = document.getElementById('tradeDuration').value;
            
            fetch('/api/manual_trade', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    direction: direction,
                    amount: parseFloat(amount),
                    duration: parseInt(duration),
                    symbol: 'R_100'
                })
            }).then(response => response.json())
              .then(data => {
                  if (data.success) {
                      alert(`Trade executed: ${direction} for $${amount}`);
                  } else {
                      alert('Trade failed: ' + data.error);
                  }
              });
        }
        
        // Auto-trade toggle
        document.getElementById('autoTrade').addEventListener('change', function(e) {
            fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ auto_trade: e.target.checked })
            });
        });
        
        // Initialize
        initChart();
        connectWebSocket();
        
        // Refresh data every 2 seconds
        setInterval(() => {
            fetch('/api/status')
                .then(res => res.json())
                .then(data => updateDashboard(data));
        }, 2000);
    </script>
</body>
</html>
"""

# API Endpoints
@app.get("/")
async def root():
    return HTMLResponse(PROFESSIONAL_DASHBOARD)

@app.get("/api/status")
async def get_status():
    return JSONResponse(bot.get_full_state())

@app.get("/api/trades")
async def get_trades():
    return JSONResponse(bot.trades[-100:])

@app.post("/api/manual_trade")
async def manual_trade(request: Request):
    try:
        data = await request.json()
        direction = data.get("direction")
        amount = data.get("amount")
        duration = data.get("duration")
        symbol = data.get("symbol", "R_100")
        
        # Execute manual trade
        await bot.execute_trade(symbol, direction, 100, "Manual trade")
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.post("/api/settings")
async def update_settings(request: Request):
    try:
        data = await request.json()
        if "auto_trade" in data:
            bot.settings["auto_trade"] = data["auto_trade"]
        if "default_amount" in data:
            bot.settings["default_amount"] = data["default_amount"]
        if "default_duration" in data:
            bot.settings["default_duration"] = data["default_duration"]
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            state = bot.get_full_state()
            await websocket.send_json(state)
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