import asyncio
import json
import time
import logging
import os
from collections import deque
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from config import Settings
from core import DerivConnection, AccountManager, MarketManager, MarketSelector
from analysis import AnalysisManager
from trading import TradeExecutor, TradeMonitor, RiskManager, StatsManager, PositionSizer, ExecutionOptimizer, ZeroLossRiskManager
from database import DatabaseManager, SupabaseManager
from utils import CacheManager, PerformanceMetrics, system_logger, trade_logger, performance_logger
from trading.trade_journal import TradeJournal
from models import Prediction
from trading.deriv_execution import DerivExecutionAdapter, expected_value_per_stake
from ai_core.trade_approval import TradeApprover
from phase5.live_gate import LiveCertificateGate
from intelligence import IntelligenceOrchestrator, ResearchOrchestrator
from intelligence.trade_memory import TradeRecord
from intelligence.probability_calibration import ProbabilityCalibrator
from strategies.registry import StrategyRegistry
from strategies.marketplace import StrategyMarketplace

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
        self.deriv_execution = DerivExecutionAdapter(self.connection)
        self.trade_approver = TradeApprover()
        self.live_certificate_gate = LiveCertificateGate(
            os.getenv("PRODUCTION_CERTIFICATE_PATH", "intelligence_data/production_certificate.json")
        )
        self.probability_calibrator = ProbabilityCalibrator(
            path=os.getenv("CALIBRATION_ARTIFACT", "intelligence_data/calibration.json"),
            min_context_samples=int(os.getenv("CALIBRATION_MIN_CONTEXT_SAMPLES", "200")),
        )
        self._last_trade_at_by_symbol = {}
        self._decision_lock = asyncio.Lock()
        self._pending_contract_tasks = {}
        self._canonical_trades = {}
        self._last_tick_epoch = 0.0
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
        self.settings = Settings.from_env()
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
        self.digit_history = deque(maxlen=500)
        
        # ========== BOT STATUS ==========
        self.bot_status = "STOPPED"
        self.best_prediction: Optional[Prediction] = None
        
        # Configure analyzers based on settings
        self._configure_analyzers()
        
        # ========== INTELLIGENCE LAYER ==========
        self.intelligence = None
        self.research = None

        # ========== STRATEGY PLATFORM ==========
        self.strategy_marketplace = StrategyMarketplace()
        self.strategy_registry = StrategyRegistry()
        self.strategy_marketplace.set_registry(self.strategy_registry)
        self._init_strategy_platform()

        if self.settings.intelligence_enabled:
            try:
                self.intelligence = IntelligenceOrchestrator(
                    analysis_manager=self.analysis,
                    settings=self.settings,
                )
                self.intelligence.load_all()
                logger.info("Intelligence layer initialised")
            except Exception as e:
                logger.warning("Intelligence layer init failed: %s — falling back to legacy mode", e)
                self.intelligence = None

            # Advanced research intelligence layer
            if getattr(self.settings, 'research_mode_enabled', False):
                try:
                    self.research = ResearchOrchestrator(
                        analysis_manager=self.analysis,
                        settings=self.settings,
                    )
                    self.research.load_all()
                    logger.info("Research intelligence layer initialised")
                except Exception as e:
                    logger.warning("Research layer init failed: %s — using legacy intelligence", e)
                    self.research = None

        # Setup connection callbacks
        self.connection.set_reconnect_callback(self._on_reconnect)
        self.connection.set_disconnect_callback(self._on_disconnect)
        self.connection.add_handler("tick", self._handle_tick_message)
    
    def _configure_analyzers(self):
        """Configure analyzers based on settings"""
        self.analysis.set_analyzer_enabled("even_odd", self.settings.enable_even_odd)
        self.analysis.set_analyzer_enabled("rise_fall", self.settings.enable_rise_fall)
        self.analysis.set_analyzer_enabled("over_under", self.settings.enable_over_under)
        self.analysis.set_analyzer_enabled("match_diff", self.settings.enable_match_diff)
        self.analysis.set_analyzer_enabled("digit_analysis", self.settings.enable_digit_analysis)

    def _init_strategy_platform(self):
        """Register all marketplace strategies into the registry."""
        for meta_info in self.strategy_marketplace.list_all():
            strategy = self.strategy_marketplace.create_strategy(meta_info["name"])
            if strategy:
                self.strategy_registry.register(meta_info["name"], strategy)
        # Activate unified by default if available
        if self.strategy_registry.has("unified"):
            self.strategy_registry.set_active("unified")
        elif self.strategy_registry.has("grid"):
            self.strategy_registry.set_active("grid")
        logger.info(
            "Strategy platform: %d strategies registered, active=%s",
            len(self.strategy_registry.list_all()),
            self.strategy_registry.active_name,
        )

    def switch_strategy(self, name: str) -> bool:
        """Hot-swap the active trading strategy at runtime."""
        success = self.strategy_marketplace.activate(name)
        if success:
            logger.info("Switched strategy to: %s", name)
        return success

    def get_strategy_platform_state(self) -> Dict[str, Any]:
        """Get strategy platform state for the dashboard."""
        return {
            "marketplace": self.strategy_marketplace.get_state(),
            "registry": self.strategy_registry.get_state(),
        }
    
    async def _handle_tick_message(self, message: Dict[str, Any]):
        tick = message.get("tick") if isinstance(message, dict) else None
        if tick:
            await self.process_tick(tick)

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
        """Connect, discover active markets, then hydrate account state."""
        if await self.connection.connect():
            try:
                await self.market.discover_markets(self.connection)
            except Exception as exc:
                logger.warning("Active market discovery failed: %s; retaining configured symbols", exc)
            await self.account.update_balance(self.connection)
            return True
        return False
    
    async def subscribe_to_market(self):
        """Subscribe the canonical Deriv connection to the active market."""
        await self.connection.subscribe(
            {"ticks": self.market.get_current_market(), "subscribe": 1},
            "tick",
            self._handle_tick_message,
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
        self.monitor.active_trades = {}
        self._canonical_trades.clear()
        self._pending_intel = {}
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
        price_str = format(self.current_price, ".8f").rstrip("0")
        last_digit = int(price_str[-1]) if price_str and price_str[-1].isdigit() else 0
        self.last_20_digits.append(last_digit)
        if len(self.last_20_digits) > 100:
            self.last_20_digits = self.last_20_digits[-100:]
        self.digit_history.append(last_digit)
        self._last_tick_epoch = float(tick_data.get("epoch") or time.time())
        
        # Run analysis without execution-result caching. A stale AI decision can
        # become a real-money order within seconds on synthetic indices.
        analysis_data = {
            "last_20_digits": self.last_20_digits,
            "price_history": self.price_history,
            "current_price": self.current_price,
            "market": self.market.get_current_market(),
            "markets": self.market.get_all_markets()
        }
        
        self.metrics.start_timer("analysis")
        self.analysis.get_comprehensive_analysis(analysis_data)
        self.best_prediction = self.analysis.get_best_prediction()
        self.metrics.stop_timer("analysis")
        
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
        """Run the canonical AI -> quote -> risk -> buy path.

        Live execution fails closed: intelligence errors, stale ticks, missing
        proposals, insufficient edge, or risk violations never fall back to a
        legacy confidence-only trade.
        """
        async with self._decision_lock:
            gate = self.live_certificate_gate.status(
                live_enabled=self.settings.live_trading_enabled,
                confirmation=os.getenv("LIVE_TRADING_CONFIRMATION", ""),
            )
            if not gate["allowed"]:
                logger.info("Live trading blocked by Phase-5 certificate gate: %s", gate["reason"])
                return None
            if not self.connection.authorized or not self.connection.is_connected():
                return None
            if not self.best_prediction:
                return None

            symbol = self.market.get_current_market()
            now = time.time()
            if now - self._last_tick_epoch > self.settings.decision_ttl_seconds:
                logger.info("Trade blocked: stale market data")
                return None
            last_trade = self._last_trade_at_by_symbol.get(symbol, 0.0)
            if now - last_trade < self.settings.per_symbol_cooldown_seconds:
                return None
            if len(self.deriv_execution.get_open_contracts()) >= self.settings.max_open_contracts:
                return None

            active_intel = self.research if self.research is not None else self.intelligence
            if active_intel is None:
                logger.warning("Trade blocked: no intelligence pipeline loaded")
                return None

            try:
                hour = datetime.now(timezone.utc).hour
                intel = active_intel.evaluate_tick(
                    price_history=list(self.price_history),
                    digit_history=list(self.digit_history),
                    analyzer_output=self.analysis.analysis_result or {},
                    market=symbol,
                    hour=hour,
                )
            except Exception:
                logger.exception("AI pipeline failed; live trading remains blocked")
                return None

            if not intel or intel.get("decision") != "TRADE":
                return None

            # The analysis layer must nominate a real contract space.
            contract_type = str(intel.get("contract_type") or self.best_prediction.get("type") or "").upper()
            direction = str(intel.get("direction") or self.best_prediction.get("direction") or "").upper()
            if contract_type in {"CONSENSUS", ""}:
                # Legacy consensus is not a broker contract. Map only an explicit
                # rise/fall directional result; digit contracts need explicit type.
                if direction in {"CALL", "PUT"}:
                    contract_type = direction
                else:
                    logger.info("Trade blocked: AI did not return an executable contract type")
                    return None

            trade_amount = float(intel.get("size") or self.settings.base_amount)
            balance = float(self.account.get_balance() or 0.0)
            max_stake = balance * self.settings.max_stake_pct_equity if balance > 0 else 0.0
            if max_stake > 0:
                trade_amount = min(trade_amount, max_stake)
            if trade_amount <= 0:
                logger.info("Trade blocked: computed stake is not positive")
                return None

            currency = self.account.get_currency()
            prediction = str(intel.get("prediction") or direction or "") or None
            barrier = intel.get("barrier")

            # Ask Deriv for the real quote after applying the equity cap.
            try:
                proposal = await self.deriv_execution.get_proposal(
                    symbol=symbol, contract_type=contract_type, amount=trade_amount,
                    currency=currency, duration=int(intel.get("duration") or 1),
                    duration_unit=str(intel.get("duration_unit") or "t"),
                    barrier=str(barrier) if barrier is not None else None,
                    prediction=prediction,
                )
            except Exception as exc:
                logger.warning("Trade blocked: proposal failed: %s", exc)
                return None

            raw_conf = float(intel.get("win_probability") or intel.get("probability") or (float(self.best_prediction.get("confidence", 0)) / 100.0))
            raw_conf = max(0.0, min(1.0, raw_conf))
            calibration = self.probability_calibrator.transform(
                raw_conf, market=symbol, contract_type=contract_type,
                duration=int(intel.get("duration") or 1),
                regime=str(intel.get("regime", {}).get("regime", "UNKNOWN")) if isinstance(intel.get("regime"), dict) else str(intel.get("regime", "UNKNOWN")),
            )
            # Phase 2 live policy: no calibrated artifact means no live trade.
            if self.settings.live_trading_enabled and getattr(self.settings, "require_calibrated_probability", True) and not calibration.calibrated:
                logger.info("Trade blocked: no valid calibration artifact for %s", calibration.context)
                return None
            win_probability = calibration.probability
            approval = self.trade_approver.approve(
                win_probability=win_probability,
                payout=proposal.payout,
                stake=proposal.ask_price,
                min_expected_value=self.settings.min_expected_value,
                min_probability=self.settings.min_confidence / 100.0,
                model_ready=bool(intel.get("pipeline_ok", True)),
                market_data_fresh=(time.time() - self._last_tick_epoch) <= self.settings.decision_ttl_seconds,
            )
            if not approval.approved:
                logger.info("Trade blocked by final approval gate: %s", "; ".join(approval.reasons))
                return None
            ev = approval.expected_value

            can_trade, reason = self.risk_manager.check_risk_limits(
                self.stats_manager.get_stats()["session_pnl"],
                self.risk_manager.get_consecutive_losses(),
                self.settings.to_dict(),
            )
            if not can_trade:
                if "kill switch" in reason.lower():
                    self.bot_status = "STOPPED"
                return None

            try:
                trade = await self.deriv_execution.buy(proposal, max_price=proposal.ask_price)
            except Exception as exc:
                logger.warning("Buy failed: %s", exc)
                return None

            self._last_trade_at_by_symbol[symbol] = time.time()
            contract_id = trade.contract_id

            self._pending_intel = getattr(self, "_pending_intel", {})
            self._pending_intel[contract_id] = {
                "analyzer_output": self.analysis.analysis_result or {},
                "amount": trade.buy_price, "market": symbol,
                "direction": direction, "type": contract_type,
                "prediction": prediction, "confidence": win_probability * 100,
                "entry_price": self.current_price,
                "regime": str(intel.get("regime", {}).get("regime", "unknown")) if isinstance(intel.get("regime"), dict) else str(intel.get("regime", "unknown")),
                "entropy": float(intel.get("entropy", self.analysis.get_market_entropy())),
                "volatility": 0.0,
                "proposal": {"id": proposal.id, "ask_price": proposal.ask_price, "payout": proposal.payout, "ev": ev},
                "calibration": {"raw_probability": raw_conf, "calibrated_probability": win_probability, "source": calibration.source, "sample_size": calibration.sample_size, "context": calibration.context},
            }
            self._canonical_trades[contract_id] = {
                "id": contract_id,
                "market": symbol,
                "type": contract_type,
                "direction": direction,
                "amount": trade.buy_price,
                "confidence": win_probability * 100,
                "entry_price": trade.entry_spot if trade.entry_spot is not None else self.current_price,
                "buy_price": trade.buy_price,
                "payout": trade.payout,
                "proposal_id": proposal.id,
                "expected_value": ev,
                "prediction": prediction,
                "entry_time": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self.monitor.add_trade(contract_id, self._canonical_trades[contract_id])

            # Persistent monitoring is tied to the contract stream, not a fixed sleep.
            self._pending_contract_tasks[contract_id] = asyncio.create_task(
                self._monitor_deriv_contract(contract_id),
                name=f"contract-{contract_id}",
            )
            logger.info(
                "TRADE %s type=%s p=%.3f payout=%.4f stake=%.4f EV=%.5f",
                contract_id, contract_type, win_probability, proposal.payout, trade.buy_price, ev,
            )
            return contract_id

    async def _monitor_deriv_contract(self, contract_id: str):
        try:
            contract = await self.deriv_execution.watch_contract(contract_id)
            profit = float(contract.get("profit", 0) or 0)
            await self._on_trade_complete(contract_id, profit)
        except Exception as exc:
            logger.error("Contract monitoring failed for %s: %s", contract_id, exc)
        finally:
            self._pending_contract_tasks.pop(contract_id, None)

    async def _on_trade_complete(self, contract_id: str, profit: float):
        """Callback when trade completes with database persistence and structured logging"""
        self.metrics.start_timer("trade_completion")
        
        # Update statistics
        self.stats_manager.update_stats(profit)
        self.stats_manager.update_averages(self.monitor.get_all_trade_history())
        
        # Update risk manager
        self.risk_manager.update_consecutive_losses(profit)
        
        # Complete trade in the canonical monitor/store.
        trade_data = self._canonical_trades.pop(contract_id, None) or self.executor.get_trade(contract_id)
        if trade_data:
            if contract_id in self.monitor.active_trades:
                self.monitor.complete_trade(contract_id, profit)

            trade_data["profit"] = profit
            trade_data["exit_price"] = self.current_price
            trade_data["completed_at"] = datetime.now(timezone.utc).isoformat()
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

            # ── Feed outcome to intelligence layer ───────────────────
            if self.intelligence or self.research:
                try:
                    pending_intel = getattr(self, "_pending_intel", {})
                    intel_data = pending_intel.pop(contract_id, {})
                    if intel_data:
                        price_str = f"{self.current_price:.4f}"
                        last_digit = int(price_str[-1]) if price_str[-1].isdigit() else 0
                        pnl_pct = (profit / max(intel_data.get("amount", 1.0), 0.01)) * 100

                        trade_record = TradeRecord(
                            trade_id=contract_id,
                            timestamp=datetime.now(timezone.utc).timestamp(),
                            market=intel_data.get("market", ""),
                            direction=intel_data.get("direction", ""),
                            amount=intel_data.get("amount", 1.0),
                            entry_price=intel_data.get("entry_price", 0),
                            exit_price=self.current_price,
                            profit=profit,
                            pnl_pct=pnl_pct,
                            confidence=intel_data.get("confidence", 0),
                            analyzer_outputs=intel_data.get("analyzer_output", {}),
                            market_features={
                                "regime": intel_data.get("regime", "UNKNOWN"),
                                "entropy": intel_data.get("entropy", 3.0),
                                "volatility": intel_data.get("volatility", 0.0),
                            },
                            regime=intel_data.get("regime", "UNKNOWN"),
                            entropy=intel_data.get("entropy", 3.0),
                            volatility=intel_data.get("volatility", 0.0),
                            digit_pattern=list(self.last_20_digits)[-10:],
                            outcome="WIN" if profit > 0 else ("BREAK_EVEN" if profit == 0 else "LOSS"),
                            duration_seconds=0,
                            metadata={},
                        )
                        # Record in both intelligence layers
                        if self.intelligence:
                            self.intelligence.record_trade_outcome(
                                trade_record=trade_record,
                                analyzer_output=intel_data.get("analyzer_output", {}),
                            )
                        if self.research:
                            self.research.record_trade_outcome(
                                trade_record=trade_record,
                                analyzer_output=intel_data.get("analyzer_output", {}),
                            )
                except Exception as ie:
                    logger.warning("Intelligence outcome recording failed: %s", ie)
            
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
            
            if self.executor.get_trade(contract_id):
                self.executor.remove_trade(contract_id)
        
        # Update balance
        await self.account.update_balance(self.connection)
        
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
        """Compatibility loop; DerivConnection owns socket receive handling."""
        while self.connection.connected and not self.connection._stopping:
            await asyncio.sleep(1)

    async def run(self):
        """Keep the canonical Deriv connection alive for the service lifetime."""
        while not self.connection._stopping:
            if not self.connection.is_connected():
                connected = await self.connect()
                if connected:
                    await self.subscribe_to_market()
                else:
                    await asyncio.sleep(5)
                    continue
            await asyncio.sleep(1)

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
            "intelligence": self.intelligence.get_intelligence_state() if self.intelligence else None,
            "research": self.research.get_intelligence_state() if self.research else None,
            "strategy_platform": self.get_strategy_platform_state(),
            "performance": {
                "cache": self.cache.get_stats(),
                "metrics": self.metrics.get_summary(),
                "connection": {
                    "reconnect_attempts": self.connection.reconnect_attempts
                }
            }
        }
