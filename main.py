# main.py - Fully Integrated Professional Trading Platform with Real Deriv Data
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
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealDerivTradingPlatform:
    def __init__(self):
        # Deriv connection
        self.websocket = None
        self.connected = False
        self.api_token = os.getenv("DERIV_API_TOKEN")
        self.app_id = os.getenv("DERIV_APP_ID", "1089")
        
        # Account type selection (demo is default Deriv demo account)
        self.account_mode = "demo"  # "demo" or "real"
        self.demo_balance = 10000.00
        self.real_balance = 0.00
        self.current_balance = 10000.00
        self.currency = "USD"
        
        # Bot status
        self.bot_status = "STOPPED"
        self.bot_running = False
        
        # Trading symbols (Deriv Volatility Indices)
        self.symbols = {
            "1HZ10V": {"name": "1HZ10V", "active": True},
            "R_10": {"name": "Volatility 10 Index", "active": True},
            "R_25": {"name": "Volatility 25 Index", "active": True},
            "R_50": {"name": "Volatility 50 Index", "active": True},
            "R_75": {"name": "Volatility 75 Index", "active": True},
            "R_100": {"name": "Volatility 100 Index", "active": True}
        }
        self.current_symbol = "1HZ10V"
        self.current_price = 0
        self.price_history = deque(maxlen=200)
        self.ticks_collected = 0
        
        # Trading settings
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
            "rsi": 50.0,
            "macd": "→",
            "volatility": 0.00,
            "trend": "neutral"
        }
        
        # Pattern analysis
        self.last_10_digits = ["4", "U", "0", "U", "7", "O", "9", "O", "5", "O"]
        self.even_odd_pattern = {"even": 3, "odd": 7, "signal": "EVEN"}
        self.over_under_pattern = {"over": 4, "under": 6, "edge": False}
        
        # Active trades
        self.active_trades = {}
        self.trade_log = []
        
        # Market score factors
        self.market_factors = {
            "trend_strength": 0,
            "volatility_score": 0,
            "momentum": 0,
            "pattern_match": 0
        }
    
    async def connect_deriv(self):
        """Connect to Deriv WebSocket with real API"""
        if not self.api_token:
            logger.error("No API token found! Set DERIV_API_TOKEN environment variable")
            return False
        
        # Always use wss://ws.binaryws.com/websockets/v3
        # For demo accounts, app_id=1089 works
        # For real accounts, you need your registered app_id
        url = f"wss://ws.binaryws.com/websockets/v3?app_id={self.app_id}"
        
        try:
            self.websocket = await websockets.connect(url)
            logger.info(f"WebSocket connected to {url}")
            
            # Authorize with token
            auth_msg = {"authorize": self.api_token}
            await self.websocket.send(json.dumps(auth_msg))
            response = await self.websocket.recv()
            auth_data = json.loads(response)
            
            if auth_data.get("error"):
                logger.error(f"Authorization failed: {auth_data['error']['message']}")
                return False
            
            logger.info(f"Authorization successful! Account: {auth_data.get('authorize', {}).get('loginid', 'Unknown')}")
            
            # Get account balance
            await self.get_balance()
            
            # Get available symbols
            await self.get_available_symbols()
            
            self.connected = True
            return True
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def get_balance(self):
        """Fetch real account balance from Deriv"""
        try:
            balance_msg = {"balance": 1}
            await self.websocket.send(json.dumps(balance_msg))
            response = await self.websocket.recv()
            balance_data = json.loads(response)
            
            if "balance" in balance_data:
                balance_info = balance_data["balance"]
                self.current_balance = float(balance_info.get("balance", 0))
                self.currency = balance_info.get("currency", "USD")
                
                # Determine if this is demo or real based on loginid
                loginid = balance_info.get("loginid", "")
                if loginid.startswith("VRTC") or loginid.startswith("VRT"):
                    self.account_mode = "demo"
                    self.demo_balance = self.current_balance
                else:
                    self.account_mode = "real"
                    self.real_balance = self.current_balance
                
                logger.info(f"Balance: {self.currency} {self.current_balance:,.2f} (Account: {loginid})")
                return True
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
        
        return False
    
    async def get_available_symbols(self):
        """Get active symbols from Deriv"""
        try:
            active_symbols_msg = {"active_symbols": "brief"}
            await self.websocket.send(json.dumps(active_symbols_msg))
            response = await self.websocket.recv()
            symbols_data = json.loads(response)
            
            if "active_symbols" in symbols_data:
                for symbol in symbols_data["active_symbols"]:
                    if symbol.get("market") == "volatility":
                        logger.info(f"Available symbol: {symbol.get('symbol')} - {symbol.get('display_name')}")
        except Exception as e:
            logger.error(f"Failed to get symbols: {e}")
    
    async def subscribe_to_symbol(self):
        """Subscribe to price ticks for current symbol"""
        if not self.connected:
            return
        
        subscribe_msg = {
            "ticks": self.current_symbol,
            "subscribe": 1
        }
        await self.websocket.send(json.dumps(subscribe_msg))
        logger.info(f"Subscribed to {self.current_symbol}")
    
    async def get_candles(self, symbol: str = None, count: int = 100):
        """Get historical candles for analysis"""
        if not self.connected:
            return None
        
        symbol = symbol or self.current_symbol
        candles_msg = {
            "ticks_history": symbol,
            "adjust_start_time": 1,
            "count": count,
            "end": "latest",
            "start": 1,
            "style": "candles"
        }
        await self.websocket.send(json.dumps(candles_msg))
        response = await self.websocket.recv()
        return json.loads(response)
    
    def calculate_market_score(self):
        """Calculate comprehensive market score based on real data"""
        score = 50
        
        # RSI factor
        if self.market_conditions["rsi"] < 30 or self.market_conditions["rsi"] > 70:
            score += 15
        elif self.market_conditions["rsi"] < 40 or self.market_conditions["rsi"] > 60:
            score += 8
        
        # Trend factor
        if self.market_conditions["trend"] == "up":
            score += 10
        elif self.market_conditions["trend"] == "down":
            score += 5
        
        # Volatility factor
        if 0.001 < self.market_conditions["volatility"] < 0.005:
            score += 10
        
        # Pattern factor
        if self.over_under_pattern.get("edge", False):
            score += 15
        
        if self.even_odd_pattern.get("signal") == "EVEN":
            score += 5
        
        self.market_score = min(max(score, 0), 100)
        return self.market_score
    
    def generate_signal(self):
        """Generate trading signal based on analysis"""
        if not self.settings["auto_trading"] or self.bot_status != "RUNNING":
            return None
        
        # Check if market score meets threshold
        if self.market_score < self.settings["min_confidence"]:
            return None
        
        # Check trade limits
        if len(self.active_trades) >= self.settings["max_trades_per_session"]:
            return None
        
        # Check consecutive losses
        if self.stats["consecutive_losses"] >= self.settings["max_consecutive_losses"]:
            return None
        
        # Check stop loss
        if self.stats["session_pnl"] <= -self.settings["stop_loss"]:
            self.stop_bot("Stop loss hit")
            return None
        
        # Check profit target
        if self.stats["session_pnl"] >= self.settings["profit_target"]:
            self.stop_bot("Profit target achieved")
            return None
        
        # Generate signal based on patterns
        if self.even_odd_pattern.get("signal") == "EVEN" and self.even_odd_pattern.get("odd", 0) >= 7:
            return {
                "type": "even_odd",
                "direction": "CALL",
                "confidence": min(70 + (self.market_score - 50), 95),
                "reason": "Strong even/odd edge detected"
            }
        
        # Technical signal based on RSI
        if self.market_conditions["rsi"] < 35:
            return {
                "type": "rise_fall",
                "direction": "CALL",
                "confidence": 70 + (35 - self.market_conditions["rsi"]) / 2,
                "reason": f"Oversold RSI: {self.market_conditions['rsi']:.1f}"
            }
        
        if self.market_conditions["rsi"] > 65:
            return {
                "type": "rise_fall",
                "direction": "PUT",
                "confidence": 70 + (self.market_conditions["rsi"] - 65) / 2,
                "reason": f"Overbought RSI: {self.market_conditions['rsi']:.1f}"
            }
        
        return None
    
    async def execute_trade(self, signal: Dict):
        """Execute trade on Deriv"""
        if not self.connected:
            logger.error("Not connected to Deriv")
            return None
        
        amount = self.settings["base_trade_amount"]
        duration = self.settings["trade_duration"]
        
        trade_msg = {
            "buy": 1,
            "parameters": {
                "amount": amount,
                "basis": "stake",
                "contract_type": signal["direction"].lower(),
                "currency": self.currency,
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
                    "status": "open",
                    "reason": signal["reason"]
                }
                self.active_trades[contract_id] = trade
                self.trade_log.append(trade)
                
                logger.info(f"🎯 TRADE: {signal['direction']} {self.current_symbol} | ${amount} | {signal['confidence']:.0f}%")
                
                # Auto-close after duration
                asyncio.create_task(self.close_trade(contract_id, duration * 60))
                return contract_id
            else:
                logger.error(f"Trade failed: {data}")
                
        except Exception as e:
            logger.error(f"Trade execution error: {e}")
        
        return None
    
    async def close_trade(self, contract_id: int, seconds: int):
        """Close trade and record result"""
        await asyncio.sleep(seconds)
        
        try:
            # Get contract status
            portfolio_msg = {"portfolio": 1}
            await self.websocket.send(json.dumps(portfolio_msg))
            response = await self.websocket.recv()
            data = json.loads(response)
            
            profit = 0
            if "portfolio" in data:
                for contract in data["portfolio"].get("contracts", []):
                    if contract["contract_id"] == contract_id:
                        profit = float(contract.get("profit", 0))
                        break
            
            # Update statistics
            self.stats["total_trades"] += 1
            self.stats["session_pnl"] += profit
            self.current_balance += profit
            
            if profit > 0:
                self.stats["wins"] += 1
                self.stats["consecutive_wins"] += 1
                self.stats["consecutive_losses"] = 0
                if profit > self.stats["best_trade"]:
                    self.stats["best_trade"] = profit
                
                # Update strategy performance
                if contract_id in self.active_trades:
                    strategy = self.active_trades[contract_id].get("strategy", "rise_fall")
                    if strategy in self.strategies:
                        self.strategies[strategy]["wins"] += 1
            else:
                self.stats["losses"] += 1
                self.stats["consecutive_losses"] += 1
                self.stats["consecutive_wins"] = 0
                if profit < self.stats["worst_trade"]:
                    self.stats["worst_trade"] = profit
                
                # Update strategy performance
                if contract_id in self.active_trades:
                    strategy = self.active_trades[contract_id].get("strategy", "rise_fall")
                    if strategy in self.strategies:
                        self.strategies[strategy]["losses"] += 1
            
            # Update win rate
            if self.stats["total_trades"] > 0:
                self.stats["win_rate"] = (self.stats["wins"] / self.stats["total_trades"]) * 100
            
            # Update profit factor
            total_wins = sum(t.get("profit", 0) for t in self.trade_log if t.get("profit", 0) > 0)
            total_losses = abs(sum(t.get("profit", 0) for t in self.trade_log if t.get("profit", 0) < 0))
            self.stats["profit_factor"] = total_wins / total_losses if total_losses > 0 else 0
            
            # Update averages
            wins_list = [t.get("profit", 0) for t in self.trade_log if t.get("profit", 0) > 0]
            losses_list = [t.get("profit", 0) for t in self.trade_log if t.get("profit", 0) < 0]
            self.stats["avg_win"] = sum(wins_list) / len(wins_list) if wins_list else 0
            self.stats["avg_loss"] = sum(losses_list) / len(losses_list) if losses_list else 0
            
            # Update trade record
            if contract_id in self.active_trades:
                trade = self.active_trades[contract_id]
                trade["profit"] = profit
                trade["exit_time"] = datetime.now().isoformat()
                trade["status"] = "closed"
                del self.active_trades[contract_id]
            
            logger.info(f"{'✅ WIN' if profit > 0 else '❌ LOSS'}: ${profit:.2f} | Session: ${self.stats['session_pnl']:.2f}")
            
            # Check kill switch conditions
            if self.settings["kill_switch_armed"]:
                if self.stats["session_pnl"] <= -self.settings["stop_loss"]:
                    self.stop_bot(f"Stop loss triggered (${abs(self.stats['session_pnl']):.2f})")
                elif self.stats["session_pnl"] >= self.settings["profit_target"]:
                    self.stop_bot(f"Profit target achieved (${self.stats['session_pnl']:.2f})")
                elif self.stats["consecutive_losses"] >= self.settings["max_consecutive_losses"]:
                    self.stop_bot(f"Max consecutive losses: {self.stats['consecutive_losses']}")
            
        except Exception as e:
            logger.error(f"Close trade error: {e}")
    
    async def process_tick(self, tick_data: Dict):
        """Process incoming price tick"""
        symbol = tick_data.get("symbol")
        price = tick_data.get("quote")
        
        if not symbol or symbol != self.current_symbol:
            return
        
        self.current_price = float(price)
        self.price_history.append(self.current_price)
        self.ticks_collected += 1
        
        # Update market analysis
        if len(self.price_history) >= 20:
            prices = list(self.price_history)
            
            # Calculate RSI
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
            
            # Calculate trend
            sma_short = sum(prices[-20:]) / 20
            sma_long = sum(prices[-50:]) / 50 if len(prices) >= 50 else sma_short
            self.market_conditions["trend"] = "up" if sma_short > sma_long else "down"
            self.market_conditions["macd"] = "↑" if sma_short > sma_long else "↓"
            
            # Calculate volatility
            returns = [prices[i] - prices[i-1] for i in range(1, len(prices))]
            self.market_conditions["volatility"] = sum(abs(r) for r in returns[-20:]) / 20 if returns else 0
            
            # Update market score
            self.calculate_market_score()
            
            # Update pattern analysis (simplified tick-based)
            last_price = prices[-1]
            last_change = (prices[-1] - prices[-2]) / prices[-2] * 100 if len(prices) > 1 else 0
            self.even_odd_pattern = {
                "even": sum(1 for p in prices[-10:] if int(p * 100) % 2 == 0),
                "odd": sum(1 for p in prices[-10:] if int(p * 100) % 2 == 1),
                "signal": "EVEN" if sum(1 for p in prices[-10:] if int(p * 100) % 2 == 0) > 
                                 sum(1 for p in prices[-10:] if int(p * 100) % 2 == 1) else "ODD"
            }
            
            self.over_under_pattern = {
                "over": sum(1 for p in prices[-10:] if p > sum(prices[-10:])/10),
                "under": sum(1 for p in prices[-10:] if p < sum(prices[-10:])/10),
                "edge": abs(sum(1 for p in prices[-10:] if p > sum(prices[-10:])/10) - 
                           sum(1 for p in prices[-10:] if p < sum(prices[-10:])/10)) >= 3
            }
            
            # Update last 10 digits for display
            self.last_10_digits = [str(int(p * 100) % 10) for p in prices[-10:]]
            
            # Generate and execute signal
            signal = self.generate_signal()
            if signal:
                await self.execute_trade(signal)
        
        logger.info(f"{symbol}: ${self.current_price:.4f} | Score: {self.market_score} | RSI: {self.market_conditions['rsi']:.1f}")
    
    async def listen_for_prices(self):
        """Main listening loop"""
        logger.info("Listening for price ticks...")
        
        while self.connected and self.bot_running:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                if "tick" in data:
                    await self.process_tick(data["tick"])
                elif "error" in data:
                    logger.error(f"Deriv error: {data['error']['message']}")
                elif "balance" in data:
                    # Update balance when changed
                    self.current_balance = float(data["balance"]["balance"])
                    
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Connection closed, reconnecting...")
                await self.reconnect()
                break
            except Exception as e:
                logger.error(f"Listen error: {e}")
                await asyncio.sleep(1)
    
    async def reconnect(self):
        """Reconnect to Deriv"""
        self.connected = False
        await asyncio.sleep(5)
        await self.connect_deriv()
        if self.connected:
            await self.subscribe_to_symbol()
            await self.listen_for_prices()
    
    async def run(self):
        """Main bot entry point"""
        logger.info("Starting SmartPip Trading Platform...")
        self.bot_running = True
        
        if await self.connect_deriv():
            await self.subscribe_to_symbol()
            await self.listen_for_prices()
    
    def start_bot(self):
        """Start auto-trading"""
        self.bot_status = "RUNNING"
        self.settings["auto_trading"] = True
        logger.info("Bot started - Auto-trading enabled")
    
    def stop_bot(self, reason: str = "Manual stop"):
        """Stop auto-trading"""
        self.bot_status = "STOPPED"
        self.settings["auto_trading"] = False
        logger.info(f"Bot stopped: {reason}")
    
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
            "best_trade": 0.00,
            "worst_trade": 0.00
        }
        self.trade_log = []
        self.active_trades = {}
        
        for strategy in self.strategies:
            self.strategies[strategy] = {"wins": 0, "losses": 0, "roi": 1.00}
    
    async def manual_trade_order(self, direction: str, amount: float, duration: int):
        """Execute manual trade"""
        signal = {
            "type": "manual",
            "direction": direction,
            "confidence": 100,
            "reason": "Manual trade"
        }
        self.settings["base_trade_amount"] = amount
        self.settings["trade_duration"] = duration
        return await self.execute_trade(signal)
    
    def get_full_state(self) -> Dict:
        """Get complete platform state for frontend"""
        return {
            "connected": self.connected,
            "bot_status": self.bot_status,
            "account_mode": self.account_mode,
            "current_balance": self.current_balance,
            "demo_balance": self.demo_balance,
            "real_balance": self.real_balance,
            "currency": self.currency,
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
            "active_trades_count": len(self.active_trades),
            "active_trades": list(self.active_trades.values()),
            "trade_log": self.trade_log[-30:],
            "symbols": list(self.symbols.keys())
        }

# Initialize platform
platform = RealDerivTradingPlatform()

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(platform.run())
    yield
    platform.bot_running = False
    if platform.websocket:
        await platform.websocket.close()

app = FastAPI(lifespan=lifespan)

# Serve the same professional HTML dashboard (keeping the same HTML from previous response)
# The HTML remains the same - it will now display REAL data from Deriv

# API Endpoints
@app.get("/")
async def root():
    # Use the professional HTML from the previous response
    HTML_DASHBOARD = """[The complete HTML from the previous response goes here]"""
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
        result = await platform.manual_trade_order(
            direction=data.get("direction", "CALL"),
            amount=float(data.get("amount", 1)),
            duration=int(data.get("duration", 2))
        )
        return JSONResponse({"success": result is not None})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.post("/api/switch_symbol")
async def switch_symbol(request: Request):
    try:
        data = await request.json()
        platform.current_symbol = data.get("symbol")
        platform.price_history.clear()
        platform.ticks_collected = 0
        await platform.subscribe_to_symbol()
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.post("/api/update_settings")
async def update_settings(request: Request):
    try:
        data = await request.json()
        for key, value in data.items():
            if key in platform.settings:
                platform.settings[key] = value
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.post("/api/reset_session")
async def reset_session():
    platform.reset_session()
    return JSONResponse({"success": True})

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