# main.py - ULTIMATE INTELLIGENT TRADING SYSTEM
import os
import json
import asyncio
import random
import math
import hashlib
from datetime import datetime, timedelta
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any
from collections import deque
import logging
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketType(Enum):
    VOLATILITY = "volatility"
    RISE_FALL = "rise_fall"
    EVEN_ODD = "even_odd"
    OVER_UNDER = "over_under"
    MATCH_DIFF = "match_diff"
    DIGITS = "digits"

class UltimateIntelligentSystem:
    def __init__(self):
        # ========== CONNECTION ==========
        self.websocket = None
        self.connected = False
        self.api_token = os.getenv("DERIV_API_TOKEN")
        self.app_id = os.getenv("DERIV_APP_ID", "1089")
        
        # ========== ACCOUNTS ==========
        self.accounts = {
            "demo": {"balance": 10000.00, "initial": 10000.00, "pnl": 0.00},
            "real": {"balance": 0.00, "initial": 0.00, "pnl": 0.00}
        }
        self.active_account = "demo"
        self.current_balance = 10000.00
        self.currency = "USD"
        
        # ========== MARKETS ==========
        self.markets = {
            "R_10": {"type": MarketType.VOLATILITY, "volatility": "low", "spread": 0.001},
            "R_25": {"type": MarketType.VOLATILITY, "volatility": "medium", "spread": 0.002},
            "R_50": {"type": MarketType.VOLATILITY, "volatility": "high", "spread": 0.003},
            "R_75": {"type": MarketType.VOLATILITY, "volatility": "very_high", "spread": 0.004},
            "R_100": {"type": MarketType.VOLATILITY, "volatility": "extreme", "spread": 0.005},
            "1HZ10V": {"type": MarketType.VOLATILITY, "volatility": "synthetic", "spread": 0.001}
        }
        self.current_market = "R_100"
        self.current_price = 0
        self.price_history = deque(maxlen=500)
        
        # ========== ANALYSIS MODELS ==========
        self.models = {
            "even_odd": {"enabled": True, "confidence": 0, "predictions": []},
            "rise_fall": {"enabled": True, "confidence": 0, "predictions": []},
            "over_3_under_7": {"enabled": True, "confidence": 0, "predictions": []},
            "match_diff": {"enabled": True, "confidence": 0, "predictions": []},
            "digit_analysis": {"enabled": True, "confidence": 0, "predictions": []},
            "pattern_recognition": {"enabled": True, "confidence": 0, "predictions": []},
            "volatility_analysis": {"enabled": True, "confidence": 0, "predictions": []}
        }
        
        # ========== DIGIT ANALYSIS ==========
        self.digit_history = deque(maxlen=100)
        self.last_20_digits = []
        self.digit_frequencies = {i: 0 for i in range(10)}
        self.digit_predictions = {}
        
        # Even/Odd Analysis
        self.even_odd = {
            "even_count": 0,
            "odd_count": 0,
            "even_streak": 0,
            "odd_streak": 0,
            "prediction": None,
            "confidence": 0,
            "edge": 0
        }
        
        # Rise/Fall Analysis (price direction)
        self.rise_fall = {
            "rise_count": 0,
            "fall_count": 0,
            "rise_streak": 0,
            "fall_streak": 0,
            "prediction": None,
            "confidence": 0,
            "momentum": 0
        }
        
        # Over 3 / Under 7 Analysis
        self.over_under = {
            "over_3_count": 0,
            "under_7_count": 0,
            "between_3_7": 0,
            "prediction": None,
            "confidence": 0,
            "edge": 0
        }
        
        # Match & Differ Analysis
        self.match_diff = {
            "match_count": 0,
            "diff_count": 0,
            "match_streak": 0,
            "diff_streak": 0,
            "prediction": None,
            "confidence": 0,
            "last_match": None
        }
        
        # ========== MULTI-MARKET ANALYSIS ==========
        self.market_correlations = {}
        self.arbitrage_opportunities = []
        self.best_market = None
        self.market_scores = {}
        
        # ========== TRADING SETTINGS ==========
        self.settings = {
            "base_amount": 1.0,
            "auto_trading": False,
            "max_trades_per_hour": 10,
            "min_confidence": 70,
            "stop_loss": 50.0,
            "take_profit": 100.0,
            "max_consecutive_losses": 3,
            "enable_even_odd": True,
            "enable_rise_fall": True,
            "enable_over_under": True,
            "enable_match_diff": True,
            "enable_digit_analysis": True,
            "enable_foreign_bot": False,
            "foreign_bot_endpoint": "",
            "foreign_bot_api_key": ""
        }
        
        # ========== TRADING STATS ==========
        self.stats = {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0,
            "total_profit": 0,
            "session_pnl": 0,
            "best_trade": 0,
            "worst_trade": 0,
            "avg_win": 0,
            "avg_loss": 0
        }
        
        # ========== BOT STATUS ==========
        self.bot_status = "STOPPED"
        self.active_trades = {}
        self.trade_history = []
        self.consecutive_losses = 0
        self.analysis_result = {}
        self.best_prediction = None
        self.trade_signals = []
        
        # ========== KILL SWITCH ==========
        self.kill_switch = {"armed": True, "stop_loss": 50, "max_losses": 3}
    
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
            logger.info("Connected to Deriv!")
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
                self.accounts[self.active_account]["balance"] = self.current_balance
        except:
            pass
    
    async def subscribe_to_market(self):
        await self.websocket.send(json.dumps({"ticks": self.current_market, "subscribe": 1}))
        logger.info(f"Subscribed to {self.current_market}")
    
    # ========== INTELLIGENT ANALYSIS MODELS ==========
    
    def analyze_even_odd(self):
        """Analyze Even/Odd patterns with advanced statistics"""
        if len(self.last_20_digits) < 20:
            return
        
        evens = sum(1 for d in self.last_20_digits if d % 2 == 0)
        odds = 20 - evens
        
        # Calculate streaks
        current_streak = 1
        for i in range(len(self.last_20_digits)-1, 0, -1):
            if (self.last_20_digits[i] % 2) == (self.last_20_digits[i-1] % 2):
                current_streak += 1
            else:
                break
        
        # Prediction logic
        confidence = 50
        prediction = None
        
        if evens > odds + 4:
            confidence = 60 + (evens - odds) * 2
            prediction = "ODD"  # Mean reversion
        elif odds > evens + 4:
            confidence = 60 + (odds - evens) * 2
            prediction = "EVEN"  # Mean reversion
        elif current_streak >= 4:
            # Streak reversal
            current_type = "EVEN" if self.last_20_digits[-1] % 2 == 0 else "ODD"
            prediction = "ODD" if current_type == "EVEN" else "EVEN"
            confidence = 65 + min(current_streak * 2, 25)
        else:
            # Random walk - slight edge to majority
            if evens > odds:
                prediction = "EVEN"
                confidence = 55
            else:
                prediction = "ODD"
                confidence = 55
        
        self.even_odd = {
            "even_count": evens,
            "odd_count": odds,
            "even_streak": self.calculate_streak(0),
            "odd_streak": self.calculate_streak(1),
            "prediction": prediction,
            "confidence": min(confidence, 95),
            "edge": abs(evens - odds)
        }
        
        return self.even_odd
    
    def analyze_rise_fall(self):
        """Analyze price direction for Rise/Fall predictions"""
        if len(self.price_history) < 30:
            return
        
        prices = list(self.price_history)
        rises = 0
        falls = 0
        
        for i in range(1, len(prices)):
            if prices[i] > prices[i-1]:
                rises += 1
            elif prices[i] < prices[i-1]:
                falls += 1
        
        # Calculate momentum
        recent_changes = [prices[i] - prices[i-1] for i in range(-20, 0)]
        momentum = sum(recent_changes) / len(recent_changes) if recent_changes else 0
        
        # Calculate streaks
        rise_streak = 0
        fall_streak = 0
        for i in range(len(prices)-1, 0, -1):
            if prices[i] > prices[i-1]:
                rise_streak += 1
                fall_streak = 0
            elif prices[i] < prices[i-1]:
                fall_streak += 1
                rise_streak = 0
            else:
                break
        
        # Prediction
        confidence = 50
        prediction = None
        
        if momentum > 0.001:
            prediction = "RISE"
            confidence = 60 + min(momentum * 1000, 30)
        elif momentum < -0.001:
            prediction = "FALL"
            confidence = 60 + min(abs(momentum) * 1000, 30)
        elif rise_streak >= 3:
            prediction = "FALL"  # Reversal
            confidence = 65 + min(rise_streak * 3, 25)
        elif fall_streak >= 3:
            prediction = "RISE"  # Reversal
            confidence = 65 + min(fall_streak * 3, 25)
        else:
            # Use majority
            if rises > falls:
                prediction = "RISE"
                confidence = 55
            else:
                prediction = "FALL"
                confidence = 55
        
        self.rise_fall = {
            "rise_count": rises,
            "fall_count": falls,
            "rise_streak": rise_streak,
            "fall_streak": fall_streak,
            "prediction": prediction,
            "confidence": min(confidence, 95),
            "momentum": momentum
        }
        
        return self.rise_fall
    
    def analyze_over_under(self):
        """Analyze Over 3 / Under 7 patterns"""
        if len(self.last_20_digits) < 20:
            return
        
        over_3 = sum(1 for d in self.last_20_digits if d > 3)
        under_7 = sum(1 for d in self.last_20_digits if d < 7)
        between = sum(1 for d in self.last_20_digits if 3 <= d <= 7)
        
        prediction = None
        confidence = 50
        
        if over_3 > under_7 + 5:
            prediction = "UNDER_7"
            confidence = 65 + (over_3 - under_7)
        elif under_7 > over_3 + 5:
            prediction = "OVER_3"
            confidence = 65 + (under_7 - over_3)
        else:
            # Check for streaks
            streak = self.calculate_streak(lambda x: x > 3)
            if streak >= 4:
                prediction = "UNDER_7"
                confidence = 70
            else:
                streak = self.calculate_streak(lambda x: x < 7)
                if streak >= 4:
                    prediction = "OVER_3"
                    confidence = 70
        
        self.over_under = {
            "over_3_count": over_3,
            "under_7_count": under_7,
            "between_3_7": between,
            "prediction": prediction,
            "confidence": min(confidence, 95),
            "edge": abs(over_3 - under_7)
        }
        
        return self.over_under
    
    def analyze_match_diff(self):
        """Analyze Match and Differ patterns"""
        if len(self.last_20_digits) < 20:
            return
        
        matches = 0
        diffs = 0
        
        for i in range(1, len(self.last_20_digits)):
            if self.last_20_digits[i] == self.last_20_digits[i-1]:
                matches += 1
            else:
                diffs += 1
        
        # Current streak
        current_streak = 1
        for i in range(len(self.last_20_digits)-1, 0, -1):
            if self.last_20_digits[i] == self.last_20_digits[i-1]:
                current_streak += 1
            else:
                break
        
        prediction = None
        confidence = 50
        
        if matches > diffs + 5:
            prediction = "DIFF"
            confidence = 65
        elif diffs > matches + 5:
            prediction = "MATCH"
            confidence = 65
        elif current_streak >= 3:
            prediction = "DIFF"  # Break the streak
            confidence = 70 + min(current_streak * 2, 20)
        
        self.match_diff = {
            "match_count": matches,
            "diff_count": diffs,
            "match_streak": self.calculate_streak_match(),
            "diff_streak": current_streak,
            "prediction": prediction,
            "confidence": min(confidence, 95),
            "last_match": self.last_20_digits[-1] if self.last_20_digits else None
        }
        
        return self.match_diff
    
    def analyze_digits(self):
        """Comprehensive digit analysis for exact predictions"""
        if len(self.last_20_digits) < 20:
            return
        
        # Frequency analysis
        for d in self.last_20_digits:
            self.digit_frequencies[d] = self.digit_frequencies.get(d, 0) + 1
        
        # Most frequent digits
        most_frequent = max(self.digit_frequencies, key=self.digit_frequencies.get)
        least_frequent = min(self.digit_frequencies, key=self.digit_frequencies.get)
        
        # Calculate probabilities
        total = sum(self.digit_frequencies.values())
        probabilities = {d: count/total for d, count in self.digit_frequencies.items()}
        
        # Look for specific patterns
        predictions = []
        
        # Single digit prediction
        if probabilities.get(most_frequent, 0) > 0.2:
            predictions.append({"digit": most_frequent, "confidence": probabilities[most_frequent] * 100, "reason": "Most frequent"})
        
        # Range predictions
        low_digits = sum(probabilities.get(d, 0) for d in [0,1,2,3,4])
        high_digits = sum(probabilities.get(d, 0) for d in [5,6,7,8,9])
        
        if low_digits > 0.6:
            predictions.append({"range": "0-4", "confidence": low_digits * 100, "reason": "Low digit bias"})
        if high_digits > 0.6:
            predictions.append({"range": "5-9", "confidence": high_digits * 100, "reason": "High digit bias"})
        
        # Streak prediction
        streak = self.calculate_streak(lambda x: True)
        if streak >= 3:
            predictions.append({"digit": self.last_20_digits[-1], "confidence": 60 + streak * 2, "reason": f"Streak of {streak}"})
        
        self.digit_predictions = predictions
        return predictions
    
    def analyze_volatility_markets(self):
        """Analyze all volatility markets and find best opportunity"""
        market_scores = {}
        
        for market, data in self.markets.items():
            score = 50
            
            # Higher score for higher volatility (more movement)
            vol_scores = {"low": 40, "medium": 60, "high": 70, "very_high": 80, "extreme": 85, "synthetic": 50}
            score += vol_scores.get(data["volatility"], 50)
            
            # Adjust based on spread
            score -= data["spread"] * 1000
            
            market_scores[market] = min(max(score, 0), 100)
        
        self.best_market = max(market_scores, key=market_scores.get)
        self.market_scores = market_scores
        
        return self.best_market
    
    def calculate_streak(self, condition_func):
        """Calculate streak based on condition"""
        if not self.last_20_digits:
            return 0
        
        streak = 1
        for i in range(len(self.last_20_digits)-1, 0, -1):
            if condition_func(self.last_20_digits[i]) == condition_func(self.last_20_digits[i-1]):
                streak += 1
            else:
                break
        return streak
    
    def calculate_streak_match(self):
        """Calculate match streak"""
        if len(self.last_20_digits) < 2:
            return 0
        
        streak = 1
        for i in range(len(self.last_20_digits)-1, 0, -1):
            if self.last_20_digits[i] == self.last_20_digits[i-1]:
                streak += 1
            else:
                break
        return streak
    
    def get_comprehensive_analysis(self):
        """Run all analysis models and combine results"""
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "last_20_digits": self.last_20_digits,
            "current_price": self.current_price,
            "market": self.current_market
        }
        
        # Run all models
        if self.settings["enable_even_odd"]:
            analysis["even_odd"] = self.analyze_even_odd()
        
        if self.settings["enable_rise_fall"]:
            analysis["rise_fall"] = self.analyze_rise_fall()
        
        if self.settings["enable_over_under"]:
            analysis["over_under"] = self.analyze_over_under()
        
        if self.settings["enable_match_diff"]:
            analysis["match_diff"] = self.analyze_match_diff()
        
        if self.settings["enable_digit_analysis"]:
            analysis["digit_predictions"] = self.analyze_digits()
        
        analysis["best_market"] = self.analyze_volatility_markets()
        
        # Generate best overall prediction
        self.analysis_result = analysis
        self.generate_best_prediction()
        
        return analysis
    
    def generate_best_prediction(self):
        """Combine all model predictions to find best trade"""
        predictions = []
        
        # Even/Odd prediction
        if self.even_odd.get("prediction") and self.even_odd.get("confidence", 0) > 60:
            predictions.append({
                "type": "EVEN_ODD",
                "direction": self.even_odd["prediction"],
                "confidence": self.even_odd["confidence"],
                "reason": f"Even/Odd edge: {self.even_odd['edge']}"
            })
        
        # Rise/Fall prediction
        if self.rise_fall.get("prediction") and self.rise_fall.get("confidence", 0) > 60:
            predictions.append({
                "type": "RISE_FALL",
                "direction": self.rise_fall["prediction"],
                "confidence": self.rise_fall["confidence"],
                "reason": f"Momentum: {self.rise_fall['momentum']:.4f}"
            })
        
        # Over/Under prediction
        if self.over_under.get("prediction") and self.over_under.get("confidence", 0) > 60:
            predictions.append({
                "type": "OVER_UNDER",
                "direction": self.over_under["prediction"],
                "confidence": self.over_under["confidence"],
                "reason": f"Edge: {self.over_under['edge']}"
            })
        
        # Match/Diff prediction
        if self.match_diff.get("prediction") and self.match_diff.get("confidence", 0) > 60:
            predictions.append({
                "type": "MATCH_DIFF",
                "direction": self.match_diff["prediction"],
                "confidence": self.match_diff["confidence"],
                "reason": f"Streak: {self.match_diff['match_streak']}"
            })
        
        # Digit predictions
        if self.digit_predictions:
            for pred in self.digit_predictions[:2]:
                if pred.get("confidence", 0) > 65:
                    predictions.append({
                        "type": "DIGIT",
                        "direction": f"DIGIT_{pred.get('digit', pred.get('range', '?'))}",
                        "confidence": pred["confidence"],
                        "reason": pred["reason"]
                    })
        
        # Sort by confidence
        predictions.sort(key=lambda x: x["confidence"], reverse=True)
        
        self.trade_signals = predictions
        self.best_prediction = predictions[0] if predictions else None
        
        return self.best_prediction
    
    async def execute_intelligent_trade(self):
        """Execute trade based on best prediction"""
        if not self.best_prediction:
            return None
        
        if self.best_prediction["confidence"] < self.settings["min_confidence"]:
            return None
        
        if self.consecutive_losses >= self.settings["max_consecutive_losses"]:
            return None
        
        if self.stats["session_pnl"] <= -self.settings["stop_loss"]:
            return None
        
        amount = self.settings["base_amount"]
        
        # Map prediction to Deriv contract type
        direction = None
        if self.best_prediction["type"] == "RISE_FALL":
            direction = "CALL" if self.best_prediction["direction"] == "RISE" else "PUT"
        elif self.best_prediction["type"] == "EVEN_ODD":
            # For even/odd, we use a different approach
            direction = "CALL" if self.best_prediction["direction"] == "EVEN" else "PUT"
        else:
            direction = "CALL"
        
        trade_msg = {
            "buy": 1,
            "parameters": {
                "amount": amount,
                "basis": "stake",
                "contract_type": direction.lower(),
                "currency": self.currency,
                "duration": 2,
                "duration_unit": "m",
                "symbol": self.current_market
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
                    "market": self.current_market,
                    "type": self.best_prediction["type"],
                    "direction": self.best_prediction["direction"],
                    "amount": amount,
                    "confidence": self.best_prediction["confidence"],
                    "reason": self.best_prediction["reason"],
                    "entry_price": self.current_price,
                    "entry_time": datetime.now().isoformat()
                }
                self.active_trades[contract_id] = trade
                logger.info(f"🎯 TRADE: {self.best_prediction['type']} - {self.best_prediction['direction']} | ${amount} | {self.best_prediction['confidence']:.0f}%")
                
                asyncio.create_task(self.monitor_trade(contract_id, 120))
                return contract_id
        except Exception as e:
            logger.error(f"Trade error: {e}")
        
        return None
    
    async def monitor_trade(self, contract_id, seconds):
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
            
            # Update stats
            self.stats["total_trades"] += 1
            self.stats["session_pnl"] += profit
            self.stats["total_profit"] += profit
            
            if profit > 0:
                self.stats["wins"] += 1
                self.consecutive_losses = 0
                if profit > self.stats["best_trade"]:
                    self.stats["best_trade"] = profit
                logger.info(f"✅ WIN: +${profit:.2f}")
            else:
                self.stats["losses"] += 1
                self.consecutive_losses += 1
                if profit < self.stats["worst_trade"]:
                    self.stats["worst_trade"] = profit
                logger.info(f"❌ LOSS: ${profit:.2f}")
            
            # Update win rate
            if self.stats["total_trades"] > 0:
                self.stats["win_rate"] = (self.stats["wins"] / self.stats["total_trades"]) * 100
            
            # Update averages
            wins = [t.get("profit", 0) for t in self.trade_history if t.get("profit", 0) > 0]
            losses = [t.get("profit", 0) for t in self.trade_history if t.get("profit", 0) < 0]
            self.stats["avg_win"] = sum(wins) / len(wins) if wins else 0
            self.stats["avg_loss"] = sum(losses) / len(losses) if losses else 0
            
            # Record trade
            if contract_id in self.active_trades:
                trade = self.active_trades[contract_id]
                trade["profit"] = profit
                trade["exit_time"] = datetime.now().isoformat()
                self.trade_history.append(trade)
                del self.active_trades[contract_id]
            
            await self.update_balance()
            
            # Check kill switch
            if self.kill_switch["armed"]:
                if self.stats["session_pnl"] <= -self.kill_switch["stop_loss"]:
                    self.bot_status = "STOPPED"
                    logger.warning("Kill switch triggered - Stop loss hit")
                elif self.consecutive_losses >= self.kill_switch["max_losses"]:
                    self.bot_status = "STOPPED"
                    logger.warning("Kill switch triggered - Max losses reached")
            
        except Exception as e:
            logger.error(f"Monitor error: {e}")
    
    async def process_tick(self, tick_data):
        symbol = tick_data.get("symbol")
        price = tick_data.get("quote")
        
        if not symbol or symbol != self.current_market:
            return
        
        self.current_price = float(price)
        self.price_history.append(self.current_price)
        
        # Extract last digit for analysis
        price_str = f"{self.current_price:.4f}"
        last_digit = int(price_str[-1]) if price_str[-1].isdigit() else 0
        self.last_20_digits.append(last_digit)
        if len(self.last_20_digits) > 20:
            self.last_20_digits = self.last_20_digits[-20:]
        
        # Run analysis every tick
        self.get_comprehensive_analysis()
        
        # Execute trade if auto-trading is on
        if self.settings["auto_trading"] and self.bot_status == "RUNNING":
            await self.execute_intelligent_trade()
        
        logger.info(f"{symbol}: ${self.current_price:.4f} | Best: {self.best_prediction.get('type', 'None') if self.best_prediction else 'None'} | Conf: {self.best_prediction.get('confidence', 0):.0f}%")
    
    async def listen_for_prices(self):
        while self.connected and self.bot_status == "RUNNING":
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
            await self.subscribe_to_market()
            await self.listen_for_prices()
    
    def start_bot(self):
        self.bot_status = "RUNNING"
        logger.info("Bot started")
    
    def stop_bot(self):
        self.bot_status = "STOPPED"
        self.settings["auto_trading"] = False
        logger.info("Bot stopped")
    
    def update_settings(self, new_settings):
        self.settings.update(new_settings)
        logger.info("Settings updated")
    
    def get_full_state(self):
        return {
            "connected": self.connected,
            "bot_status": self.bot_status,
            "active_account": self.active_account,
            "current_balance": self.current_balance,
            "currency": self.currency,
            "current_market": self.current_market,
            "current_price": self.current_price,
            "settings": self.settings,
            "stats": self.stats,
            "analysis": self.analysis_result,
            "best_prediction": self.best_prediction,
            "trade_signals": self.trade_signals,
            "active_trades": len(self.active_trades),
            "trade_history": self.trade_history[-20:],
            "consecutive_losses": self.consecutive_losses,
            "kill_switch": self.kill_switch,
            "even_odd": self.even_odd,
            "rise_fall": self.rise_fall,
            "over_under": self.over_under,
            "match_diff": self.match_diff,
            "market_scores": self.market_scores,
            "best_market": self.best_market,
            "last_20_digits": self.last_20_digits
        }

platform = UltimateIntelligentSystem()

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(platform.run())
    yield

app = FastAPI(lifespan=lifespan)

# ULTIMATE HTML DASHBOARD
HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🧠 ULTIMATE AI TRADING SYSTEM | SmartPip</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: #0a0e27; color: #e2e8f0; }
        
        /* Header */
        .header { background: linear-gradient(135deg, #0f1235, #1a1f4e); padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2d3748; position: sticky; top: 0; z-index: 100; }
        .logo { font-size: 22px; font-weight: 800; background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .balance-card { background: rgba(16,185,129,0.1); padding: 8px 20px; border-radius: 12px; border: 1px solid rgba(16,185,129,0.3); text-align: center; }
        .balance-value { font-size: 24px; font-weight: bold; color: #10b981; }
        
        /* Main Grid */
        .main-grid { display: grid; grid-template-columns: 380px 1fr 380px; gap: 20px; padding: 20px; max-width: 1600px; margin: 0 auto; }
        
        /* Panels */
        .panel { background: #0f1235; border-radius: 16px; border: 1px solid #2d3748; overflow: hidden; }
        .panel-header { padding: 15px 20px; background: #1a1f4e; font-weight: bold; font-size: 14px; border-bottom: 1px solid #2d3748; }
        .panel-content { padding: 20px; }
        
        /* Market Card */
        .market-card { background: linear-gradient(135deg, #1a1f4e, #0f1235); border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 20px; border: 1px solid #2d3748; }
        .market-price { font-size: 36px; font-weight: bold; margin: 10px 0; }
        .status-badge { display: inline-block; padding: 5px 15px; border-radius: 20px; font-size: 12px; font-weight: bold; }
        .status-running { background: #10b981; color: white; animation: pulse 2s infinite; }
        .status-stopped { background: #ef4444; color: white; }
        
        /* Prediction Card */
        .prediction-card { background: linear-gradient(135deg, #667eea20, #764ba220); border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 20px; border: 1px solid #667eea; }
        .prediction-type { font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }
        .prediction-value { font-size: 28px; font-weight: bold; margin: 10px 0; color: #667eea; }
        .prediction-confidence { font-size: 20px; font-weight: bold; color: #10b981; }
        
        /* Stats Grid */
        .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }
        .stat-card { background: #1a1f4e; padding: 12px; border-radius: 10px; text-align: center; }
        .stat-label { font-size: 10px; color: #94a3b8; margin-bottom: 5px; text-transform: uppercase; }
        .stat-value { font-size: 18px; font-weight: bold; }
        
        /* Analysis Cards */
        .analysis-card { background: #1a1f4e; border-radius: 10px; padding: 15px; margin-bottom: 10px; }
        .analysis-title { font-size: 13px; font-weight: bold; margin-bottom: 10px; color: #667eea; }
        .analysis-row { display: flex; justify-content: space-between; padding: 5px 0; font-size: 12px; border-bottom: 1px solid #2d3748; }
        .prediction-tag { background: #667eea20; padding: 2px 8px; border-radius: 12px; color: #667eea; }
        
        /* Settings Panel */
        .setting-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #2d3748; }
        .setting-label { font-size: 13px; }
        .setting-input { background: #0f1235; border: 1px solid #2d3748; color: white; padding: 6px 12px; border-radius: 6px; width: 100px; }
        .setting-checkbox { width: 20px; height: 20px; cursor: pointer; }
        
        /* Buttons */
        .btn-start { background: linear-gradient(135deg, #10b981, #059669); color: white; border: none; padding: 12px 24px; border-radius: 10px; font-weight: bold; cursor: pointer; margin-right: 10px; }
        .btn-stop { background: linear-gradient(135deg, #ef4444, #dc2626); color: white; border: none; padding: 12px 24px; border-radius: 10px; font-weight: bold; cursor: pointer; }
        .btn-manual { background: #1a1f4e; border: 1px solid #667eea; color: #667eea; padding: 8px 16px; border-radius: 8px; cursor: pointer; margin: 5px; }
        .btn-save { background: #667eea; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; }
        
        /* Digits */
        .digits-container { background: #1a1f4e; border-radius: 12px; padding: 15px; margin-bottom: 20px; }
        .digits-row { display: flex; gap: 8px; flex-wrap: wrap; margin: 10px 0; justify-content: center; }
        .digit { width: 40px; height: 40px; background: #0f1235; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 18px; border: 1px solid #2d3748; }
        
        /* Trade Log */
        .trade-log { max-height: 300px; overflow-y: auto; }
        .trade-item { background: #1a1f4e; padding: 10px; border-radius: 8px; margin-bottom: 8px; border-left: 3px solid; font-size: 11px; }
        .trade-win { border-left-color: #10b981; }
        .trade-loss { border-left-color: #ef4444; }
        
        /* Market Selector */
        .market-selector { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; }
        .market-btn { background: #1a1f4e; border: 1px solid #2d3748; color: #94a3b8; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 11px; }
        .market-btn.active { background: linear-gradient(135deg, #667eea, #764ba2); color: white; }
        
        /* Signal List */
        .signal-item { background: #1a1f4e; padding: 8px; border-radius: 6px; margin-bottom: 5px; font-size: 11px; display: flex; justify-content: space-between; align-items: center; }
        
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
        <div class="logo">🧠 ULTIMATE AI TRADING SYSTEM | SmartPip</div>
        <div class="balance-card">
            <div style="font-size:11px;">Balance</div>
            <div class="balance-value" id="balance">$0.00</div>
        </div>
    </div>
    
    <div class="main-grid">
        <!-- LEFT PANEL - TRADING & PREDICTION -->
        <div class="panel">
            <div class="panel-header">🎯 LIVE TRADING</div>
            <div class="panel-content">
                <div class="market-card">
                    <div style="font-size:12px; color:#94a3b8;">Current Market</div>
                    <div class="market-price" id="price">$0.00</div>
                    <div><span class="status-badge" id="status">STOPPED</span></div>
                </div>
                
                <div class="market-selector" id="marketSelector"></div>
                
                <div class="prediction-card">
                    <div class="prediction-type">BEST PREDICTION</div>
                    <div class="prediction-value" id="bestPrediction">-</div>
                    <div class="prediction-confidence" id="bestConfidence">0% confidence</div>
                    <div style="font-size:11px; margin-top:10px;" id="bestReason"></div>
                </div>
                
                <div style="display:flex; gap:10px; margin-bottom:20px;">
                    <button class="btn-start" onclick="startBot()">▶ START ENGINE</button>
                    <button class="btn-stop" onclick="stopBot()">⏹ STOP ENGINE</button>
                </div>
                
                <div style="margin-bottom:20px;">
                    <button class="btn-manual" onclick="manualTrade('CALL')">📈 MANUAL CALL</button>
                    <button class="btn-manual" onclick="manualTrade('PUT')">📉 MANUAL PUT</button>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card"><div class="stat-label">Win Rate</div><div class="stat-value" id="winRate">0%</div></div>
                    <div class="stat-card"><div class="stat-label">Session P&L</div><div class="stat-value" id="sessionPnl">$0.00</div></div>
                    <div class="stat-card"><div class="stat-label">Total Trades</div><div class="stat-value" id="totalTrades">0</div></div>
                    <div class="stat-card"><div class="stat-label">Active</div><div class="stat-value" id="activeTrades">0</div></div>
                </div>
            </div>
        </div>
        
        <!-- CENTER PANEL - INTELLIGENT ANALYSIS -->
        <div class="panel">
            <div class="panel-header">🧠 INTELLIGENT MARKET ANALYSIS</div>
            <div class="panel-content">
                <div class="digits-container">
                    <div style="font-size:12px; margin-bottom:10px;">📊 LAST 20 DIGITS PATTERN</div>
                    <div class="digits-row" id="digitsRow"></div>
                </div>
                
                <div class="analysis-card">
                    <div class="analysis-title">🎲 EVEN / ODD ANALYSIS</div>
                    <div class="analysis-row"><span>Even/Odd Count</span><span id="evenOddCount">0E / 0O</span></div>
                    <div class="analysis-row"><span>Prediction</span><span id="evenOddPred" class="prediction-tag">-</span></div>
                    <div class="analysis-row"><span>Confidence</span><span id="evenOddConf">0%</span></div>
                </div>
                
                <div class="analysis-card">
                    <div class="analysis-title">📈 RISE / FALL ANALYSIS</div>
                    <div class="analysis-row"><span>Rise/Fall Count</span><span id="riseFallCount">0R / 0F</span></div>
                    <div class="analysis-row"><span>Momentum</span><span id="momentum">0.0000</span></div>
                    <div class="analysis-row"><span>Prediction</span><span id="riseFallPred" class="prediction-tag">-</span></div>
                </div>
                
                <div class="analysis-card">
                    <div class="analysis-title">📊 OVER 3 / UNDER 7 ANALYSIS</div>
                    <div class="analysis-row"><span>Over 3 / Under 7</span><span id="overUnderCount">0O / 0U</span></div>
                    <div class="analysis-row"><span>Prediction</span><span id="overUnderPred" class="prediction-tag">-</span></div>
                    <div class="analysis-row"><span>Confidence</span><span id="overUnderConf">0%</span></div>
                </div>
                
                <div class="analysis-card">
                    <div class="analysis-title">🔄 MATCH / DIFF ANALYSIS</div>
                    <div class="analysis-row"><span>Match/Diff Count</span><span id="matchDiffCount">0M / 0D</span></div>
                    <div class="analysis-row"><span>Streak</span><span id="streak">0</span></div>
                    <div class="analysis-row"><span>Prediction</span><span id="matchDiffPred" class="prediction-tag">-</span></div>
                </div>
                
                <div class="analysis-card">
                    <div class="analysis-title">🏆 TOP TRADE SIGNALS</div>
                    <div id="tradeSignalsList"></div>
                </div>
            </div>
        </div>
        
        <!-- RIGHT PANEL - SETTINGS & TRADE LOG -->
        <div class="panel">
            <div class="panel-header">⚙️ SETTINGS & CONTROL</div>
            <div class="panel-content">
                <div class="setting-row">
                    <span class="setting-label">💰 Base Trade Amount</span>
                    <input type="number" id="baseAmount" class="setting-input" value="1" step="0.5">
                </div>
                <div class="setting-row">
                    <span class="setting-label">🎯 Min Confidence (%)</span>
                    <input type="number" id="minConfidence" class="setting-input" value="70" min="50" max="95">
                </div>
                <div class="setting-row">
                    <span class="setting-label">🛑 Stop Loss ($)</span>
                    <input type="number" id="stopLoss" class="setting-input" value="50">
                </div>
                <div class="setting-row">
                    <span class="setting-label">🎯 Take Profit ($)</span>
                    <input type="number" id="takeProfit" class="setting-input" value="100">
                </div>
                <div class="setting-row">
                    <span class="setting-label">📊 Max Consecutive Losses</span>
                    <input type="number" id="maxLosses" class="setting-input" value="3">
                </div>
                <div class="setting-row">
                    <span class="setting-label">🔘 Enable Even/Odd</span>
                    <input type="checkbox" id="enableEvenOdd" class="setting-checkbox" checked>
                </div>
                <div class="setting-row">
                    <span class="setting-label">🔘 Enable Rise/Fall</span>
                    <input type="checkbox" id="enableRiseFall" class="setting-checkbox" checked>
                </div>
                <div class="setting-row">
                    <span class="setting-label">🔘 Enable Over/Under</span>
                    <input type="checkbox" id="enableOverUnder" class="setting-checkbox" checked>
                </div>
                <div class="setting-row">
                    <span class="setting-label">🔘 Enable Match/Diff</span>
                    <input type="checkbox" id="enableMatchDiff" class="setting-checkbox" checked>
                </div>
                <div class="setting-row">
                    <span class="setting-label">🛡 Kill Switch Armed</span>
                    <input type="checkbox" id="killSwitch" class="setting-checkbox" checked>
                </div>
                <div class="setting-row">
                    <span class="setting-label">🤖 Auto Trading</span>
                    <input type="checkbox" id="autoTrading" class="setting-checkbox">
                </div>
                <div class="setting-row">
                    <button class="btn-save" onclick="saveSettings()">💾 SAVE SETTINGS</button>
                    <button class="btn-save" onclick="resetSession()">🔄 RESET SESSION</button>
                </div>
            </div>
            
            <div class="panel-header" style="margin-top:0;">📋 TRADE LOG</div>
            <div class="panel-content">
                <div class="trade-log" id="tradeLog">
                    <div style="text-align:center; padding:20px;">No trades yet</div>
                </div>
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
            // Balance & Status
            document.getElementById('balance').innerHTML = `${data.currency || '$'}${(data.current_balance || 0).toFixed(2)}`;
            document.getElementById('price').innerHTML = `${data.currency || '$'}${(data.current_price || 0).toFixed(4)}`;
            document.getElementById('status').innerHTML = data.bot_status || 'STOPPED';
            document.getElementById('status').className = `status-badge status-${(data.bot_status || 'stopped').toLowerCase()}`;
            
            // Stats
            document.getElementById('winRate').innerHTML = `${(data.stats?.win_rate || 0).toFixed(0)}%`;
            const sessionPnl = data.stats?.session_pnl || 0;
            document.getElementById('sessionPnl').innerHTML = `${sessionPnl >= 0 ? '+' : ''}${data.currency || '$'}${sessionPnl.toFixed(2)}`;
            document.getElementById('totalTrades').innerHTML = data.stats?.total_trades || 0;
            document.getElementById('activeTrades').innerHTML = data.active_trades || 0;
            
            // Best Prediction
            if (data.best_prediction) {
                document.getElementById('bestPrediction').innerHTML = `${data.best_prediction.type} - ${data.best_prediction.direction}`;
                document.getElementById('bestConfidence').innerHTML = `${data.best_prediction.confidence.toFixed(0)}% confidence`;
                document.getElementById('bestReason').innerHTML = data.best_prediction.reason || '';
            } else {
                document.getElementById('bestPrediction').innerHTML = 'Analyzing...';
                document.getElementById('bestConfidence').innerHTML = '0% confidence';
            }
            
            // Even/Odd
            if (data.even_odd) {
                document.getElementById('evenOddCount').innerHTML = `${data.even_odd.even_count || 0}E / ${data.even_odd.odd_count || 0}O`;
                document.getElementById('evenOddPred').innerHTML = data.even_odd.prediction || '-';
                document.getElementById('evenOddConf').innerHTML = `${(data.even_odd.confidence || 0).toFixed(0)}%`;
            }
            
            // Rise/Fall
            if (data.rise_fall) {
                document.getElementById('riseFallCount').innerHTML = `${data.rise_fall.rise_count || 0}R / ${data.rise_fall.fall_count || 0}F`;
                document.getElementById('momentum').innerHTML = (data.rise_fall.momentum || 0).toFixed(4);
                document.getElementById('riseFallPred').innerHTML = data.rise_fall.prediction || '-';
            }
            
            // Over/Under
            if (data.over_under) {
                document.getElementById('overUnderCount').innerHTML = `${data.over_under.over_3_count || 0}O / ${data.over_under.under_7_count || 0}U`;
                document.getElementById('overUnderPred').innerHTML = data.over_under.prediction || '-';
                document.getElementById('overUnderConf').innerHTML = `${(data.over_under.confidence || 0).toFixed(0)}%`;
            }
            
            // Match/Diff
            if (data.match_diff) {
                document.getElementById('matchDiffCount').innerHTML = `${data.match_diff.match_count || 0}M / ${data.match_diff.diff_count || 0}D`;
                document.getElementById('streak').innerHTML = data.match_diff.match_streak || 0;
                document.getElementById('matchDiffPred').innerHTML = data.match_diff.prediction || '-';
            }
            
            // Digits
            if (data.last_20_digits && data.last_20_digits.length > 0) {
                const digitsRow = document.getElementById('digitsRow');
                digitsRow.innerHTML = data.last_20_digits.map(d => `<div class="digit">${d}</div>`).join('');
            }
            
            // Trade Signals
            if (data.trade_signals && data.trade_signals.length > 0) {
                const signalsList = document.getElementById('tradeSignalsList');
                signalsList.innerHTML = data.trade_signals.slice(0,5).map(s => `
                    <div class="signal-item">
                        <span>${s.type}</span>
                        <span style="color:#667eea;">${s.direction}</span>
                        <span style="color:#10b981;">${s.confidence.toFixed(0)}%</span>
                    </div>
                `).join('');
            }
            
            // Trade Log
            if (data.trade_history && data.trade_history.length > 0) {
                const logContainer = document.getElementById('tradeLog');
                logContainer.innerHTML = data.trade_history.slice().reverse().map(trade => `
                    <div class="trade-item ${trade.profit > 0 ? 'trade-win' : trade.profit < 0 ? 'trade-loss' : ''}">
                        <div>${new Date(trade.entry_time).toLocaleTimeString()} | ${trade.type}</div>
                        <div>${trade.direction} | ${trade.profit > 0 ? '+' : ''}${data.currency || '$'}${(trade.profit || 0).toFixed(2)}</div>
                        <div style="font-size:10px;">Conf: ${trade.confidence}% | ${trade.reason}</div>
                    </div>
                `).join('');
            }
            
            // Market Selector
            if (data.market_scores) {
                const selector = document.getElementById('marketSelector');
                selector.innerHTML = Object.keys(data.market_scores).map(m => 
                    `<button class="market-btn ${m === data.current_market ? 'active' : ''}" onclick="switchMarket('${m}')">${m}<br><small>${data.market_scores[m]}%</small></button>`
                ).join('');
            }
            
            // Settings sync
            document.getElementById('baseAmount').value = data.settings?.base_amount || 1;
            document.getElementById('minConfidence').value = data.settings?.min_confidence || 70;
            document.getElementById('stopLoss').value = data.settings?.stop_loss || 50;
            document.getElementById('takeProfit').value = data.settings?.take_profit || 100;
            document.getElementById('maxLosses').value = data.settings?.max_consecutive_losses || 3;
            document.getElementById('enableEvenOdd').checked = data.settings?.enable_even_odd !== false;
            document.getElementById('enableRiseFall').checked = data.settings?.enable_rise_fall !== false;
            document.getElementById('enableOverUnder').checked = data.settings?.enable_over_under !== false;
            document.getElementById('enableMatchDiff').checked = data.settings?.enable_match_diff !== false;
            document.getElementById('killSwitch').checked = data.kill_switch?.armed || false;
            document.getElementById('autoTrading').checked = data.settings?.auto_trading || false;
        }
        
        function startBot() { fetch('/api/start', { method: 'POST' }); }
        function stopBot() { fetch('/api/stop', { method: 'POST' }); }
        
        function switchMarket(market) { 
            fetch('/api/switch_market', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ market }) });
        }
        
        function saveSettings() {
            const settings = {
                base_amount: parseFloat(document.getElementById('baseAmount').value),
                min_confidence: parseFloat(document.getElementById('minConfidence').value),
                stop_loss: parseFloat(document.getElementById('stopLoss').value),
                take_profit: parseFloat(document.getElementById('takeProfit').value),
                max_consecutive_losses: parseInt(document.getElementById('maxLosses').value),
                enable_even_odd: document.getElementById('enableEvenOdd').checked,
                enable_rise_fall: document.getElementById('enableRiseFall').checked,
                enable_over_under: document.getElementById('enableOverUnder').checked,
                enable_match_diff: document.getElementById('enableMatchDiff').checked,
                auto_trading: document.getElementById('autoTrading').checked
            };
            fetch('/api/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(settings) });
        }
        
        function resetSession() { fetch('/api/reset_session', { method: 'POST' }); }
        
        function manualTrade(direction) {
            const amount = prompt('Enter trade amount:', '1');
            if (amount) {
                fetch('/api/manual_trade', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ direction, amount: parseFloat(amount) }) });
            }
        }
        
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
    platform.settings["auto_trading"] = True
    return JSONResponse({"success": True})

@app.post("/api/stop")
async def stop_bot():
    platform.stop_bot()
    platform.settings["auto_trading"] = False
    return JSONResponse({"success": True})

@app.post("/api/settings")
async def update_settings(request: Request):
    data = await request.json()
    platform.update_settings(data)
    return JSONResponse({"success": True})

@app.post("/api/switch_market")
async def switch_market(request: Request):
    data = await request.json()
    platform.current_market = data.get("market")
    platform.price_history.clear()
    platform.last_20_digits = []
    await platform.subscribe_to_market()
    return JSONResponse({"success": True})

@app.post("/api/manual_trade")
async def manual_trade(request: Request):
    data = await request.json()
    platform.settings["base_amount"] = data.get("amount", 1)
    platform.best_prediction = {
        "type": "MANUAL",
        "direction": data.get("direction"),
        "confidence": 100,
        "reason": "Manual trade"
    }
    result = await platform.execute_intelligent_trade()
    return JSONResponse({"success": result is not None})

@app.post("/api/reset_session")
async def reset_session():
    platform.stats = {
        "total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0,
        "total_profit": 0, "session_pnl": 0, "best_trade": 0, "worst_trade": 0,
        "avg_win": 0, "avg_loss": 0
    }
    platform.trade_history = []
    platform.consecutive_losses = 0
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