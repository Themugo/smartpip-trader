# main.py - ULTIMATE PROFESSIONAL TRADING SYSTEM
import os
import json
import asyncio
import random
import math
import hashlib
from datetime import datetime, timedelta
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any
from collections import deque
import logging
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UltimateTradingSystem:
    def __init__(self):
        # ========== CONNECTION & ACCOUNTS ==========
        self.websocket = None
        self.connected = False
        self.api_token = os.getenv("DERIV_API_TOKEN")
        self.app_id = os.getenv("DERIV_APP_ID", "1089")
        
        # Account Management
        self.accounts = {
            "demo": {
                "id": "VRTC14297314",
                "balance": 10000.00,
                "initial": 10000.00,
                "pnl": 0.00,
                "type": "demo",
                "status": "active",
                "leverage": 1,
                "risk_level": "Low"
            },
            "real": {
                "id": "REAL12345678",
                "balance": 0.00,
                "initial": 0.00,
                "pnl": 0.00,
                "type": "real",
                "status": "active",
                "leverage": 1,
                "risk_level": "Medium"
            }
        }
        self.active_account = "demo"
        self.current_balance = 10000.00
        self.currency = "USD"
        
        # ========== MARKET DATA ==========
        self.symbols = {
            "1HZ10V": {"name": "1HZ10V", "type": "synthetic", "spread": 0.001, "min_duration": 1, "max_duration": 300},
            "R_10": {"name": "Volatility 10", "type": "volatility", "spread": 0.002, "min_duration": 1, "max_duration": 300},
            "R_25": {"name": "Volatility 25", "type": "volatility", "spread": 0.003, "min_duration": 1, "max_duration": 300},
            "R_50": {"name": "Volatility 50", "type": "volatility", "spread": 0.004, "min_duration": 1, "max_duration": 300},
            "R_75": {"name": "Volatility 75", "type": "volatility", "spread": 0.005, "min_duration": 1, "max_duration": 300},
            "R_100": {"name": "Volatility 100", "type": "volatility", "spread": 0.006, "min_duration": 1, "max_duration": 300}
        }
        self.current_symbol = "1HZ10V"
        self.current_price = 0
        self.previous_price = 0
        self.price_history = deque(maxlen=1000)
        self.candle_data = []
        self.ticks_data = []
        self.market_depth = {"bids": [], "asks": []}
        
        # ========== TECHNICAL INDICATORS ==========
        self.indicators = {
            "RSI": 50.0,
            "MACD": 0.0,
            "MACD_Signal": 0.0,
            "MACD_Histogram": 0.0,
            "BB_Upper": 0.0,
            "BB_Middle": 0.0,
            "BB_Lower": 0.0,
            "ATR": 0.0,
            "Stoch_K": 50.0,
            "Stoch_D": 50.0,
            "ADX": 25.0,
            "CCI": 0.0,
            "Williams_R": -50.0,
            "MFI": 50.0,
            "OBV": 0.0
        }
        
        # ========== AI / ML MODELS ==========
        self.ai_confidence = 0.0
        self.ai_prediction = None
        self.ai_patterns = []
        self.market_regime = "neutral"
        self.sentiment_score = 0.0
        self.volatility_regime = "normal"
        
        # ========== MARKET SCORING ==========
        self.market_score = 0
        self.max_score = 100
        self.score_components = {
            "trend_strength": 0,
            "momentum": 0,
            "volume_flow": 0,
            "volatility_optimal": 0,
            "pattern_match": 0,
            "rsi_optimal": 0,
            "macd_alignment": 0,
            "bb_position": 0,
            "ai_confidence": 0,
            "sentiment": 0
        }
        
        # ========== TRADING STRATEGIES ==========
        self.strategies = {
            "scalping": {"enabled": True, "weight": 0.25, "wins": 0, "losses": 0, "confidence": 0},
            "trend_following": {"enabled": True, "weight": 0.25, "wins": 0, "losses": 0, "confidence": 0},
            "mean_reversion": {"enabled": True, "weight": 0.25, "wins": 0, "losses": 0, "confidence": 0},
            "breakout": {"enabled": True, "weight": 0.25, "wins": 0, "losses": 0, "confidence": 0},
            "grid_trading": {"enabled": False, "weight": 0.10, "wins": 0, "losses": 0, "confidence": 0},
            "arbitrage": {"enabled": False, "weight": 0.10, "wins": 0, "losses": 0, "confidence": 0},
            "news_based": {"enabled": False, "weight": 0.05, "wins": 0, "losses": 0, "confidence": 0}
        }
        
        # ========== ACTIVE SIGNALS ==========
        self.active_signals = []
        self.signal_history = []
        self.current_edges = []
        
        # ========== RISK MANAGEMENT ==========
        self.risk_settings = {
            "max_risk_per_trade": 2.0,  # Percentage
            "max_daily_risk": 10.0,  # Percentage
            "max_drawdown": 15.0,  # Percentage
            "stop_loss_pct": 70.0,  # Percentage of position
            "take_profit_pct": 150.0,  # Percentage of position
            "max_consecutive_losses": 3,
            "daily_loss_limit": 100.0,
            "session_timeout_minutes": 0,
            "risk_reward_ratio": 2.0,
            "max_correlation": 0.7
        }
        
        # ========== POSITION SIZING ==========
        self.position_sizing = {
            "base_amount": 1.0,
            "dynamic_sizing": True,
            "kelly_fraction": 0.25,
            "max_position": 100.0,
            "min_position": 0.01
        }
        
        # ========== TRADING STATISTICS ==========
        self.stats = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_profit": 0.0,
            "total_loss": 0.0,
            "net_profit": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "largest_win": 0.0,
            "largest_loss": 0.0,
            "max_consecutive_wins": 0,
            "max_consecutive_losses": 0,
            "current_streak": 0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "calmar_ratio": 0.0,
            "expectancy": 0.0,
            "recovery_factor": 0.0,
            "avg_bars_in_trades": 0
        }
        
        # ========== SESSION DATA ==========
        self.session = {
            "start_time": datetime.now().isoformat(),
            "session_pnl": 0.0,
            "session_trades": 0,
            "session_wins": 0,
            "session_losses": 0,
            "session_high": 0.0,
            "session_low": 0.0,
            "session_drawdown": 0.0,
            "daily_target": 50.0,
            "daily_achieved": 0.0
        }
        
        # ========== ACTIVE TRADES ==========
        self.active_trades = {}
        self.trade_history = []
        self.order_book = []
        self.pending_orders = []
        
        # ========== BOT STATUS ==========
        self.bot_status = "STOPPED"  # STOPPED, ANALYZING, TRADING, PAUSED
        self.bot_mode = "AUTO"  # AUTO, MANUAL, HYBRID
        self.bot_speed = "NORMAL"  # SLOW, NORMAL, FAST, INSANE
        self.last_trade_time = None
        self.consecutive_losses = 0
        
        # ========== KILL SWITCH ==========
        self.kill_switch = {
            "armed": False,
            "triggered": False,
            "stop_loss": 100.0,
            "loss_streak": 3,
            "profit_target": 50.0,
            "drawdown_limit": 15.0
        }
        
        # ========== PATTERN RECOGNITION ==========
        self.patterns = {
            "double_top": False,
            "double_bottom": False,
            "head_shoulders": False,
            "triangle": False,
            "flag": False,
            "wedge": False,
            "gap": False,
            "doji": False,
            "hammer": False,
            "shooting_star": False,
            "engulfing": False,
            "morning_star": False,
            "evening_star": False
        }
        
        # ========== PATTERN ANALYSIS ==========
        self.last_20_digits = []
        self.even_odd_analysis = {"even": 0, "odd": 0, "streak": 0, "edge": 0}
        self.over_under_analysis = {"over": 0, "under": 0, "streak": 0, "edge": 0}
        self.streak_analysis = {"current": 0, "max": 0, "type": None}
        
        # ========== PERFORMANCE METRICS ==========
        self.performance = {
            "daily": {"pnl": 0.0, "trades": 0, "win_rate": 0.0},
            "weekly": {"pnl": 0.0, "trades": 0, "win_rate": 0.0},
            "monthly": {"pnl": 0.0, "trades": 0, "win_rate": 0.0},
            "all_time": {"pnl": 0.0, "trades": 0, "win_rate": 0.0}
        }
        
        # ========== NEWSLETTER / ALERTS ==========
        self.alerts = []
        self.notifications = []
        
        # ========== AUTOMATION SETTINGS ==========
        self.automation = {
            "auto_start": False,
            "auto_stop": True,
            "max_runtime_hours": 0,
            "scheduled_trades": [],
            "time_based_strategy": False
        }
        
        # ========== ADVANCED FEATURES ==========
        self.hedge_positions = []
        self.copytrading_enabled = False
        self.social_signals = []
        self.backtest_results = {}
    
    # ========== DERIV CONNECTION ==========
    async def connect_deriv(self):
        if not self.api_token:
            logger.error("No API token found!")
            return False
        
        url = f"wss://ws.binaryws.com/websockets/v3?app_id={self.app_id}"
        
        try:
            self.websocket = await websockets.connect(url)
            await self.websocket.send(json.dumps({"authorize": self.api_token}))
            response = await self.websocket.recv()
            auth_data = json.loads(response)
            
            if auth_data.get("error"):
                logger.error(f"Auth failed: {auth_data['error']['message']}")
                return False
            
            await self.update_balance()
            self.connected = True
            logger.info("Connected to Deriv successfully!")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def update_balance(self):
        try:
            await self.websocket.send(json.dumps({"balance": 1}))
            response = await self.websocket.recv()
            data = json.loads(response)
            if "balance" in data:
                self.current_balance = float(data["balance"]["balance"])
                self.currency = data["balance"]["currency"]
                if self.active_account == "demo":
                    self.accounts["demo"]["balance"] = self.current_balance
                else:
                    self.accounts["real"]["balance"] = self.current_balance
        except:
            pass
    
    async def subscribe_to_symbol(self):
        await self.websocket.send(json.dumps({"ticks": self.current_symbol, "subscribe": 1}))
        logger.info(f"Subscribed to {self.current_symbol}")
    
    # ========== ADVANCED MARKET ANALYSIS ==========
    def calculate_indicators(self):
        """Calculate all technical indicators"""
        prices = list(self.price_history)
        if len(prices) < 50:
            return
        
        # RSI Calculation
        gains = []
        losses = []
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
            else:
                losses.append(abs(change))
        
        avg_gain = sum(gains[-14:]) / 14 if gains else 0
        avg_loss = sum(losses[-14:]) / 14 if losses else 0
        if avg_loss > 0:
            rs = avg_gain / avg_loss
            self.indicators["RSI"] = 100 - (100 / (1 + rs))
        
        # MACD Calculation
        ema12 = self.calculate_ema(prices, 12)
        ema26 = self.calculate_ema(prices, 26)
        self.indicators["MACD"] = ema12 - ema26
        self.indicators["MACD_Signal"] = self.calculate_ema([self.indicators["MACD"]], 9) if len(prices) > 9 else 0
        self.indicators["MACD_Histogram"] = self.indicators["MACD"] - self.indicators["MACD_Signal"]
        
        # Bollinger Bands
        sma20 = sum(prices[-20:]) / 20
        std20 = np.std(prices[-20:]) if len(prices) >= 20 else 0
        self.indicators["BB_Middle"] = sma20
        self.indicators["BB_Upper"] = sma20 + (std20 * 2)
        self.indicators["BB_Lower"] = sma20 - (std20 * 2)
        
        # ATR
        tr_values = []
        for i in range(1, min(15, len(prices))):
            tr = max(prices[-i] - prices[-i-1], abs(prices[-i] - prices[-i-2]) if i > 1 else 0, abs(prices[-i-1] - prices[-i-2]) if i > 1 else 0)
            tr_values.append(tr)
        self.indicators["ATR"] = sum(tr_values) / len(tr_values) if tr_values else 0
        
        # Stochastic
        if len(prices) >= 14:
            low14 = min(prices[-14:])
            high14 = max(prices[-14:])
            if high14 != low14:
                self.indicators["Stoch_K"] = ((prices[-1] - low14) / (high14 - low14)) * 100
                self.indicators["Stoch_D"] = (self.indicators["Stoch_K"] + self.indicators["Stoch_K"]) / 2
        
        # CCI
        if len(prices) >= 20:
            tp = [(prices[i] + prices[i] + prices[i]) / 3 for i in range(-20, 0)]
            sma_tp = sum(tp) / 20
            mean_dev = sum(abs(t - sma_tp) for t in tp) / 20
            if mean_dev > 0:
                self.indicators["CCI"] = (tp[-1] - sma_tp) / (0.015 * mean_dev)
        
        # Williams %R
        if len(prices) >= 14:
            high14 = max(prices[-14:])
            low14 = min(prices[-14:])
            if high14 != low14:
                self.indicators["Williams_R"] = ((high14 - prices[-1]) / (high14 - low14)) * -100
        
        # MFI
        if len(prices) >= 14 and hasattr(self, 'volumes'):
            typical_prices = [(prices[i] + prices[i] + prices[i]) / 3 for i in range(-14, 0)]
            money_flows = [tp * v for tp, v in zip(typical_prices, self.volumes[-14:])] if hasattr(self, 'volumes') else [0] * 14
            positive_mf = sum(mf for mf in money_flows if money_flows[money_flows.index(mf)-1] < mf if money_flows.index(mf) > 0 else 0)
            negative_mf = sum(mf for mf in money_flows if money_flows[money_flows.index(mf)-1] > mf if money_flows.index(mf) > 0 else 0)
            if negative_mf > 0:
                mfr = positive_mf / negative_mf
                self.indicators["MFI"] = 100 - (100 / (1 + mfr))
    
    def calculate_ema(self, data, period):
        if len(data) < period:
            return data[-1] if data else 0
        alpha = 2 / (period + 1)
        ema = data[-period]
        for price in data[-period+1:]:
            ema = alpha * price + (1 - alpha) * ema
        return ema
    
    def calculate_market_score(self):
        """Advanced market scoring system"""
        score = 0
        
        # RSI Score
        if self.indicators["RSI"] < 30:
            score += 15
            self.score_components["rsi_optimal"] = 15
        elif self.indicators["RSI"] > 70:
            score += 15
            self.score_components["rsi_optimal"] = 15
        elif 40 <= self.indicators["RSI"] <= 60:
            score += 5
            self.score_components["rsi_optimal"] = 5
        
        # MACD Score
        if self.indicators["MACD"] > self.indicators["MACD_Signal"]:
            score += 10
            self.score_components["macd_alignment"] = 10
        
        # Bollinger Bands Score
        if self.current_price <= self.indicators["BB_Lower"]:
            score += 15
            self.score_components["bb_position"] = 15
        elif self.current_price >= self.indicators["BB_Upper"]:
            score += 15
            self.score_components["bb_position"] = 15
        
        # Trend Strength (ADX proxy)
        if self.indicators["ADX"] > 25:
            score += 10
            self.score_components["trend_strength"] = 10
        
        # Momentum
        if len(self.price_history) > 5:
            momentum = (self.current_price - list(self.price_history)[-5]) / list(self.price_history)[-5] * 100
            if abs(momentum) > 0.5:
                score += min(abs(momentum) * 5, 20)
                self.score_components["momentum"] = min(abs(momentum) * 5, 20)
        
        # Volatility
        if 0.001 < self.indicators["ATR"] / self.current_price < 0.01:
            score += 10
            self.score_components["volatility_optimal"] = 10
        
        # Pattern Recognition
        pattern_score = self.analyze_patterns()
        score += pattern_score
        self.score_components["pattern_match"] = pattern_score
        
        # AI Confidence
        if self.ai_confidence > 0:
            score += self.ai_confidence * 0.3
            self.score_components["ai_confidence"] = self.ai_confidence * 0.3
        
        self.market_score = min(int(score), 100)
        return self.market_score
    
    def analyze_patterns(self):
        """Recognize chart patterns"""
        prices = list(self.price_history)
        if len(prices) < 50:
            return 0
        
        score = 0
        self.patterns["double_top"] = self.detect_double_top(prices)
        self.patterns["double_bottom"] = self.detect_double_bottom(prices)
        self.patterns["head_shoulders"] = self.detect_head_shoulders(prices)
        self.patterns["triangle"] = self.detect_triangle(prices)
        
        if self.patterns["double_top"] or self.patterns["head_shoulders"]:
            score += 15
        if self.patterns["double_bottom"]:
            score += 15
        if self.patterns["triangle"]:
            score += 10
        
        return score
    
    def detect_double_top(self, prices):
        if len(prices) < 30:
            return False
        recent_highs = []
        for i in range(-30, -5):
            if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                recent_highs.append(prices[i])
        if len(recent_highs) >= 2:
            return abs(recent_highs[-1] - recent_highs[-2]) / recent_highs[-2] < 0.02
        return False
    
    def detect_double_bottom(self, prices):
        if len(prices) < 30:
            return False
        recent_lows = []
        for i in range(-30, -5):
            if prices[i] < prices[i-1] and prices[i] < prices[i+1]:
                recent_lows.append(prices[i])
        if len(recent_lows) >= 2:
            return abs(recent_lows[-1] - recent_lows[-2]) / recent_lows[-2] < 0.02
        return False
    
    def detect_head_shoulders(self, prices):
        if len(prices) < 40:
            return False
        peaks = []
        for i in range(-40, -5):
            if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                peaks.append(prices[i])
        if len(peaks) >= 3:
            return peaks[-2] > peaks[-1] and peaks[-2] > peaks[-3]
        return False
    
    def detect_triangle(self, prices):
        if len(prices) < 30:
            return False
        highs = [max(prices[i-5:i+1]) for i in range(-30, 0)]
        lows = [min(prices[i-5:i+1]) for i in range(-30, 0)]
        if len(highs) > 10 and len(lows) > 10:
            high_slope = (highs[-1] - highs[0]) / len(highs)
            low_slope = (lows[-1] - lows[0]) / len(lows)
            return high_slope < 0 and low_slope > 0
        return False
    
    def analyze_digit_patterns(self):
        """Analyze last digit patterns for edge detection"""
        prices = list(self.price_history)
        if len(prices) < 20:
            return
        
        # Last digits extraction
        self.last_20_digits = [int(str(p).split('.')[-1][:1]) if '.' in str(p) else int(p) % 10 for p in prices[-20:]]
        
        # Even/Odd analysis
        even_count = sum(1 for d in self.last_20_digits if d % 2 == 0)
        odd_count = 20 - even_count
        self.even_odd_analysis = {
            "even": even_count,
            "odd": odd_count,
            "streak": self.calculate_streak(self.last_20_digits, lambda x: x % 2 == 0),
            "edge": abs(even_count - odd_count)
        }
        
        # Over/Under analysis (above/below 5)
        over_count = sum(1 for d in self.last_20_digits if d > 4)
        under_count = 20 - over_count
        self.over_under_analysis = {
            "over": over_count,
            "under": under_count,
            "streak": self.calculate_streak(self.last_20_digits, lambda x: x > 4),
            "edge": abs(over_count - under_count)
        }
        
        # Streak analysis
        current_streak = 1
        max_streak = 1
        streak_type = None
        for i in range(1, len(self.last_20_digits)):
            if self.last_20_digits[i] == self.last_20_digits[i-1]:
                current_streak += 1
                if current_streak > max_streak:
                    max_streak = current_streak
                    streak_type = self.last_20_digits[i]
            else:
                current_streak = 1
        
        self.streak_analysis = {
            "current": current_streak,
            "max": max_streak,
            "type": streak_type,
            "edge": "high" if max_streak >= 4 else "medium" if max_streak >= 3 else "low"
        }
    
    def calculate_streak(self, data, condition):
        streak = 0
        max_streak = 0
        for item in data:
            if condition(item):
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0
        return max_streak
    
    def calculate_ai_confidence(self):
        """AI confidence based on multiple factors"""
        confidence = 50.0
        
        # Factor 1: Technical indicators alignment
        tech_score = 0
        if self.indicators["RSI"] < 30 or self.indicators["RSI"] > 70:
            tech_score += 20
        if self.indicators["MACD"] > self.indicators["MACD_Signal"]:
            tech_score += 15
        if self.current_price <= self.indicators["BB_Lower"] or self.current_price >= self.indicators["BB_Upper"]:
            tech_score += 20
        confidence += tech_score * 0.3
        
        # Factor 2: Pattern recognition
        pattern_score = sum(1 for v in self.patterns.values() if v) * 10
        confidence += pattern_score * 0.2
        
        # Factor 3: Digit patterns
        if self.even_odd_analysis["edge"] >= 4:
            confidence += 15
        if self.over_under_analysis["edge"] >= 4:
            confidence += 15
        
        # Factor 4: Market score
        confidence += self.market_score * 0.2
        
        # Factor 5: Recent performance
        if len(self.trade_history) > 10:
            recent_wins = sum(1 for t in self.trade_history[-10:] if t.get("profit", 0) > 0)
            confidence += (recent_wins / 10) * 20
        
        self.ai_confidence = min(confidence, 98)
        return self.ai_confidence
    
    def generate_trading_signal(self):
        """Generate high-confidence trading signals"""
        if self.bot_status != "RUNNING":
            return None
        
        # Calculate all metrics
        self.calculate_indicators()
        self.analyze_digit_patterns()
        self.calculate_market_score()
        ai_conf = self.calculate_ai_confidence()
        
        signal = None
        confidence = 0
        direction = None
        strategy_used = None
        reasons = []
        
        # Strategy 1: RSI Mean Reversion
        if self.strategies["mean_reversion"]["enabled"]:
            if self.indicators["RSI"] < 30:
                signal = "CALL"
                confidence = 70 + (30 - self.indicators["RSI"]) / 2
                strategy_used = "mean_reversion"
                reasons.append(f"RSI oversold: {self.indicators['RSI']:.1f}")
            elif self.indicators["RSI"] > 70:
                signal = "PUT"
                confidence = 70 + (self.indicators["RSI"] - 70) / 2
                strategy_used = "mean_reversion"
                reasons.append(f"RSI overbought: {self.indicators['RSI']:.1f}")
        
        # Strategy 2: Bollinger Bands
        if not signal and self.strategies["breakout"]["enabled"]:
            if self.current_price <= self.indicators["BB_Lower"]:
                signal = "CALL"
                confidence = 75
                strategy_used = "breakout"
                reasons.append("Price at lower Bollinger Band")
            elif self.current_price >= self.indicators["BB_Upper"]:
                signal = "PUT"
                confidence = 75
                strategy_used = "breakout"
                reasons.append("Price at upper Bollinger Band")
        
        # Strategy 3: MACD Momentum
        if not signal and self.strategies["trend_following"]["enabled"]:
            if self.indicators["MACD"] > self.indicators["MACD_Signal"] and self.indicators["MACD_Histogram"] > 0:
                signal = "CALL"
                confidence = 70
                strategy_used = "trend_following"
                reasons.append("MACD bullish crossover")
            elif self.indicators["MACD"] < self.indicators["MACD_Signal"] and self.indicators["MACD_Histogram"] < 0:
                signal = "PUT"
                confidence = 70
                strategy_used = "trend_following"
                reasons.append("MACD bearish crossover")
        
        # Strategy 4: Digit Pattern Edge
        if not signal and self.strategies["scalping"]["enabled"]:
            if self.even_odd_analysis["edge"] >= 5:
                if self.even_odd_analysis["even"] > self.even_odd_analysis["odd"]:
                    signal = "CALL"
                else:
                    signal = "PUT"
                confidence = 75
                strategy_used = "scalping"
                reasons.append(f"Even/Odd edge: {self.even_odd_analysis['even']}E/{self.even_odd_analysis['odd']}O")
        
        # Apply confidence boost from AI
        confidence = min(confidence * (ai_conf / 50), 98)
        
        # Check minimum confidence
        if confidence < 70:
            return None
        
        # Check market score
        if self.market_score < 60:
            return None
        
        # Check risk limits
        if self.consecutive_losses >= self.risk_settings["max_consecutive_losses"]:
            return None
        
        if self.session["session_pnl"] <= -self.kill_switch["stop_loss"]:
            return None
        
        if self.session["session_trades"] >= 50:
            return None
        
        # Calculate position size based on Kelly Criterion
        if self.position_sizing["dynamic_sizing"] and len(self.trade_history) > 20:
            win_rate = self.stats["win_rate"] / 100
            avg_win = self.stats["avg_win"]
            avg_loss = abs(self.stats["avg_loss"]) if self.stats["avg_loss"] != 0 else 1
            if avg_loss > 0:
                kelly = win_rate - ((1 - win_rate) / (avg_win / avg_loss)) if avg_win > 0 else 0
                position_multiplier = min(max(kelly * self.position_sizing["kelly_fraction"] * 10, 0.5), 2)
            else:
                position_multiplier = 1
        else:
            position_multiplier = 1
        
        amount = self.position_sizing["base_amount"] * position_multiplier
        amount = min(amount, self.position_sizing["max_position"])
        amount = max(amount, self.position_sizing["min_position"])
        
        return {
            "direction": signal,
            "confidence": round(confidence, 1),
            "strategy": strategy_used,
            "reasons": reasons,
            "amount": round(amount, 2),
            "ai_confidence": round(ai_conf, 1),
            "market_score": self.market_score,
            "indicators": {
                "rsi": round(self.indicators["RSI"], 1),
                "macd": round(self.indicators["MACD"], 4),
                "bb_position": round((self.current_price - self.indicators["BB_Lower"]) / (self.indicators["BB_Upper"] - self.indicators["BB_Lower"]) * 100, 1) if self.indicators["BB_Upper"] != self.indicators["BB_Lower"] else 50,
                "atr": round(self.indicators["ATR"], 4)
            }
        }
    
    async def execute_trade(self, signal):
        """Execute trade on Deriv"""
        trade_msg = {
            "buy": 1,
            "parameters": {
                "amount": signal["amount"],
                "basis": "stake",
                "contract_type": signal["direction"].lower(),
                "currency": self.currency,
                "duration": 2,
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
                    "amount": signal["amount"],
                    "confidence": signal["confidence"],
                    "strategy": signal["strategy"],
                    "entry_price": self.current_price,
                    "entry_time": datetime.now().isoformat(),
                    "reasons": signal["reasons"],
                    "indicators": signal["indicators"],
                    "status": "open"
                }
                self.active_trades[contract_id] = trade
                self.order_book.append(trade)
                self.last_trade_time = datetime.now()
                
                logger.info(f"🎯 TRADE: {signal['direction']} {self.current_symbol} | ${signal['amount']} | {signal['confidence']}% | {signal['strategy']}")
                
                asyncio.create_task(self.monitor_trade(contract_id, 120))
                return contract_id
        except Exception as e:
            logger.error(f"Trade error: {e}")
        return None
    
    async def monitor_trade(self, contract_id, seconds):
        """Monitor and close trade"""
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
            
            # Update statistics
            self.stats["total_trades"] += 1
            self.session["session_trades"] += 1
            self.session["session_pnl"] += profit
            self.stats["net_profit"] += profit
            
            if profit > 0:
                self.stats["winning_trades"] += 1
                self.session["session_wins"] += 1
                self.consecutive_losses = 0
                if profit > self.stats["largest_win"]:
                    self.stats["largest_win"] = profit
                logger.info(f"✅ WIN: +${profit:.2f}")
            else:
                self.stats["losing_trades"] += 1
                self.session["session_losses"] += 1
                self.consecutive_losses += 1
                if profit < self.stats["largest_loss"]:
                    self.stats["largest_loss"] = profit
                logger.info(f"❌ LOSS: ${profit:.2f}")
            
            # Update win rate
            if self.stats["total_trades"] > 0:
                self.stats["win_rate"] = (self.stats["winning_trades"] / self.stats["total_trades"]) * 100
            
            # Update averages
            wins = [t.get("profit", 0) for t in self.trade_history if t.get("profit", 0) > 0]
            losses = [t.get("profit", 0) for t in self.trade_history if t.get("profit", 0) < 0]
            self.stats["avg_win"] = sum(wins) / len(wins) if wins else 0
            self.stats["avg_loss"] = sum(losses) / len(losses) if losses else 0
            
            # Update strategy performance
            if contract_id in self.active_trades:
                trade = self.active_trades[contract_id]
                strategy = trade.get("strategy")
                if strategy in self.strategies:
                    if profit > 0:
                        self.strategies[strategy]["wins"] += 1
                    else:
                        self.strategies[strategy]["losses"] += 1
                    total = self.strategies[strategy]["wins"] + self.strategies[strategy]["losses"]
                    if total > 0:
                        self.strategies[strategy]["confidence"] = (self.strategies[strategy]["wins"] / total) * 100
                
                trade["profit"] = profit
                trade["exit_time"] = datetime.now().isoformat()
                trade["status"] = "closed"
                self.trade_history.append(trade)
                del self.active_trades[contract_id]
            
            # Check kill switch
            if self.kill_switch["armed"]:
                if self.session["session_pnl"] <= -self.kill_switch["stop_loss"]:
                    self.stop_bot("Stop loss triggered")
                elif self.consecutive_losses >= self.kill_switch["loss_streak"]:
                    self.stop_bot("Max consecutive losses reached")
                elif self.session["session_pnl"] >= self.kill_switch["profit_target"]:
                    self.stop_bot("Profit target achieved")
            
            await self.update_balance()
            
        except Exception as e:
            logger.error(f"Monitor error: {e}")
    
    async def process_tick(self, tick_data):
        symbol = tick_data.get("symbol")
        price = tick_data.get("quote")
        
        if not symbol or symbol != self.current_symbol:
            return
        
        self.previous_price = self.current_price
        self.current_price = float(price)
        self.price_history.append(self.current_price)
        self.ticks_data.append({"time": datetime.now(), "price": self.current_price})
        
        if len(self.price_history) > 1000:
            self.price_history = deque(list(self.price_history)[-500:])
        
        # Generate trading signal
        if self.bot_status == "RUNNING":
            signal = self.generate_trading_signal()
            if signal and len(self.active_trades) < 5:
                await self.execute_trade(signal)
        
        logger.info(f"{symbol}: ${self.current_price:.4f} | Score: {self.market_score}% | AI: {self.ai_confidence:.0f}% | RSI: {self.indicators['RSI']:.1f}")
    
    async def listen_for_prices(self):
        while self.connected:
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
        self.session["start_time"] = datetime.now().isoformat()
        logger.info("🚀 BOT STARTED - AI Trading Active")
    
    def stop_bot(self, reason="Manual"):
        self.bot_status = "STOPPED"
        logger.info(f"🛑 BOT STOPPED - Reason: {reason}")
    
    def switch_account(self, account_type):
        self.active_account = account_type
        self.current_balance = self.accounts[account_type]["balance"]
        logger.info(f"Switched to {account_type} account")
    
    def switch_symbol(self, symbol):
        if symbol in self.symbols:
            self.current_symbol = symbol
            self.price_history.clear()
            asyncio.create_task(self.subscribe_to_symbol())
            logger.info(f"Switched to {symbol}")
    
    def update_kill_switch(self, settings):
        self.kill_switch.update(settings)
    
    def get_full_state(self):
        return {
            # Account Info
            "connected": self.connected,
            "accounts": self.accounts,
            "active_account": self.active_account,
            "current_balance": self.current_balance,
            "currency": self.currency,
            
            # Bot Status
            "bot_status": self.bot_status,
            "bot_mode": self.bot_mode,
            "bot_speed": self.bot_speed,
            
            # Market
            "current_symbol": self.current_symbol,
            "current_price": self.current_price,
            "price_history": list(self.price_history)[-50:],
            
            # Indicators
            "indicators": self.indicators,
            
            # Market Score
            "market_score": self.market_score,
            "max_score": self.max_score,
            "score_components": self.score_components,
            
            # AI
            "ai_confidence": self.ai_confidence,
            "ai_prediction": self.ai_prediction,
            "market_regime": self.market_regime,
            
            # Patterns
            "patterns": self.patterns,
            "last_20_digits": self.last_20_digits,
            "even_odd_analysis": self.even_odd_analysis,
            "over_under_analysis": self.over_under_analysis,
            "streak_analysis": self.streak_analysis,
            
            # Strategies
            "strategies": self.strategies,
            "active_signals": self.active_signals,
            "current_edges": self.current_edges,
            
            # Statistics
            "stats": self.stats,
            "session": self.session,
            "performance": self.performance,
            
            # Risk
            "risk_settings": self.risk_settings,
            "position_sizing": self.position_sizing,
            "kill_switch": self.kill_switch,
            "consecutive_losses": self.consecutive_losses,
            
            # Trades
            "active_trades": list(self.active_trades.values()),
            "trade_history": self.trade_history[-50:],
            "total_active": len(self.active_trades),
            
            # Alerts
            "alerts": self.alerts[-10:]
        }

platform = UltimateTradingSystem()

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(platform.run())
    yield

app = FastAPI(lifespan=lifespan)

# ========== PROFESSIONAL HTML DASHBOARD ==========
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 SmartPip Ultimate | AI-Powered Trading Platform</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0a0e27; color: #e2e8f0; overflow-x: hidden; }
        
        /* Header */
        .header { background: linear-gradient(135deg, #0f1235, #1a1f4e); padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2d3748; position: sticky; top: 0; z-index: 100; }
        .logo { font-size: 24px; font-weight: bold; background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .account-badge { display: flex; gap: 10px; }
        .account-btn { padding: 8px 20px; border-radius: 8px; cursor: pointer; background: #1a1f4e; border: 1px solid #2d3748; color: #94a3b8; transition: all 0.3s; }
        .account-btn.active { background: linear-gradient(135deg, #667eea, #764ba2); color: white; border-color: transparent; }
        .balance-card { background: rgba(16,185,129,0.1); padding: 8px 20px; border-radius: 12px; border: 1px solid rgba(16,185,129,0.3); text-align: center; }
        .balance-value { font-size: 24px; font-weight: bold; color: #10b981; }
        
        /* Main Grid */
        .main-grid { display: grid; grid-template-columns: 300px 1fr 320px; gap: 20px; padding: 20px; max-width: 1600px; margin: 0 auto; }
        
        /* Panels */
        .panel { background: #0f1235; border-radius: 16px; border: 1px solid #2d3748; overflow: hidden; }
        .panel-header { padding: 15px 20px; background: #1a1f4e; font-weight: bold; font-size: 14px; border-bottom: 1px solid #2d3748; }
        .panel-content { padding: 20px; }
        
        /* Market Card */
        .market-card { background: linear-gradient(135deg, #1a1f4e, #0f1235); border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 20px; border: 1px solid #2d3748; }
        .market-symbol { font-size: 20px; font-weight: bold; color: #667eea; }
        .market-price { font-size: 36px; font-weight: bold; margin: 10px 0; }
        .market-change { font-size: 14px; }
        .status-badge { display: inline-block; padding: 5px 15px; border-radius: 20px; font-size: 12px; font-weight: bold; }
        .status-running { background: #10b981; color: white; animation: pulse 2s infinite; }
        .status-stopped { background: #ef4444; color: white; }
        
        /* Score Display */
        .score-circle { width: 120px; height: 120px; margin: 0 auto 20px; position: relative; }
        .score-value { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 32px; font-weight: bold; }
        .score-label { text-align: center; font-size: 12px; color: #94a3b8; margin-top: 10px; }
        
        /* Buttons */
        .btn-start { background: linear-gradient(135deg, #10b981, #059669); color: white; border: none; padding: 12px 24px; border-radius: 10px; font-weight: bold; cursor: pointer; margin-right: 10px; }
        .btn-stop { background: linear-gradient(135deg, #ef4444, #dc2626); color: white; border: none; padding: 12px 24px; border-radius: 10px; font-weight: bold; cursor: pointer; }
        .btn-manual { background: #1a1f4e; border: 1px solid #667eea; color: #667eea; padding: 8px 16px; border-radius: 8px; cursor: pointer; }
        
        /* Stats Grid */
        .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }
        .stat-card { background: #1a1f4e; padding: 12px; border-radius: 10px; text-align: center; }
        .stat-label { font-size: 11px; color: #94a3b8; margin-bottom: 5px; }
        .stat-value { font-size: 18px; font-weight: bold; }
        
        /* Indicators */
        .indicator-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #2d3748; }
        .indicator-label { color: #94a3b8; }
        .indicator-value { font-weight: bold; }
        
        /* Digits */
        .digits-container { background: #1a1f4e; border-radius: 12px; padding: 15px; margin-bottom: 20px; }
        .digits-row { display: flex; gap: 8px; flex-wrap: wrap; margin: 10px 0; }
        .digit { width: 35px; height: 35px; background: #0f1235; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 1px solid #2d3748; }
        
        /* Trade Log */
        .trade-log { max-height: 400px; overflow-y: auto; }
        .trade-item { background: #1a1f4e; padding: 10px; border-radius: 8px; margin-bottom: 8px; border-left: 3px solid; font-size: 12px; }
        .trade-win { border-left-color: #10b981; }
        .trade-loss { border-left-color: #ef4444; }
        
        /* Strategy Cards */
        .strategy-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px; }
        .strategy-card { background: #1a1f4e; padding: 10px; border-radius: 8px; text-align: center; }
        .strategy-name { font-size: 11px; color: #94a3b8; }
        .strategy-winrate { font-size: 16px; font-weight: bold; color: #10b981; }
        
        /* Symbol Selector */
        .symbol-selector { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; }
        .symbol-btn { background: #1a1f4e; border: 1px solid #2d3748; color: #94a3b8; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 11px; }
        .symbol-btn.active { background: linear-gradient(135deg, #667eea, #764ba2); color: white; }
        
        /* Kill Switch */
        .kill-switch { background: #1a1f4e; border-radius: 12px; padding: 15px; margin-top: 20px; }
        .switch-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .toggle { position: relative; width: 50px; height: 24px; }
        .toggle input { opacity: 0; width: 0; height: 0; }
        .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background: #4a5568; transition: 0.3s; border-radius: 24px; }
        .slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background: white; transition: 0.3s; border-radius: 50%; }
        input:checked + .slider { background: #667eea; }
        input:checked + .slider:before { transform: translateX(26px); }
        
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }
        .positive { color: #10b981; }
        .negative { color: #ef4444; }
        
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #1a1f4e; }
        ::-webkit-scrollbar-thumb { background: #667eea; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">🚀 SMARTPIP ULTIMATE | AI-POWERED TRADING</div>
        <div class="account-badge" id="accountBadge">
            <button class="account-btn active" onclick="switchAccount('demo')">DEMO</button>
            <button class="account-btn" onclick="switchAccount('real')">REAL</button>
        </div>
        <div class="balance-card">
            <div style="font-size:11px;">Balance</div>
            <div class="balance-value" id="balance">$0.00</div>
        </div>
    </div>
    
    <div class="main-grid">
        <!-- LEFT PANEL - MARKET & TRADING -->
        <div class="panel">
            <div class="panel-header">📊 MARKET & TRADING</div>
            <div class="panel-content">
                <div class="market-card">
                    <div class="market-symbol" id="symbol">1HZ10V</div>
                    <div class="market-price" id="price">$0.00</div>
                    <div class="market-change" id="change">+0.00%</div>
                    <div style="margin-top:10px;"><span class="status-badge" id="status">STOPPED</span></div>
                </div>
                
                <div class="symbol-selector" id="symbolSelector"></div>
                
                <div style="text-align:center; margin-bottom:20px;">
                    <canvas id="marketScoreChart" width="100" height="100" style="width:100px;height:100px;"></canvas>
                    <div class="score-label">Market Score | Need ≥70%</div>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card"><div class="stat-label">AI Confidence</div><div class="stat-value" id="aiConfidence">0%</div></div>
                    <div class="stat-card"><div class="stat-label">Market Regime</div><div class="stat-value" id="marketRegime">neutral</div></div>
                    <div class="stat-card"><div class="stat-label">Session P&L</div><div class="stat-value" id="sessionPnl">$0.00</div></div>
                    <div class="stat-card"><div class="stat-label">Trades Today</div><div class="stat-value" id="tradeCount">0</div></div>
                </div>
                
                <div style="display:flex; gap:10px;">
                    <button class="btn-start" onclick="startBot()">▶ START ENGINE</button>
                    <button class="btn-stop" onclick="stopBot()">⏹ STOP ENGINE</button>
                </div>
                
                <div class="kill-switch">
                    <div class="switch-header">
                        <span>🛡 SMART KILL-SWITCH</span>
                        <label class="toggle">
                            <input type="checkbox" id="killSwitch" onchange="toggleKillSwitch()">
                            <span class="slider"></span>
                        </label>
                    </div>
                    <div style="font-size:11px;">
                        Stop: $<span id="stopLoss">100</span> | Loss Streak: <span id="lossStreak">0/3</span> | Target: $<span id="profitTarget">50</span>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- CENTER PANEL - AI ANALYSIS & SIGNALS -->
        <div class="panel">
            <div class="panel-header">🧠 AI MARKET ANALYSIS</div>
            <div class="panel-content">
                <div class="stats-grid">
                    <div class="stat-card"><div class="stat-label">RSI</div><div class="stat-value" id="rsi">50.0</div></div>
                    <div class="stat-card"><div class="stat-label">MACD</div><div class="stat-value" id="macd">0.00</div></div>
                    <div class="stat-card"><div class="stat-label">Bollinger</div><div class="stat-value" id="bb">50%</div></div>
                    <div class="stat-card"><div class="stat-label">ATR</div><div class="stat-value" id="atr">0.00</div></div>
                </div>
                
                <div class="indicator-row"><span class="indicator-label">Trend Strength</span><span class="indicator-value" id="trendStrength">0%</span></div>
                <div class="indicator-row"><span class="indicator-label">Momentum</span><span class="indicator-value" id="momentum">0%</span></div>
                <div class="indicator-row"><span class="indicator-label">Volatility</span><span class="indicator-value" id="volatility">0%</span></div>
                <div class="indicator-row"><span class="indicator-label">Pattern Match</span><span class="indicator-value" id="patternMatch">0%</span></div>
                
                <div class="digits-container">
                    <div style="font-size:12px; margin-bottom:10px;">🎯 PATTERN EDGE ANALYSIS</div>
                    <div class="digits-row" id="digitsRow"></div>
                    <div style="font-size:11px; margin-top:10px;">
                        Even/Odd: <strong id="evenOdd">0E/0O</strong> | Edge: <span id="evenOddEdge">0</span><br>
                        Over/Under: <strong id="overUnder">0O/0U</strong> | Edge: <span id="overUnderEdge">0</span><br>
                        Streak: <strong id="streak">0</strong> x <span id="streakType">-</span>
                    </div>
                </div>
                
                <div class="strategy-grid">
                    <div class="strategy-card"><div class="strategy-name">📈 Scalping</div><div class="strategy-winrate" id="scalpingWR">0%</div></div>
                    <div class="strategy-card"><div class="strategy-name">📊 Trend Follow</div><div class="strategy-winrate" id="trendWR">0%</div></div>
                    <div class="strategy-card"><div class="strategy-name">🔄 Mean Rev</div><div class="strategy-winrate" id="meanrevWR">0%</div></div>
                    <div class="strategy-card"><div class="strategy-name">💥 Breakout</div><div class="strategy-winrate" id="breakoutWR">0%</div></div>
                </div>
                
                <div id="activeSignals" style="background:#1a1f4e; border-radius:8px; padding:10px; margin-top:10px;">
                    <div style="font-size:11px; color:#94a3b8;">🎯 ACTIVE SIGNALS</div>
                    <div id="signalsList">No active signals</div>
                </div>
            </div>
        </div>
        
        <!-- RIGHT PANEL - PORTFOLIO & TRADES -->
        <div class="panel">
            <div class="panel-header">💰 PORTFOLIO | WIN/LOSS</div>
            <div class="panel-content">
                <div class="stats-grid">
                    <div class="stat-card"><div class="stat-label">Win Rate</div><div class="stat-value" id="winRate">0%</div></div>
                    <div class="stat-card"><div class="stat-label">Profit Factor</div><div class="stat-value" id="profitFactor">0.00</div></div>
                    <div class="stat-card"><div class="stat-label">Total P&L</div><div class="stat-value" id="totalPnl">$0.00</div></div>
                    <div class="stat-card"><div class="stat-label">Active Trades</div><div class="stat-value" id="activeTrades">0</div></div>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card"><div class="stat-label">Wins</div><div class="stat-value" id="wins">0</div></div>
                    <div class="stat-card"><div class="stat-label">Losses</div><div class="stat-value" id="losses">0</div></div>
                    <div class="stat-card"><div class="stat-label">Avg Win</div><div class="stat-value" id="avgWin">$0.00</div></div>
                    <div class="stat-card"><div class="stat-label">Avg Loss</div><div class="stat-value" id="avgLoss">$0.00</div></div>
                </div>
                
                <div style="margin:15px 0;">
                    <button class="btn-manual" onclick="manualCall()">📈 MANUAL CALL</button>
                    <button class="btn-manual" onclick="manualPut()">📉 MANUAL PUT</button>
                </div>
                
                <div class="panel-header" style="margin:0 -20px 10px -20px; padding:10px 20px;">📋 TRADE LOG</div>
                <div class="trade-log" id="tradeLog">
                    <div style="text-align:center; padding:20px;">No trades yet</div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let ws = null;
        let scoreChart = null;
        
        function connectWebSocket() {
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${location.host}/ws`);
            ws.onmessage = (event) => { const data = JSON.parse(event.data); updateDashboard(data); };
            ws.onclose = () => setTimeout(connectWebSocket, 3000);
        }
        
        function updateDashboard(data) {
            // Balance & Account
            document.getElementById('balance').innerHTML = `${data.currency || '$'}${(data.current_balance || 0).toFixed(2)}`;
            document.getElementById('price').innerHTML = `${data.currency || '$'}${(data.current_price || 0).toFixed(4)}`;
            document.getElementById('status').innerHTML = data.bot_status || 'STOPPED';
            document.getElementById('status').className = `status-badge status-${(data.bot_status || 'stopped').toLowerCase()}`;
            
            // AI & Market
            document.getElementById('aiConfidence').innerHTML = `${(data.ai_confidence || 0).toFixed(0)}%`;
            document.getElementById('marketRegime').innerHTML = data.market_regime || 'neutral';
            document.getElementById('sessionPnl').innerHTML = `${(data.session?.session_pnl || 0) >= 0 ? '+' : ''}${data.currency || '$'}${(data.session?.session_pnl || 0).toFixed(2)}`;
            document.getElementById('tradeCount').innerHTML = data.session?.session_trades || 0;
            
            // Indicators
            document.getElementById('rsi').innerHTML = (data.indicators?.RSI || 50).toFixed(1);
            document.getElementById('macd').innerHTML = (data.indicators?.MACD || 0).toFixed(4);
            document.getElementById('bb').innerHTML = (data.indicators?.BB_Upper && data.indicators?.BB_Lower ? 
                ((data.current_price - data.indicators.BB_Lower) / (data.indicators.BB_Upper - data.indicators.BB_Lower) * 100).toFixed(0) : 50) + '%';
            document.getElementById('atr').innerHTML = (data.indicators?.ATR || 0).toFixed(4);
            
            // Score components
            if (data.score_components) {
                document.getElementById('trendStrength').innerHTML = (data.score_components.trend_strength || 0) + '%';
                document.getElementById('momentum').innerHTML = (data.score_components.momentum || 0) + '%';
                document.getElementById('volatility').innerHTML = (data.score_components.volatility_optimal || 0) + '%';
                document.getElementById('patternMatch').innerHTML = (data.score_components.pattern_match || 0) + '%';
            }
            
            // Market Score Chart
            if (data.market_score !== undefined) {
                if (scoreChart) { scoreChart.destroy(); }
                const ctx = document.getElementById('marketScoreChart').getContext('2d');
                scoreChart = new Chart(ctx, {
                    type: 'doughnut',
                    data: { datasets: [{ data: [data.market_score, 100 - data.market_score], backgroundColor: ['#667eea', '#2d3748'], borderWidth: 0 }] },
                    options: { cutout: '70%', plugins: { tooltip: { enabled: false }, legend: { display: false } } }
                });
                document.getElementById('marketScoreChart').parentElement.querySelector('.score-label').innerHTML = `Market Score: ${data.market_score}% | Need ≥70%`;
            }
            
            // Digits & Patterns
            if (data.last_20_digits) {
                const digitsRow = document.getElementById('digitsRow');
                digitsRow.innerHTML = data.last_20_digits.slice(-10).map(d => `<div class="digit">${d}</div>`).join('');
            }
            if (data.even_odd_analysis) {
                document.getElementById('evenOdd').innerHTML = `${data.even_odd_analysis.even || 0}E / ${data.even_odd_analysis.odd || 0}O`;
                document.getElementById('evenOddEdge').innerHTML = data.even_odd_analysis.edge || 0;
                document.getElementById('overUnder').innerHTML = `${data.over_under_analysis.over || 0}O / ${data.over_under_analysis.under || 0}U`;
                document.getElementById('overUnderEdge').innerHTML = data.over_under_analysis.edge || 0;
                document.getElementById('streak').innerHTML = data.streak_analysis?.current || 0;
                document.getElementById('streakType').innerHTML = data.streak_analysis?.type || '-';
            }
            
            // Strategy Performance
            if (data.strategies) {
                document.getElementById('scalpingWR').innerHTML = `${(data.strategies.scalping?.confidence || 0).toFixed(0)}%`;
                document.getElementById('trendWR').innerHTML = `${(data.strategies.trend_following?.confidence || 0).toFixed(0)}%`;
                document.getElementById('meanrevWR').innerHTML = `${(data.strategies.mean_reversion?.confidence || 0).toFixed(0)}%`;
                document.getElementById('breakoutWR').innerHTML = `${(data.strategies.breakout?.confidence || 0).toFixed(0)}%`;
            }
            
            // Statistics
            document.getElementById('winRate').innerHTML = `${(data.stats?.win_rate || 0).toFixed(0)}%`;
            document.getElementById('profitFactor').innerHTML = (data.stats?.profit_factor || 0).toFixed(2);
            document.getElementById('totalPnl').innerHTML = `${(data.stats?.net_profit || 0) >= 0 ? '+' : ''}${data.currency || '$'}${(data.stats?.net_profit || 0).toFixed(2)}`;
            document.getElementById('activeTrades').innerHTML = data.total_active || 0;
            document.getElementById('wins').innerHTML = data.stats?.winning_trades || 0;
            document.getElementById('losses').innerHTML = data.stats?.losing_trades || 0;
            document.getElementById('avgWin').innerHTML = `${data.currency || '$'}${(data.stats?.avg_win || 0).toFixed(2)}`;
            document.getElementById('avgLoss').innerHTML = `${data.currency || '$'}${(data.stats?.avg_loss || 0).toFixed(2)}`;
            
            // Trade Log
            if (data.trade_history && data.trade_history.length > 0) {
                const logContainer = document.getElementById('tradeLog');
                logContainer.innerHTML = data.trade_history.slice().reverse().map(trade => `
                    <div class="trade-item ${trade.profit > 0 ? 'trade-win' : trade.profit < 0 ? 'trade-loss' : ''}">
                        <div>${new Date(trade.entry_time).toLocaleTimeString()} | ${trade.symbol} | ${trade.direction}</div>
                        <div>Amount: ${data.currency || '$'}${trade.amount} | ${trade.profit > 0 ? '+' : ''}${data.currency || '$'}${(trade.profit || 0).toFixed(2)}</div>
                        <div>Confidence: ${trade.confidence}% | Strategy: ${trade.strategy}</div>
                    </div>
                `).join('');
            }
            
            // Kill Switch
            if (data.kill_switch) {
                document.getElementById('stopLoss').innerHTML = data.kill_switch.stop_loss || 100;
                document.getElementById('lossStreak').innerHTML = `${data.consecutive_losses || 0}/${data.kill_switch.loss_streak || 3}`;
                document.getElementById('profitTarget').innerHTML = data.kill_switch.profit_target || 50;
            }
            
            // Symbols
            if (data.symbols) {
                const selector = document.getElementById('symbolSelector');
                selector.innerHTML = Object.keys(data.symbols).map(s => 
                    `<button class="symbol-btn ${s === data.current_symbol ? 'active' : ''}" onclick="switchSymbol('${s}')">${s}</button>`
                ).join('');
            }
        }
        
        function startBot() { fetch('/api/start', { method: 'POST' }); }
        function stopBot() { fetch('/api/stop', { method: 'POST' }); }
        function switchAccount(type) { fetch('/api/switch_account', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ account_type: type }) }); }
        function switchSymbol(symbol) { fetch('/api/switch_symbol', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ symbol }) }); }
        function toggleKillSwitch() { const enabled = document.getElementById('killSwitch').checked; fetch('/api/kill_switch', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ enabled }) }); }
        function manualCall() { manualTrade('CALL'); }
        function manualPut() { manualTrade('PUT'); }
        function manualTrade(direction) { const amount = prompt('Enter amount:', '1'); if(amount) { fetch('/api/manual_trade', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ direction, amount: parseFloat(amount), duration: 2 }) }); } }
        
        connectWebSocket();
        setInterval(() => { fetch('/api/status').then(res => res.json()).then(data => updateDashboard(data)); }, 2000);
    </script>
</body>
</html>'''

@app.get("/")
async def root():
    return HTMLResponse(HTML_TEMPLATE)

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

@app.post("/api/switch_account")
async def switch_account(request: Request):
    data = await request.json()
    platform.switch_account(data.get("account_type"))
    return JSONResponse({"success": True})

@app.post("/api/switch_symbol")
async def switch_symbol(request: Request):
    data = await request.json()
    platform.switch_symbol(data.get("symbol"))
    return JSONResponse({"success": True})

@app.post("/api/kill_switch")
async def kill_switch(request: Request):
    data = await request.json()
    platform.update_kill_switch({"armed": data.get("enabled", False)})
    return JSONResponse({"success": True})

@app.post("/api/manual_trade")
async def manual_trade(request: Request):
    data = await request.json()
    signal = {"direction": data.get("direction"), "amount": data.get("amount"), "strategy": "manual", "confidence": 100, "reasons": ["Manual trade"]}
    result = await platform.execute_trade(signal)
    return JSONResponse({"success": result is not None})

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