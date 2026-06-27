import asyncio
import json
import logging
from collections import deque
from datetime import datetime
from typing import Dict, Any, Optional

from config import Settings
from core import DerivConnection, AccountManager, MarketManager, MarketSelector
from analysis import AnalysisManager
from trading import TradeExecutor, TradeMonitor, RiskManager, StatsManager, PositionSizer, ExecutionOptimizer, ZeroLossRiskManager
from database import DatabaseManager, SupabaseManager
from utils import CacheManager, PerformanceMetrics, system_logger, trade_logger, performance_logger
from trading.trade_journal import TradeJournal
from models import Prediction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TradingSystem:
    """Main trading system that orchestrates all modules with performance optimizations"""
    
    def __init__(self):
        # ========== CORE MODULES ==========
        self.connection = DerivConnection()
        self.account = AccountManager()
        self.market = MarketManager()
        self.market_selector = MarketSelector()
        
        # ========== ANALYSIS MODULE ==========
        self.analysis = AnalysisManager()
        
        # ========== TRADING MODULES ==========
        self.executor = TradeExecutor()
        self.monitor = TradeMonitor()
        self.risk_manager = RiskManager()
        self.zero_loss_risk_manager = ZeroLossRiskManager()
        self.stats_manager = StatsManager()
        self.position_sizer = PositionSizer()
        self.execution_optimizer = ExecutionOptimizer()
        self.trade_journal = TradeJournal()
        
        # ========== PERFORMANCE MODULES ==========
        self.cache = CacheManager(max_size=1000, ttl=5)
        self.metrics = PerformanceMetrics(max_history=1000)
        # Initialize database (Supabase primary, SQLite fallback)
        self.database = SupabaseManager()
        try:
            test_settings = self.database.get_settings()
            if test_settings is None:
                raise Exception("Supabase not available")
        except Exception:
            self.database = DatabaseManager()
        
        # ========== SETTINGS ==========
        self.settings = Settings()
        # Load persisted settings from database
        try:
            db_settings = self.database.get_settings()
            if db_settings:
                for key in ['base_amount', 'auto_trading', 'max_trades_per_hour', 'min_confidence',
                           'stop_loss', 'take_profit', 'max_consecutive_losses',
                           'enable_even_odd', 'enable_rise_fall', 'enable_over_under',
                           'enable_match_diff', 'enable_digit_analysis']:
                    if key in db_settings and db_settings[key] is not None:
                        setattr(self.settings, key, db_settings[key])
        except Exception:
            pass
        
        # ========== DATA STORAGE ==========
        self.current_price = 0
        self.price_history = deque(maxlen=500)
        self.last_20_digits = []
        self.digit_history = deque(maxlen=100)
        
        # ========== BOT STATUS ==========
        self.bot_status = "STOPPED"
        self.best_prediction: Optional[Prediction] = None
        
        # Configure analyzers based on settings
        self._configure_analyzers()
        
        # Setup connection callbacks
        self.connection.set_reconnect_callback(self._on_reconnect)
        self.connection.set_disconnect_callback(self._on_disconnect)
    
    def _configure_analyzers(self):
        """Configure analyzers based on settings"""
        self.analysis.set_analyzer_enabled("even_odd", self.settings.enable_even_odd)
        self.analysis.set_analyzer_enabled("rise_fall", self.settings.enable_rise_fall)
        self.analysis.set_analyzer_enabled("over_under", self.settings.enable_over_under)
        self.analysis.set_analyzer_enabled("match_diff", self.settings.enable_match_diff)
        self.analysis.set_analyzer_enabled("digit_analysis", self.settings.enable_digit_analysis)
    
    async def _on_reconnect(self):
        """Callback when connection is re-established"""
        system_logger.info("Reconnected to Deriv API", reconnect_attempts=self.connection.reconnect_attempts)
        await self.subscribe_to_market()
        self.metrics.increment_counter("reconnections")
    
    async def _on_disconnect(self):
        """Callback when connection is lost"""
        system_logger.warning("Disconnected from Deriv API", reconnect_attempts=self.connection.reconnect_attempts)
        self.metrics.increment_counter("disconnections")
    
    async def connect(self) -> bool:
        """Connect to Deriv API"""
        if await self.connection.connect():
            await self.account.update_balance(self.connection.websocket)
            return True
        return False
    
    async def subscribe_to_market(self):
        """Subscribe to current market"""
        await self.market.subscribe_to_market(
            self.connection.websocket,
            self.market.get_current_market()
        )
    
    def switch_market(self, market: str):
        """Switch to different market"""
        self.market.set_market(market)
        self.price_history.clear()
        self.last_20_digits = []
        logger.info(f"Switched to market: {market}")
    
    def start_bot(self):
        """Start the trading bot"""
        self.bot_status = "RUNNING"
        logger.info("Bot started")
    
    def stop_bot(self):
        """Stop the trading bot"""
        self.bot_status = "STOPPED"
        self.settings.auto_trading = False
        logger.info("Bot stopped")
    
    def reset_session(self):
        """Reset session statistics"""
        self.stats_manager.reset_stats()
        self.risk_manager.reset_consecutive_losses()
        self.monitor.trade_history = []
        logger.info("Session reset")
    
    async def process_tick(self, tick_data: Dict[str, Any]):
        """Process incoming tick data with performance tracking"""
        self.metrics.start_timer("process_tick")
        
        symbol = tick_data.get("symbol")
        price = tick_data.get("quote")
        
        if not symbol or symbol != self.market.get_current_market():
            self.metrics.stop_timer("process_tick")
            return
        
        self.current_price = float(price)
        self.price_history.append(self.current_price)
        
        # Extract last digit for analysis
        price_str = f"{self.current_price:.4f}"
        last_digit = int(price_str[-1]) if price_str[-1].isdigit() else 0
        self.last_20_digits.append(last_digit)
        if len(self.last_20_digits) > 20:
            self.last_20_digits = self.last_20_digits[-20:]
        
        # Run analysis with caching
        analysis_data = {
            "last_20_digits": self.last_20_digits,
            "price_history": self.price_history,
            "current_price": self.current_price,
            "market": self.market.get_current_market(),
            "markets": self.market.get_all_markets()
        }
        
        # Check cache first
        cached_result = self.cache.get(analysis_data)
        if cached_result:
            self.analysis.analysis_result = cached_result
            self.analysis.generate_best_prediction()
            self.best_prediction = self.analysis.get_best_prediction()
        else:
            self.metrics.start_timer("analysis")
            self.analysis.get_comprehensive_analysis(analysis_data)
            self.best_prediction = self.analysis.get_best_prediction()
            self.metrics.stop_timer("analysis")
            # Cache the result
            self.cache.set(analysis_data, self.analysis.analysis_result)
        
        # Execute trade if auto-trading is on
        if self.settings.auto_trading and self.bot_status == "RUNNING":
            await self.execute_intelligent_trade()
        
        self.metrics.increment_counter("ticks_processed")
        self.metrics.stop_timer("process_tick")
        
        logger.info(
            f"{symbol}: ${self.current_price:.4f} | "
            f"Best: {self.best_prediction.type if self.best_prediction else 'None'} | "
            f"Conf: {self.best_prediction.confidence if self.best_prediction else 0:.0f}%"
        )
    
    async def execute_intelligent_trade(self) -> Optional[str]:
        """Execute trade based on best prediction"""
        if not self.best_prediction:
            return None
        
        if self.best_prediction.confidence < self.settings.min_confidence:
            return None
        
        # Check risk limits
        can_trade, reason = self.risk_manager.check_risk_limits(
            self.stats_manager.get_stats()["session_pnl"],
            self.risk_manager.get_consecutive_losses(),
            self.settings.to_dict()
        )
        
        if not can_trade:
            logger.warning(f"Trade blocked: {reason}")
            if "kill switch" in reason.lower():
                self.bot_status = "STOPPED"
            return None
        
        # Execute trade
        contract_id = await self.executor.execute_trade(
            self.connection.websocket,
            self.best_prediction,
            self.market.get_current_market(),
            self.account.get_currency(),
            self.settings.base_amount,
            self.current_price
        )
        
        if contract_id:
            # Log trade entry to journal
            try:
                analysis_data = getattr(self, "analysis_result", {})
                entry_conditions = []
                if self.best_prediction:
                    entry_conditions = [
                        f"confidence: {self.best_prediction.confidence:.1f}%",
                        f"type: {self.best_prediction.type}",
                    ]
                    if hasattr(self.best_prediction, 'reason') and self.best_prediction.reason:
                        entry_conditions.append(f"reason: {self.best_prediction.reason}")
                regime = "unknown"
                try:
                    regime_det = getattr(self, "regime_detector", None)
                    if regime_det:
                        regime = getattr(regime_det, "current_regime", "unknown")
                    elif hasattr(self.analysis, "last_analysis"):
                        regime = self.analysis.last_analysis.get("regime", "unknown")
                except Exception:
                    pass
                balance = self.account.get_balance() if hasattr(self.account, "get_balance") else self.stats_manager.get_stats().get("total_profit", 1000) + 1000
                self._pending_journal_ids = getattr(self, "_pending_journal_ids", {})
                jid = self.trade_journal.log_trade(
                    symbol=self.market.get_current_market(),
                    contract_type=self.best_prediction.type,
                    entry_price=self.current_price,
                    amount=self.settings.base_amount,
                    confidence=self.best_prediction.confidence,
                    regime=str(regime),
                    entry_conditions=entry_conditions,
                    running_balance=float(self.stats_manager.get_stats().get("total_profit", 0) + 1000),
                )
                self._pending_journal_ids[contract_id] = jid
            except Exception as je:
                logger.warning("Journal log_trade failed: %s", je)

            # Monitor the trade
            asyncio.create_task(
                self.monitor.monitor_trade(
                    self.connection.websocket,
                    contract_id,
                    120,
                    self._on_trade_complete
                )
            )
        
        return contract_id
    
    async def _on_trade_complete(self, contract_id: str, profit: float):
        """Callback when trade completes with database persistence and structured logging"""
        self.metrics.start_timer("trade_completion")
        
        # Update statistics
        self.stats_manager.update_stats(profit)
        self.stats_manager.update_averages(self.monitor.get_all_trade_history())
        
        # Update risk manager
        self.risk_manager.update_consecutive_losses(profit)
        
        # Complete trade in monitor
        trade_data = self.executor.get_trade(contract_id)
        if trade_data:
            self.monitor.complete_trade(contract_id, profit)
            
            # Save trade to database
            trade_data["profit"] = profit
            self.database.save_trade(trade_data)

            # Close trade in journal
            try:
                pending = getattr(self, "_pending_journal_ids", {})
                jid = pending.pop(contract_id, None)
                if jid:
                    balance = float(self.stats_manager.get_stats().get("total_profit", 0) + 1000)
                    exit_conditions = [
                        "contract_settled",
                        f"outcome: {'WIN' if profit > 0 else 'LOSS'}",
                        f"pnl: {profit:+.4f}",
                    ]
                    self.trade_journal.close_trade(
                        trade_id=jid,
                        pnl=profit,
                        exit_price=float(trade_data.get("exit_price", self.current_price)),
                        exit_conditions=exit_conditions,
                        exit_reason="contract_settled",
                        running_balance=balance,
                    )
            except Exception as je:
                logger.warning("Journal close_trade failed: %s", je)
            
            # Update statistics in database
            self.database.update_statistics(self.stats_manager.get_stats())
            
            # Log trade completion with structured data
            trade_logger.info(
                "Trade completed",
                contract_id=contract_id,
                profit=profit,
                trade_type=trade_data.get("type"),
                direction=trade_data.get("direction"),
                confidence=trade_data.get("confidence")
            )
            
            self.executor.remove_trade(contract_id)
        
        # Update balance
        await self.account.update_balance(self.connection.websocket)
        
        # Record performance metrics
        self.metrics.increment_counter("trades_completed")
        self.metrics.record_timing("trade_profit", abs(profit))
        
        # Check kill switch
        can_trade, reason = self.risk_manager.check_risk_limits(
            self.stats_manager.get_stats()["session_pnl"],
            self.risk_manager.get_consecutive_losses(),
            self.settings.to_dict()
        )
        
        if not can_trade and "kill switch" in reason.lower():
            self.bot_status = "STOPPED"
            system_logger.warning("Kill switch triggered", reason=reason, session_pnl=self.stats_manager.get_stats()["session_pnl"])
        
        self.metrics.stop_timer("trade_completion")
    
    async def listen_for_prices(self):
        """Listen for price updates from WebSocket"""
        while self.connection.connected and self.bot_status == "RUNNING":
            try:
                message = await self.connection.recv()
                data = json.loads(message)
                if "tick" in data:
                    await self.process_tick(data["tick"])
            except Exception as e:
                logger.error(f"Listen error: {e}")
                await asyncio.sleep(1)
    
    async def run(self):
        """Main run loop"""
        if await self.connect():
            await self.subscribe_to_market()
            await self.listen_for_prices()
    
    def get_full_state(self) -> Dict[str, Any]:
        """Get full system state for API/dashboard with performance metrics"""
        analysis_result = self.analysis.analysis_result
        
        # Get market analysis
        market_analysis = self.market_selector.evaluate_markets()
        
        return {
            "connected": self.connection.connected,
            "bot_status": self.bot_status,
            "active_account": self.account.active_account,
            "current_balance": self.account.get_balance(),
            "currency": self.account.get_currency(),
            "current_market": self.market_selector.get_current_market(),
            "current_price": self.current_price,
            "settings": self.settings.to_dict(),
            "stats": self.stats_manager.get_stats(),
            "analysis": analysis_result,
            "best_prediction": {
                "type": self.best_prediction.type,
                "direction": self.best_prediction.direction,
                "confidence": self.best_prediction.confidence,
                "reason": self.best_prediction.reason
            } if self.best_prediction else None,
            "trade_signals": self.analysis.get_trade_signals(),
            "active_trades": self.monitor.get_active_trades_count(),
            "trade_history": self.monitor.get_trade_history(),
            "consecutive_losses": self.risk_manager.get_consecutive_losses(),
            "kill_switch": self.risk_manager.get_kill_switch(),
            "even_odd": analysis_result.get("even_odd", {}).get("data", {}),
            "rise_fall": analysis_result.get("rise_fall", {}).get("data", {}),
            "over_under": analysis_result.get("over_under", {}).get("data", {}),
            "match_diff": analysis_result.get("match_diff", {}).get("data", {}),
            "market_analysis": market_analysis,
            "market_ranking": self.market_selector.get_market_ranking(),
            "switch_history": self.market_selector.get_switch_history(),
            "last_20_digits": self.last_20_digits,
            "hft_metrics": {
                "average_latency": self.execution_optimizer.get_average_latency(),
                "latency_p95": self.execution_optimizer.get_latency_percentile(95),
                "latency_p99": self.execution_optimizer.get_latency_percentile(99),
                "execution_count": len(self.execution_optimizer.execution_times)
            },
            "zero_loss_risk": self.zero_loss_risk_manager.get_risk_metrics(),
            "performance": {
                "cache": self.cache.get_stats(),
                "metrics": self.metrics.get_summary(),
                "connection": {
                    "reconnect_attempts": self.connection.reconnect_attempts
                }
            }
        }
