# main.py - Complete Professional Trading Platform
import os
import json
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from contextlib import asynccontextmanager
import logging
from typing import Dict, List, Optional
import websockets
import random
import hashlib
from collections import deque
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProfessionalTradingPlatform:
    def __init__(self):
        # Connection status
        self.connected = False
        self.websocket = None
        self.active_account = "demo"  # demo or real
        self.bot_status = "STOPPED"  # RUNNING, STOPPED, IDLE
        
        # Account data
        self.demo_accounts = {
            "VRTC14297314": {
                "balance": 10075.32,
                "initial_balance": 10000.00,
                "pnl": 75.32,
                "phase": "stable",
                "type": "demo"
            }
        }
        self.real_accounts = {
            "REAL12345678": {
                "balance": 5000.00,
                "initial_balance": 5000.00,
                "pnl": 0.00,
                "phase": "stable",
                "type": "real"
            }
        }
        self.current_account = "VRTC14297314"
        self.current_balance = 10075.32
        self.initial_balance = 10000.00
        
        # Trading symbols
        self.symbols = ["1HZ10V", "R_10", "R_25", "R_50", "R_75", "R_100"]
        self.current_symbol = "1HZ10V"
        self.current_price = 10179.83000
        self.price_history = deque(maxlen=200)
        self.ticks_collected = 0
        
        # Trading settings
        self.settings = {
            "target": 2.00,
            "stop_loss": 10.00,
            "min_confidence": 70,
            "auto_trading": False,
            "session_target": 2.00,
            "daily_target_percent": 3,
            "max_consecutive_losses": 2,
            "max_trades_per_session": 3,
            "kill_switch_armed": False,
            "risk_level": "MODERATE"
        }
        
        # Trading statistics
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
            "avg_loss": 0.00,
            "max_drawdown": 0.00,
            "best_trade": 0.00,
            "worst_trade": 0.00
        }
        
        # Strategy performance
        self.strategies = {
            "even_odd": {"wins": 0, "losses": 0, "roi": 1.00},
            "over_under": {"wins": 0, "losses": 0, "roi": 1.00},
            "streak_reversal": {"wins": 0, "losses": 0, "roi": 1.00},
            "rise_fall": {"wins": 0, "losses": 0, "roi": 1.00}
        }
        
        # Market analysis
        self.market_score = 50
        self.need_score = 85
        self.market_conditions = {
            "rsi": 63.5,
            "macd": "↑",
            "volatility": 0.00,
            "trend": "neutral"
        }
        
        # Pattern analysis for digits
        self.last_10_digits = ["4", "U", "0", "U", "7", "O", "9", "O", "5", "O", "1", "U", "5", "O", "3", "U", "2", "U", "3", "U"]
        self.even_odd_pattern = {"even": 3, "odd": 7, "signal": "EVEN"}
        self.over_under_pattern = {"over": 4, "under": 6, "edge": False}
        
        # Active trades
        self.active_trades = {}
        self.trade_log = []
        self.last_10_trades = []
        
        # Signal history
        self.signals = []
        self.active_signals = []
        
        # Market score calculation
        self.market_factors = {
            "trend_strength": 0,
            "volatility": 0,
            "momentum": 0,
            "volume": 0,
            "pattern_match": 0
        }
        
    async def connect_deriv(self):
        """Connect to Deriv WebSocket"""
        api_token = os.getenv("DERIV_API_TOKEN")
        app_id = os.getenv("DERIV_APP_ID", "1089")
        
        if not api_token:
            logger.error("No API token found!")
            return False
            
        url = f"wss://ws.binaryws.com/websockets/v3?app_id={app_id}"
        
        try:
            self.websocket = await websockets.connect(url)
            await self.websocket.send(json.dumps({"authorize": api_token}))
            response = await self.websocket.recv()
            data = json.loads(response)
            
            if data.get("error"):
                logger.error(f"Auth failed: {data['error']['message']}")
                return False
            
            # Get real balance if using real account
            if self.active_account == "real":
                await self.websocket.send(json.dumps({"balance": 1}))
                balance_response = await self.websocket.recv()
                balance_data = json.loads(balance_response)
                if "balance" in balance_data:
                    self.current_balance = balance_data["balance"]["balance"]
                    self.real_accounts["REAL12345678"]["balance"] = self.current_balance
            
            self.connected = True
            logger.info(f"Connected to Deriv with {self.active_account} account")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def subscribe_to_symbol(self):
        """Subscribe to current symbol"""
        subscribe_msg = {
            "ticks": self.current_symbol,
            "subscribe": 1
        }
        await self.websocket.send(json.dumps(subscribe_msg))
        logger.info(f"Subscribed to {self.current_symbol}")
    
    def calculate_market_score(self):
        """Calculate comprehensive market score"""
        score = 50
        
        # RSI factor
        if self.market_conditions["rsi"] < 30 or self.market_conditions["rsi"] > 70:
            score += 15
        elif self.market_conditions["rsi"] < 40 or self.market_conditions["rsi"] > 60:
            score += 8
        
        # MACD factor
        if self.market_conditions["macd"] == "↑":
            score += 10
        
        # Volatility factor
        if 0.001 < self.market_conditions["volatility"] < 0.005:
            score += 10
        
        # Pattern factor
        pattern_score = self.analyze_pattern_strength()
        score += pattern_score
        
        # Trend strength
        score += self.market_factors["trend_strength"]
        
        self.market_score = min(max(score, 0), 100)
        return self.market_score
    
    def analyze_pattern_strength(self):
        """Analyze pattern strength for trading edge"""
        # Check last 10 digits pattern
        if len(self.last_10_digits) >= 10:
            same_type_count = sum(1 for d in self.last_10_digits[-10:] if d in ["U", "O"])
            if same_type_count >= 7:
                return 20
            elif same_type_count >= 6:
                return 10
        return 5
    
    def generate_signal(self):
        """Generate trading signal based on analysis"""
        if self.bot_status != "RUNNING" or not self.settings["auto_trading"]:
            return None
        
        # Check if market score meets threshold
        if self.market_score < self.settings["min_confidence"]:
            return None
        
        # Check trade limits
        if len(self.active_trades) >= self.settings["max_trades_per_session"]:
            return None
        
        # Check consecutive losses limit
        if self.stats["consecutive_losses"] >= self.settings["max_consecutive_losses"]:
            return None
        
        # Check stop loss
        if self.stats["session_pnl"] <= -self.settings["stop_loss"]:
            self.stop_bot("Stop loss hit")
            return None
        
        # Check profit target
        if self.stats["session_pnl"] >= self.settings["session_target"]:
            self.stop_bot("Profit target achieved")
            return None
        
        # Generate signal based on patterns
        if self.even_odd_pattern["signal"] == "EVEN" and self.even_odd_pattern["odd"] >= 7:
            return {
                "type": "even_odd",
                "direction": "CALL" if self.even_odd_pattern["even"] > self.even_odd_pattern["odd"] else "PUT",
                "confidence": min(70 + (self.market_score - 50), 95),
                "reason": "Strong even/odd edge detected"
            }
        
        if self.over_under_pattern.get("edge", False):
            return {
                "type": "over_under",
                "direction": "CALL" if self.over_under_pattern["over"] > self.over_under_pattern["under"] else "PUT",
                "confidence": 75,
                "reason": "Over/under edge detected"
            }
        
        # Technical signal
        if self.market_conditions["rsi"] < 35:
            return {
                "type": "rise_fall",
                "direction": "CALL",
                "confidence": 70 + (35 - self.market_conditions["rsi"]) / 2,
                "reason": "Oversold RSI"
            }
        
        if self.market_conditions["rsi"] > 65:
            return {
                "type": "rise_fall",
                "direction": "PUT",
                "confidence": 70 + (self.market_conditions["rsi"] - 65) / 2,
                "reason": "Overbought RSI"
            }
        
        return None
    
    async def execute_trade(self, signal: Dict):
        """Execute trade based on signal"""
        if not self.connected:
            return None
        
        amount = 1.0  # Base amount
        duration = 2  # 2 minutes
        
        trade_msg = {
            "buy": 1,
            "parameters": {
                "amount": amount,
                "basis": "stake",
                "contract_type": signal["direction"].lower(),
                "currency": "USD",
                "duration": duration,
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
                    "amount": amount,
                    "confidence": signal["confidence"],
                    "strategy": signal["type"],
                    "entry_price": self.current_price,
                    "entry_time": datetime.now().isoformat(),
                    "status": "open"
                }
                self.active_trades[contract_id] = trade
                self.trade_log.append(trade)
                
                logger.info(f"🎯 TRADE EXECUTED: {signal['direction']} {self.current_symbol} | Confidence: {signal['confidence']:.0f}%")
                
                # Auto-close after duration
                asyncio.create_task(self.close_trade(contract_id, duration * 60, signal))
                return contract_id
        except Exception as e:
            logger.error(f"Trade error: {e}")
        
        return None
    
    async def close_trade(self, contract_id: int, seconds: int, signal: Dict):
        """Close trade and record result"""
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
            
            # Update statistics
            self.stats["total_trades"] += 1
            self.stats["session_pnl"] += profit
            
            if profit > 0:
                self.stats["wins"] += 1
                self.stats["consecutive_wins"] += 1
                self.stats["consecutive_losses"] = 0
                if profit > self.stats["best_trade"]:
                    self.stats["best_trade"] = profit
                
                # Update strategy performance
                if signal["type"] in self.strategies:
                    self.strategies[signal["type"]]["wins"] += 1
            else:
                self.stats["losses"] += 1
                self.stats["consecutive_losses"] += 1
                self.stats["consecutive_wins"] = 0
                if profit < self.stats["worst_trade"]:
                    self.stats["worst_trade"] = profit
                
                # Update strategy performance
                if signal["type"] in self.strategies:
                    self.strategies[signal["type"]]["losses"] += 1
            
            # Update win rate
            if self.stats["total_trades"] > 0:
                self.stats["win_rate"] = (self.stats["wins"] / self.stats["total_trades"]) * 100
            
            # Update balance
            self.current_balance += profit
            self.stats["session_pnl"] += profit
            
            # Update profit factor
            total_wins = sum(t.get("profit", 0) for t in self.trade_log if t.get("profit", 0) > 0)
            total_losses = abs(sum(t.get("profit", 0) for t in self.trade_log if t.get("profit", 0) < 0))
            self.stats["profit_factor"] = total_wins / total_losses if total_losses > 0 else 0
            
            # Update average win/loss
            wins_list = [t.get("profit", 0) for t in self.trade_log if t.get("profit", 0) > 0]
            losses_list = [t.get("profit", 0) for t in self.trade_log if t.get("profit", 0) < 0]
            self.stats["avg_win"] = sum(wins_list) / len(wins_list) if wins_list else 0
            self.stats["avg_loss"] = sum(losses_list) / len(losses_list) if losses_list else 0
            
            # Update trade log
            if contract_id in self.active_trades:
                trade = self.active_trades[contract_id]
                trade["profit"] = profit
                trade["exit_time"] = datetime.now().isoformat()
                trade["status"] = "closed"
                self.trade_log.append(trade)
                self.last_10_trades.insert(0, trade)
                if len(self.last_10_trades) > 10:
                    self.last_10_trades.pop()
                del self.active_trades[contract_id]
            
            logger.info(f"{'✅ WIN' if profit > 0 else '❌ LOSS'}: ${profit:.2f} | Total: ${self.stats['session_pnl']:.2f}")
            
            # Check kill switch
            if self.settings["kill_switch_armed"]:
                if self.stats["session_pnl"] <= -self.settings["stop_loss"]:
                    self.stop_bot("Stop loss triggered")
                elif self.stats["session_pnl"] >= self.settings["session_target"]:
                    self.stop_bot("Profit target achieved")
                elif self.stats["consecutive_losses"] >= self.settings["max_consecutive_losses"]:
                    self.stop_bot("Max consecutive losses reached")
            
        except Exception as e:
            logger.error(f"Close error: {e}")
    
    async def process_tick(self, tick_data: Dict):
        """Process incoming price tick"""
        symbol = tick_data.get("symbol")
        price = tick_data.get("quote")
        
        if not symbol or symbol != self.current_symbol:
            return
        
        self.current_price = price
        self.price_history.append(price)
        self.ticks_collected += 1
        
        # Update market conditions
        if len(self.price_history) >= 20:
            prices = list(self.price_history)
            returns = [prices[i] - prices[i-1] for i in range(1, len(prices))]
            self.market_conditions["volatility"] = sum(abs(r) for r in returns[-20:]) / 20 if returns else 0
            
            # Calculate RSI (simplified)
            gains = [r for r in returns if r > 0]
            losses = [abs(r) for r in returns if r < 0]
            avg_gain = sum(gains[-14:]) / 14 if gains else 0
            avg_loss = sum(losses[-14:]) / 14 if losses else 0
            if avg_loss > 0:
                rs = avg_gain / avg_loss
                self.market_conditions["rsi"] = 100 - (100 / (1 + rs))
            
            # Calculate trend
            sma_short = sum(prices[-20:]) / 20
            sma_long = sum(prices[-50:]) / 50 if len(prices) >= 50 else sma_short
            self.market_conditions["trend"] = "up" if sma_short > sma_long else "down"
            self.market_conditions["macd"] = "↑" if sma_short > sma_long else "↓"
            
            # Update market factors
            self.market_factors["trend_strength"] = min(abs(sma_short - sma_long) / sma_long * 100, 20)
            self.market_factors["volatility"] = min(self.market_conditions["volatility"] * 1000, 15)
            
            # Calculate market score
            self.calculate_market_score()
            
            # Generate and execute signal if conditions met
            signal = self.generate_signal()
            if signal:
                await self.execute_trade(signal)
        
        logger.info(f"{symbol}: ${price:.4f} | Score: {self.market_score} | RSI: {self.market_conditions['rsi']:.1f}")
    
    async def listen_for_prices(self):
        """Main listening loop"""
        while self.connected:
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
        """Main bot entry point"""
        if await self.connect_deriv():
            await self.subscribe_to_symbol()
            await self.listen_for_prices()
    
    def start_bot(self):
        """Start trading bot"""
        self.bot_status = "RUNNING"
        self.settings["auto_trading"] = True
        logger.info("Bot started - Auto-trading enabled")
    
    def stop_bot(self, reason: str = "Manual stop"):
        """Stop trading bot"""
        self.bot_status = "STOPPED"
        self.settings["auto_trading"] = False
        logger.info(f"Bot stopped: {reason}")
    
    def switch_account(self, account_id: str):
        """Switch between demo and real accounts"""
        if account_id in self.demo_accounts:
            self.current_account = account_id
            self.current_balance = self.demo_accounts[account_id]["balance"]
            self.initial_balance = self.demo_accounts[account_id]["initial_balance"]
            self.active_account = "demo"
        elif account_id in self.real_accounts:
            self.current_account = account_id
            self.current_balance = self.real_accounts[account_id]["balance"]
            self.initial_balance = self.real_accounts[account_id]["initial_balance"]
            self.active_account = "real"
        
        # Reset session stats when switching accounts
        self.reset_session()
        logger.info(f"Switched to account: {account_id}")
    
    def switch_symbol(self, symbol: str):
        """Switch trading symbol"""
        if symbol in self.symbols:
            self.current_symbol = symbol
            self.price_history.clear()
            self.ticks_collected = 0
            logger.info(f"Switched to symbol: {symbol}")
            # Resubscribe
            asyncio.create_task(self.subscribe_to_symbol())
    
    def reset_session(self):
        """Reset session statistics"""
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
            "avg_loss": 0.00,
            "max_drawdown": 0.00,
            "best_trade": 0.00,
            "worst_trade": 0.00
        }
        self.trade_log = []
        self.last_10_trades = []
        self.active_trades = {}
        
        # Reset strategies
        for strategy in self.strategies:
            self.strategies[strategy] = {"wins": 0, "losses": 0, "roi": 1.00}
    
    def get_full_state(self) -> Dict:
        """Get complete platform state"""
        return {
            "connected": self.connected,
            "bot_status": self.bot_status,
            "active_account": self.active_account,
            "current_account": self.current_account,
            "current_balance": self.current_balance,
            "initial_balance": self.initial_balance,
            "session_pnl": self.stats["session_pnl"],
            "current_symbol": self.current_symbol,
            "current_price": self.current_price,
            "ticks_collected": self.ticks_collected,
            "market_score": self.market_score,
            "need_score": self.need_score,
            "settings": self.settings,
            "stats": self.stats,
            "strategies": self.strategies,
            "market_conditions": self.market_conditions,
            "last_10_digits": self.last_10_digits,
            "even_odd_pattern": self.even_odd_pattern,
            "over_under_pattern": self.over_under_pattern,
            "active_trades": len(self.active_trades),
            "active_trades_list": list(self.active_trades.values()),
            "trade_log": self.trade_log[-20:],
            "demo_accounts": self.demo_accounts,
            "real_accounts": self.real_accounts,
            "symbols": self.symbols,
            "market_factors": self.market_factors
        }

# Initialize platform
platform = ProfessionalTradingPlatform()

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(platform.run())
    yield
    platform.stop_bot("Shutdown")

app = FastAPI(lifespan=lifespan)

# HTML Dashboard - Professional Trading Interface
HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SmartPip Trader - Professional Trading Platform</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', sans-serif;
            background: #0a0c15;
            color: #e5e7eb;
            overflow-x: hidden;
        }
        
        /* Header */
        .header {
            background: linear-gradient(135deg, #0f111a 0%, #1a1f2e 100%);
            border-bottom: 1px solid #2d3748;
            padding: 0 24px;
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .logo-icon {
            font-size: 28px;
        }
        
        .logo-text {
            font-size: 20px;
            font-weight: 800;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .account-selector {
            display: flex;
            gap: 12px;
            background: #1a1f2e;
            padding: 4px;
            border-radius: 12px;
        }
        
        .account-btn {
            padding: 6px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.2s;
            border: none;
            background: transparent;
            color: #94a3b8;
        }
        
        .account-btn.active {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
        }
        
        .balance-display {
            background: rgba(16, 185, 129, 0.1);
            padding: 8px 20px;
            border-radius: 12px;
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
        
        /* Main Layout */
        .main-container {
            display: grid;
            grid-template-columns: 320px 1fr 360px;
            gap: 16px;
            padding: 20px;
            max-width: 1600px;
            margin: 0 auto;
        }
        
        /* Panels */
        .panel {
            background: #0f111a;
            border-radius: 16px;
            border: 1px solid #2d3748;
            overflow: hidden;
        }
        
        .panel-header {
            padding: 16px 20px;
            border-bottom: 1px solid #2d3748;
            background: #0a0c15;
            font-weight: 600;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #94a3b8;
        }
        
        .panel-content {
            padding: 20px;
        }
        
        /* Market Card */
        .market-card {
            background: linear-gradient(135deg, #1a1f2e, #0f111a);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            margin-bottom: 20px;
            border: 1px solid #2d3748;
        }
        
        .market-symbol {
            font-size: 18px;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 8px;
        }
        
        .market-price {
            font-size: 32px;
            font-weight: bold;
            margin: 10px 0;
        }
        
        .market-status {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .status-idle { background: #f59e0b; color: white; }
        .status-running { background: #10b981; color: white; }
        .status-stopped { background: #ef4444; color: white; }
        
        /* Market Score */
        .market-score {
            background: #1a1f2e;
            border-radius: 12px;
            padding: 16px;
            text-align: center;
            margin-bottom: 20px;
        }
        
        .score-value {
            font-size: 48px;
            font-weight: bold;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .score-need {
            font-size: 14px;
            color: #94a3b8;
            margin-top: 5px;
        }
        
        /* Control Buttons */
        .control-buttons {
            display: flex;
            gap: 12px;
            margin-bottom: 20px;
        }
        
        .btn-start {
            flex: 1;
            background: linear-gradient(135deg, #10b981, #059669);
            color: white;
            border: none;
            padding: 12px;
            border-radius: 10px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        .btn-stop {
            flex: 1;
            background: linear-gradient(135deg, #ef4444, #dc2626);
            color: white;
            border: none;
            padding: 12px;
            border-radius: 10px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        .btn-manual {
            background: #2d3748;
            color: white;
            border: none;
            padding: 12px;
            border-radius: 10px;
            font-weight: bold;
            cursor: pointer;
        }
        
        .btn-start:hover, .btn-stop:hover, .btn-manual:hover {
            transform: translateY(-2px);
        }
        
        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 20px;
        }
        
        .stat-item {
            background: #1a1f2e;
            padding: 12px;
            border-radius: 10px;
            text-align: center;
        }
        
        .stat-label {
            font-size: 11px;
            color: #94a3b8;
            text-transform: uppercase;
            margin-bottom: 5px;
        }
        
        .stat-value {
            font-size: 20px;
            font-weight: bold;
        }
        
        /* Digits Display */
        .digits-container {
            background: #1a1f2e;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 20px;
        }
        
        .digits-title {
            font-size: 12px;
            color: #94a3b8;
            margin-bottom: 12px;
        }
        
        .digits-row {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 12px;
        }
        
        .digit-box {
            width: 40px;
            height: 40px;
            background: #0f111a;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 14px;
            border: 1px solid #2d3748;
        }
        
        .digit-up { color: #10b981; }
        .digit-over { color: #f59e0b; }
        
        /* Kill Switch */
        .kill-switch {
            background: #1a1f2e;
            border-radius: 12px;
            padding: 16px;
            margin-top: 16px;
        }
        
        .switch-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        
        .toggle-switch {
            position: relative;
            display: inline-block;
            width: 50px;
            height: 24px;
        }
        
        .toggle-switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }
        
        .toggle-slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #4a5568;
            transition: 0.3s;
            border-radius: 24px;
        }
        
        .toggle-slider:before {
            position: absolute;
            content: "";
            height: 18px;
            width: 18px;
            left: 3px;
            bottom: 3px;
            background-color: white;
            transition: 0.3s;
            border-radius: 50%;
        }
        
        input:checked + .toggle-slider {
            background-color: #667eea;
        }
        
        input:checked + .toggle-slider:before {
            transform: translateX(26px);
        }
        
        /* Trade Log */
        .trade-log {
            max-height: 300px;
            overflow-y: auto;
        }
        
        .trade-entry {
            background: #1a1f2e;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 8px;
            font-size: 12px;
        }
        
        .trade-win { border-left: 3px solid #10b981; }
        .trade-loss { border-left: 3px solid #ef4444; }
        
        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        
        ::-webkit-scrollbar-track {
            background: #1a1f2e;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #667eea;
            border-radius: 3px;
        }
        
        /* Symbol Selector */
        .symbol-selector {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }
        
        .symbol-btn {
            background: #1a1f2e;
            border: 1px solid #2d3748;
            color: #94a3b8;
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
            transition: all 0.2s;
        }
        
        .symbol-btn.active {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border-color: transparent;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">
            <div class="logo-icon">🤖</div>
            <div class="logo-text">SMARTPIP TRADER</div>
        </div>
        <div class="account-selector" id="accountSelector">
            <button class="account-btn" data-account="VRTC14297314">DEMO</button>
            <button class="account-btn" data-account="REAL12345678">REAL</button>
        </div>
        <div class="balance-display">
            <div class="balance-label">Balance</div>
            <div class="balance-value" id="balance">$10,000</div>
        </div>
    </div>
    
    <div class="main-container">
        <!-- Left Panel -->
        <div class="panel">
            <div class="panel-header">Live Trade</div>
            <div class="panel-content">
                <div class="market-card">
                    <div class="market-symbol" id="symbol">1HZ10V</div>
                    <div class="market-price" id="price">$10,179.83</div>
                    <div class="market-status" id="botStatus">IDLE</div>
                </div>
                
                <div class="symbol-selector" id="symbolSelector">
                    <button class="symbol-btn active" data-symbol="1HZ10V">1HZ10V</button>
                    <button class="symbol-btn" data-symbol="R_10">R_10</button>
                    <button class="symbol-btn" data-symbol="R_25">R_25</button>
                    <button class="symbol-btn" data-symbol="R_50">R_50</button>
                    <button class="symbol-btn" data-symbol="R_75">R_75</button>
                    <button class="symbol-btn" data-symbol="R_100">R_100</button>
                </div>
                
                <div class="market-score">
                    <div class="score-value" id="marketScore">50</div>
                    <div class="score-need">Need ≥85 to trade (<span id="pointsNeeded">35</span> points away)</div>
                </div>
                
                <div class="control-buttons">
                    <button class="btn-start" onclick="startBot()">START</button>
                    <button class="btn-stop" onclick="stopBot()">STOP</button>
                    <button class="btn-manual" onclick="manualTrade()">Manual Trade</button>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-label">Balance</div>
                        <div class="stat-value" id="balance2">$10,075.32</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Session P/L</div>
                        <div class="stat-value" id="sessionPnl">+$0.00</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Trades</div>
                        <div class="stat-value" id="tradeCount">0 / 3</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Consecutive Losses</div>
                        <div class="stat-value" id="consecutiveLosses">0 / 2</div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Center Panel -->
        <div class="panel">
            <div class="panel-header">Market Board</div>
            <div class="panel-content">
                <div class="digits-container">
                    <div class="digits-title">Last 10 Digits (Edge)</div>
                    <div class="digits-row" id="digitsRow"></div>
                    <div class="digits-row">
                        <span>Even/Odd: <strong id="evenOdd">3E / 7O</strong> → <span id="evenOddSignal">EVEN signal</span></span>
                    </div>
                    <div class="digits-row">
                        <span>Over/Under: <strong id="overUnder">4O / 6U</strong> → <span id="overUnderSignal">No edge</span></span>
                    </div>
                </div>
                
                <div class="market-score">
                    <div class="score-value" id="rsiValue">63.5</div>
                    <div class="score-need">RSI · <span id="macdSignal">MACD ↑</span></div>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-label">Win Rate</div>
                        <div class="stat-value" id="winRate">0%</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">P. Factor</div>
                        <div class="stat-value" id="profitFactor">0</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Avg Win</div>
                        <div class="stat-value" id="avgWin">$0.00</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Avg Loss</div>
                        <div class="stat-value" id="avgLoss">-$0.00</div>
                    </div>
                </div>
                
                <div class="kill-switch">
                    <div class="switch-header">
                        <span>🔴 Smart Kill-Switch</span>
                        <label class="toggle-switch">
                            <input type="checkbox" id="killSwitch" onchange="toggleKillSwitch()">
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                    <div style="font-size: 12px; color: #94a3b8;">
                        Stop-Loss: $<span id="stopLoss">10</span> · 
                        Loss Streak: <span id="lossStreak">0</span>/2 · 
                        Profit Target: $<span id="profitTarget">2</span>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Right Panel -->
        <div class="panel">
            <div class="panel-header">Profit Dashboard</div>
            <div class="panel-content">
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-label">Wins</div>
                        <div class="stat-value" id="wins">0</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Losses</div>
                        <div class="stat-value" id="losses">0</div>
                    </div>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-label">even odd</div>
                        <div class="stat-value" id="evenOddPerf">0W 0L</div>
                        <div class="stat-label">1.00×</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">over under</div>
                        <div class="stat-value" id="overUnderPerf">0W 0L</div>
                        <div class="stat-label">1.00×</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">streak reversal</div>
                        <div class="stat-value" id="streakPerf">0W 0L</div>
                        <div class="stat-label">1.00×</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">rise fall</div>
                        <div class="stat-value" id="riseFallPerf">0W 0L</div>
                        <div class="stat-label">1.00×</div>
                    </div>
                </div>
                
                <div class="panel-header" style="margin-top: 16px;">Trade Log</div>
                <div class="trade-log" id="tradeLog">
                    <div style="text-align: center; color: #94a3b8; padding: 20px;">No trades yet — start the engine</div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let ws = null;
        
        function connectWebSocket() {
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${location.host}/ws`);
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            ws.onclose = () => setTimeout(connectWebSocket, 3000);
        }
        
        function updateDashboard(data) {
            // Market info
            document.getElementById('price').innerHTML = `$${data.current_price?.toFixed(4) || '0.00'}`;
            document.getElementById('marketScore').innerHTML = data.market_score || 50;
            const pointsNeeded = Math.max(0, (data.need_score || 85) - (data.market_score || 50));
            document.getElementById('pointsNeeded').innerHTML = pointsNeeded;
            
            // Bot status
            const statusElement = document.getElementById('botStatus');
            const botStatus = data.bot_status || 'STOPPED';
            statusElement.innerHTML = botStatus;
            statusElement.className = `market-status status-${botStatus.toLowerCase()}`;
            
            // Balance
            document.getElementById('balance').innerHTML = `$${(data.current_balance || 10000).toFixed(2)}`;
            document.getElementById('balance2').innerHTML = `$${(data.current_balance || 10000).toFixed(2)}`;
            
            // Session PnL
            const sessionPnl = data.stats?.session_pnl || 0;
            const pnlElement = document.getElementById('sessionPnl');
            pnlElement.innerHTML = `${sessionPnl >= 0 ? '+' : ''}$${sessionPnl.toFixed(2)}`;
            pnlElement.style.color = sessionPnl >= 0 ? '#10b981' : '#ef4444';
            
            // Trade stats
            document.getElementById('tradeCount').innerHTML = `${data.stats?.total_trades || 0} / 3`;
            document.getElementById('consecutiveLosses').innerHTML = `${data.stats?.consecutive_losses || 0} / 2`;
            document.getElementById('winRate').innerHTML = `${data.stats?.win_rate || 0}%`;
            document.getElementById('profitFactor').innerHTML = (data.stats?.profit_factor || 0).toFixed(2);
            document.getElementById('avgWin').innerHTML = `$${(data.stats?.avg_win || 0).toFixed(2)}`;
            document.getElementById('avgLoss').innerHTML = `-$${Math.abs(data.stats?.avg_loss || 0).toFixed(2)}`;
            document.getElementById('wins').innerHTML = data.stats?.wins || 0;
            document.getElementById('losses').innerHTML = data.stats?.losses || 0;
            
            // Market conditions
            document.getElementById('rsiValue').innerHTML = (data.market_conditions?.rsi || 50).toFixed(1);
            document.getElementById('macdSignal').innerHTML = `MACD ${data.market_conditions?.macd || '→'}`;
            
            // Digits display
            if (data.last_10_digits) {
                const digitsRow = document.getElementById('digitsRow');
                digitsRow.innerHTML = data.last_10_digits.slice(-10).map(d => 
                    `<div class="digit-box ${d === 'U' ? 'digit-up' : d === 'O' ? 'digit-over' : ''}">${d}</div>`
                ).join('');
            }
            
            // Even/Odd pattern
            if (data.even_odd_pattern) {
                document.getElementById('evenOdd').innerHTML = `${data.even_odd_pattern.even || 0}E / ${data.even_odd_pattern.odd || 0}O`;
                document.getElementById('evenOddSignal').innerHTML = data.even_odd_pattern.signal || 'No signal';
            }
            
            // Over/Under pattern
            if (data.over_under_pattern) {
                document.getElementById('overUnder').innerHTML = `${data.over_under_pattern.over || 0}O / ${data.over_under_pattern.under || 0}U`;
                document.getElementById('overUnderSignal').innerHTML = data.over_under_pattern.edge ? 'EDGE detected' : 'No edge';
            }
            
            // Strategy performance
            if (data.strategies) {
                document.getElementById('evenOddPerf').innerHTML = `${data.strategies.even_odd?.wins || 0}W ${data.strategies.even_odd?.losses || 0}L`;
                document.getElementById('overUnderPerf').innerHTML = `${data.strategies.over_under?.wins || 0}W ${data.strategies.over_under?.losses || 0}L`;
                document.getElementById('streakPerf').innerHTML = `${data.strategies.streak_reversal?.wins || 0}W ${data.strategies.streak_reversal?.losses || 0}L`;
                document.getElementById('riseFallPerf').innerHTML = `${data.strategies.rise_fall?.wins || 0}W ${data.strategies.rise_fall?.losses || 0}L`;
            }
            
            // Trade log
            if (data.trade_log && data.trade_log.length > 0) {
                const logContainer = document.getElementById('tradeLog');
                logContainer.innerHTML = data.trade_log.slice().reverse().map(trade => `
                    <div class="trade-entry ${trade.profit > 0 ? 'trade-win' : trade.profit < 0 ? 'trade-loss' : ''}">
                        <div>${new Date(trade.entry_time).toLocaleTimeString()} - ${trade.symbol} - ${trade.direction}</div>
                        <div>Amount: $${trade.amount} | ${trade.profit > 0 ? '+' : ''}$${(trade.profit || 0).toFixed(2)}</div>
                        <div>Confidence: ${trade.confidence?.toFixed(0)}% | ${trade.strategy}</div>
                    </div>
                `).join('');
            }
        }
        
        function startBot() {
            fetch('/api/start', { method: 'POST' }).then(() => {
                document.getElementById('botStatus').innerHTML = 'RUNNING';
                document.getElementById('botStatus').className = 'market-status status-running';
            });
        }
        
        function stopBot() {
            fetch('/api/stop', { method: 'POST' }).then(() => {
                document.getElementById('botStatus').innerHTML = 'STOPPED';
                document.getElementById('botStatus').className = 'market-status status-stopped';
            });
        }
        
        function manualTrade() {
            const amount = prompt('Enter trade amount:', '1');
            const direction = confirm('CALL = OK, PUT = Cancel') ? 'CALL' : 'PUT';
            if (amount) {
                fetch('/api/manual_trade', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ direction, amount: parseFloat(amount), duration: 2 })
                });
            }
        }
        
        function toggleKillSwitch() {
            const enabled = document.getElementById('killSwitch').checked;
            fetch('/api/kill_switch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled })
            });
        }
        
        // Account switching
        document.querySelectorAll('.account-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.account-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                fetch('/api/switch_account', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ account_id: btn.dataset.account })
                });
            });
        });
        
        // Symbol switching
        document.querySelectorAll('.symbol-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.symbol-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                document.getElementById('symbol').innerHTML = btn.dataset.symbol;
                fetch('/api/switch_symbol', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ symbol: btn.dataset.symbol })
                });
            });
        });
        
        connectWebSocket();
        setInterval(() => {
            fetch('/api/status').then(res => res.json()).then(data => updateDashboard(data));
        }, 2000);
    </script>
</body>
</html>
"""

# API Endpoints
@app.get("/")
async def root():
    return HTMLResponse(HTML_DASHBOARD)

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

@app.post("/api/manual_trade")
async def manual_trade(request: Request):
    try:
        data = await request.json()
        signal = {
            "type": "manual",
            "direction": data.get("direction", "CALL"),
            "confidence": 100,
            "reason": "Manual trade"
        }
        await platform.execute_trade(signal)
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.post("/api/switch_account")
async def switch_account(request: Request):
    try:
        data = await request.json()
        platform.switch_account(data.get("account_id"))
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.post("/api/switch_symbol")
async def switch_symbol(request: Request):
    try:
        data = await request.json()
        platform.switch_symbol(data.get("symbol"))
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.post("/api/kill_switch")
async def kill_switch(request: Request):
    try:
        data = await request.json()
        platform.settings["kill_switch_armed"] = data.get("enabled", False)
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