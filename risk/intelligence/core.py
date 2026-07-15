"""
Core Risk Intelligence Engine
=============================

Main orchestrator for institutional-grade risk management.
"""

import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import numpy as np

from .scenarios import ScenarioAnalyzer, StressTestRunner
from .sensitivity import SensitivityAnalyzer
from .drawdown import DrawdownAnalyzer
from .shortfall import ExpectedShortfallCalculator
from .allocation import CapitalAllocator
from .exposure import AdaptiveExposureManager
from .position_sizing import ConfidenceAwareSizer
from .concentration import ConcentrationAnalyzer
from .circuit_breaker import CircuitBreaker, KillSwitch
from .recovery import RecoveryManager
from .risk_score import RiskScoreCalculator
from .dashboard import RiskDashboard
from .registry import RiskRegistry

logger = logging.getLogger(__name__)


class SystemState(Enum):
    """System operational state"""
    NORMAL = "normal"
    CAUTION = "caution"
    ELEVATED = "elevated"
    CRITICAL = "critical"
    RECOVERY = "recovery"
    KILLED = "killed"


@dataclass
class RiskMetrics:
    """Current risk metrics snapshot"""
    timestamp: datetime
    portfolio_value: float
    daily_pnl: float
    daily_return: float
    unrealized_pnl: float
    realized_pnl: float
    max_drawdown: float
    current_drawdown: float
    var_95: float  # Value at Risk (95%)
    cvar_95: float  # Conditional VaR (95%)
    volatility_30d: float
    sharpe_ratio: float
    risk_score: int  # 0-100
    system_state: SystemState
    positions: List[Dict[str, Any]]
    concentration_risk: float
    exposure_ratio: float
    margin_utilization: float


@dataclass
class RiskLimits:
    """Configurable risk limits"""
    max_daily_loss: float = 0.02  # 2% of portfolio
    max_drawdown: float = 0.10  # 10% max drawdown
    max_position_size: float = 0.20  # 20% max per position
    max_concentration: float = 0.40  # 40% max in single asset
    max_var_95: float = 0.03  # 3% VaR limit
    max_volatility: float = 0.25  # 25% annualized vol
    circuit_breaker_threshold: float = 0.05  # 5% loss triggers breaker
    kill_switch_threshold: float = 0.15  # 15% loss triggers kill switch
    min_confidence_to_trade: float = 0.5
    max_leverage: float = 1.0


@dataclass
class Position:
    """Trading position"""
    id: str
    symbol: str
    direction: str  # LONG or SHORT
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    confidence: float
    risk_contribution: float
    timestamp: datetime


class RiskIntelligenceEngine:
    """
    Core Risk Intelligence Engine
    
    Enterprise-grade risk management system that coordinates all risk
    components and provides unified risk oversight.
    """
    
    def __init__(
        self,
        initial_capital: float = 100000.0,
        limits: Optional[RiskLimits] = None,
        db_path: str = "data/risk_intelligence.db"
    ):
        self.initial_capital = initial_capital
        self.limits = limits or RiskLimits()
        self.db_path = db_path
        
        # Initialize components
        self.registry = RiskRegistry(db_path)
        self.scenario_analyzer = ScenarioAnalyzer()
        self.stress_tester = StressTestRunner()
        self.sensitivity_analyzer = SensitivityAnalyzer()
        self.drawdown_analyzer = DrawdownAnalyzer()
        self.shortfall_calculator = ExpectedShortfallCalculator()
        self.capital_allocator = CapitalAllocator()
        self.exposure_manager = AdaptiveExposureManager(self.limits)
        self.position_sizer = ConfidenceAwareSizer(self.limits)
        self.concentration_analyzer = ConcentrationAnalyzer(self.limits)
        self.circuit_breaker = CircuitBreaker(self.limits)
        self.kill_switch = KillSwitch(self.limits)
        self.recovery_manager = RecoveryManager()
        self.risk_score_calculator = RiskScoreCalculator(self.limits)
        self.dashboard = RiskDashboard(self.registry)
        
        # State
        self._positions: Dict[str, Position] = {}
        self._portfolio_value = initial_capital
        self._peak_value = initial_capital
        self._daily_pnl = 0.0
        self._system_state = SystemState.NORMAL
        self._is_paused = False
        self._kill_switch_triggered = False
        
        # History
        self._equity_curve: List[float] = [initial_capital]
        self._drawdown_history: List[float] = [0.0]
        self._risk_score_history: List[int] = []
        
        # Ensure database
        self._ensure_database()
        
        logger.info(f"RiskIntelligenceEngine initialized with capital={initial_capital}")
    
    def _ensure_database(self) -> None:
        """Initialize database tables"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Risk metrics history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS risk_metrics (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                portfolio_value REAL,
                daily_pnl REAL,
                daily_return REAL,
                max_drawdown REAL,
                current_drawdown REAL,
                var_95 REAL,
                cvar_95 REAL,
                volatility_30d REAL,
                sharpe_ratio REAL,
                risk_score INTEGER,
                system_state TEXT,
                concentration_risk REAL,
                exposure_ratio REAL,
                margin_utilization REAL
            )
        """)
        
        # Positions history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id TEXT PRIMARY KEY,
                symbol TEXT,
                direction TEXT,
                size REAL,
                entry_price REAL,
                exit_price REAL,
                pnl REAL,
                confidence REAL,
                open_time TEXT,
                close_time TEXT
            )
        """)
        
        # Events (breakers, kills, etc.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS risk_events (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                severity TEXT,
                description TEXT,
                data TEXT
            )
        """)
        
        # Circuit breaker state
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS circuit_breakers (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                trigger_type TEXT,
                triggered_at REAL,
                reset_at REAL,
                auto_reset BOOLEAN
            )
        """)
        
        conn.commit()
        conn.close()
    
    def add_position(
        self,
        symbol: str,
        direction: str,
        size: float,
        entry_price: float,
        confidence: float
    ) -> Tuple[bool, str]:
        """
        Add a new position after risk checks.
        
        Returns:
            Tuple of (accepted, reason)
        """
        # Check kill switch
        if self._kill_switch_triggered:
            return False, "Kill switch is active - no new positions allowed"
        
        # Check circuit breaker
        if self.circuit_breaker.is_tripped():
            return False, "Circuit breaker is tripped"
        
        # Check system state
        if self._system_state in [SystemState.CRITICAL, SystemState.KILLED]:
            return False, f"System in {self._system_state.value} state"
        
        # Check confidence
        if confidence < self.limits.min_confidence_to_trade:
            return False, f"Confidence {confidence:.2f} below minimum {self.limits.min_confidence_to_trade}"
        
        # Calculate position risk
        position_value = size * entry_price
        position_ratio = position_value / self._portfolio_value
        
        # Check position size limit
        if position_ratio > self.limits.max_position_size:
            return False, f"Position size {position_ratio:.1%} exceeds limit {self.limits.max_position_size:.1%}"
        
        # Check concentration
        concentration_ok, concentration_msg = self.concentration_analyzer.check_addition(
            symbol, position_value, self._positions
        )
        if not concentration_ok:
            return False, concentration_msg
        
        # Create position
        position = Position(
            id=str(uuid4()),
            symbol=symbol,
            direction=direction,
            size=size,
            entry_price=entry_price,
            current_price=entry_price,
            unrealized_pnl=0.0,
            confidence=confidence,
            risk_contribution=position_value / self._portfolio_value,
            timestamp=datetime.now()
        )
        
        self._positions[position.id] = position
        self._log_event("POSITION_OPENED", "INFO", f"Opened {direction} {symbol}")
        
        logger.info(f"Position added: {symbol} {direction} size={size}")
        return True, "Position accepted"
    
    def update_position(
        self,
        position_id: str,
        current_price: float
    ) -> Optional[float]:
        """Update position with current price, return unrealized PnL"""
        if position_id not in self._positions:
            return None
        
        position = self._positions[position_id]
        position.current_price = current_price
        
        if position.direction == "LONG":
            position.unrealized_pnl = (current_price - position.entry_price) * position.size
        else:
            position.unrealized_pnl = (position.entry_price - current_price) * position.size
        
        return position.unrealized_pnl
    
    def close_position(
        self,
        position_id: str,
        exit_price: float
    ) -> Tuple[bool, float]:
        """Close a position"""
        if position_id not in self._positions:
            return False, 0.0
        
        position = self._positions.pop(position_id)
        
        if position.direction == "LONG":
            pnl = (exit_price - position.entry_price) * position.size
        else:
            pnl = (position.entry_price - exit_price) * position.size
        
        # Update portfolio
        self._portfolio_value += pnl
        self._daily_pnl += pnl
        self._update_peak()
        
        # Record position
        self._record_position(position, exit_price, pnl)
        self._log_event("POSITION_CLOSED", "INFO", f"Closed {position.symbol} PnL={pnl:.2f}")
        
        logger.info(f"Position closed: {position.symbol} PnL={pnl:.2f}")
        return True, pnl
    
    def calculate_position_size(
        self,
        symbol: str,
        confidence: float,
        entry_price: float,
        stop_loss_pct: float = 0.02
    ) -> float:
        """Calculate recommended position size"""
        return self.position_sizer.calculate(
            portfolio_value=self._portfolio_value,
            confidence=confidence,
            entry_price=entry_price,
            stop_loss_pct=stop_loss_pct,
            current_drawdown=self.drawdown_analyzer.current_drawdown,
            system_state=self._system_state
        )
    
    def get_adaptive_exposure_limit(self) -> float:
        """Get current adaptive exposure limit"""
        return self.exposure_manager.get_exposure_limit(
            current_drawdown=self.drawdown_analyzer.current_drawdown,
            volatility=self.shortfall_calculator.recent_volatility,
            system_state=self._system_state
        )
    
    def run_risk_assessment(self) -> RiskMetrics:
        """Run complete risk assessment"""
        # Update metrics
        self._update_drawdown()
        self._update_volatility()
        
        # Calculate metrics
        var_95, cvar_95 = self.shortfall_calculator.calculate(
            positions=list(self._positions.values()),
            portfolio_value=self._portfolio_value,
            confidence=0.95
        )
        
        # Calculate concentration
        concentration = self.concentration_analyzer.calculate(
            list(self._positions.values()),
            self._portfolio_value
        )
        
        # Update circuit breaker
        self._check_circuit_breaker()
        
        # Update kill switch
        self._check_kill_switch()
        
        # Update system state
        self._update_system_state()
        
        # Calculate risk score
        risk_score = self.risk_score_calculator.calculate(
            drawdown=self.drawdown_analyzer.current_drawdown,
            volatility=self.shortfall_calculator.recent_volatility,
            concentration=concentration,
            var_95=var_95,
            system_state=self._system_state,
            circuit_breaker_tripped=self.circuit_breaker.is_tripped(),
            positions=list(self._positions.values())
        )
        
        # Create metrics
        metrics = RiskMetrics(
            timestamp=datetime.now(),
            portfolio_value=self._portfolio_value,
            daily_pnl=self._daily_pnl,
            daily_return=self._daily_pnl / self._peak_value if self._peak_value > 0 else 0,
            unrealized_pnl=sum(p.unrealized_pnl for p in self._positions.values()),
            realized_pnl=self._portfolio_value - self.initial_capital - sum(p.unrealized_pnl for p in self._positions.values()),
            max_drawdown=self.drawdown_analyzer.max_drawdown,
            current_drawdown=self.drawdown_analyzer.current_drawdown,
            var_95=var_95,
            cvar_95=cvar_95,
            volatility_30d=self.shortfall_calculator.recent_volatility,
            sharpe_ratio=self._calculate_sharpe(),
            risk_score=risk_score,
            system_state=self._system_state,
            positions=[{
                "id": p.id,
                "symbol": p.symbol,
                "direction": p.direction,
                "size": p.size,
                "entry_price": p.entry_price,
                "current_price": p.current_price,
                "unrealized_pnl": p.unrealized_pnl,
                "confidence": p.confidence
            } for p in self._positions.values()],
            concentration_risk=concentration,
            exposure_ratio=self._calculate_exposure_ratio(),
            margin_utilization=self._calculate_margin_utilization()
        )
        
        # Record metrics
        self._record_metrics(metrics)
        self._risk_score_history.append(risk_score)
        
        # Update dashboard
        self.dashboard.update(metrics)
        
        return metrics
    
    def run_stress_test(self) -> Dict[str, Any]:
        """Run comprehensive stress test"""
        return self.stress_tester.run_full_stress_test(
            portfolio_value=self._portfolio_value,
            positions=list(self._positions.values()),
            initial_capital=self.initial_capital
        )
    
    def get_scenario_analysis(self, symbol: str) -> Dict[str, Any]:
        """Get scenario analysis for a symbol"""
        return self.scenario_analyzer.analyze(
            symbol=symbol,
            positions=list(self._positions.values()),
            portfolio_value=self._portfolio_value
        )
    
    def get_sensitivity_analysis(self, symbol: str) -> Dict[str, Any]:
        """Get sensitivity analysis for a symbol"""
        return self.sensitivity_analyzer.analyze(
            symbol=symbol,
            positions=list(self._positions.values()),
            portfolio_value=self._portfolio_value
        )
    
    def can_trade(self, confidence: float = 0.5) -> Tuple[bool, str]:
        """Check if trading is allowed"""
        if self._kill_switch_triggered:
            return False, "Kill switch active"
        
        if self.circuit_breaker.is_tripped():
            return False, "Circuit breaker tripped"
        
        if self._system_state == SystemState.KILLED:
            return False, "System killed"
        
        if self._system_state in [SystemState.CRITICAL, SystemState.RECOVERY]:
            if confidence < 0.8:
                return False, f"Confidence {confidence:.2f} insufficient for {self._system_state.value} state"
        
        if self.drawdown_analyzer.current_drawdown > self.limits.max_drawdown * 0.8:
            return False, f"Drawdown {self.drawdown_analyzer.current_drawdown:.1%} approaching limit"
        
        return True, "Trading allowed"
    
    def reset_kill_switch(self, require_manual_reset: bool = True) -> bool:
        """Reset kill switch (requires explicit reset)"""
        if self._kill_switch_triggered:
            if not require_manual_reset:
                return False
            
            self._kill_switch_triggered = False
            self._system_state = SystemState.RECOVERY
            self.recovery_manager.start_recovery()
            self._log_event("KILL_SWITCH_RESET", "WARNING", "Kill switch manually reset")
            logger.warning("Kill switch reset - system entering recovery mode")
            return True
        
        return False
    
    def pause_trading(self, reason: str = "Manual pause") -> None:
        """Pause all trading"""
        self._is_paused = True
        self._log_event("TRADING_PAUSED", "WARNING", reason)
        logger.warning(f"Trading paused: {reason}")
    
    def resume_trading(self) -> bool:
        """Resume trading if conditions allow"""
        if self._kill_switch_triggered:
            return False
        
        if self._system_state == SystemState.KILLED:
            return False
        
        self._is_paused = False
        self._log_event("TRADING_RESUMED", "INFO", "Trading resumed")
        logger.info("Trading resumed")
        return True
    
    def get_state(self) -> Dict[str, Any]:
        """Get current system state"""
        return {
            "state": self._system_state.value,
            "portfolio_value": self._portfolio_value,
            "peak_value": self._peak_value,
            "current_drawdown": self.drawdown_analyzer.current_drawdown,
            "max_drawdown": self.drawdown_analyzer.max_drawdown,
            "daily_pnl": self._daily_pnl,
            "positions_count": len(self._positions),
            "is_paused": self._is_paused,
            "kill_switch_triggered": self._kill_switch_triggered,
            "circuit_breaker_tripped": self.circuit_breaker.is_tripped(),
            "risk_score": self.risk_score_history[-1] if self.risk_score_history else 50,
            "recent_risk_scores": self._risk_score_history[-20:]
        }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard data for visualization"""
        return self.dashboard.get_current_state()
    
    def _update_drawdown(self) -> None:
        """Update drawdown metrics"""
        self._update_peak()
        self.drawdown_analyzer.update(self._portfolio_value, self._peak_value)
        self._drawdown_history.append(self.drawdown_analyzer.current_drawdown)
    
    def _update_peak(self) -> None:
        """Update peak portfolio value"""
        if self._portfolio_value > self._peak_value:
            self._peak_value = self._portfolio_value
        self._equity_curve.append(self._portfolio_value)
    
    def _update_volatility(self) -> None:
        """Update volatility metrics"""
        if len(self._equity_curve) > 2:
            returns = np.diff(self._equity_curve) / self._equity_curve[:-1]
            self.shortfall_calculator.update_volatility(returns)
    
    def _check_circuit_breaker(self) -> None:
        """Check and update circuit breaker status"""
        daily_loss_ratio = abs(self._daily_pnl) / self._peak_value if self._peak_value > 0 else 0
        
        if self._daily_pnl < -self.limits.circuit_breaker_threshold * self._peak_value:
            if not self.circuit_breaker.is_tripped():
                self.circuit_breaker.trip(
                    trigger_type="daily_loss",
                    triggered_at=self._daily_pnl
                )
                self._log_event("CIRCUIT_BREAKER_TRIPPED", "ERROR", 
                              f"Daily loss {self._daily_pnl:.2f} exceeded threshold")
                self._system_state = SystemState.ELEVATED
    
    def _check_kill_switch(self) -> None:
        """Check and update kill switch status"""
        drawdown = self.drawdown_analyzer.current_drawdown
        
        if drawdown >= self.limits.kill_switch_threshold:
            if not self._kill_switch_triggered:
                self._kill_switch_triggered = True
                self.kill_switch.trigger(reason="drawdown", drawdown=drawdown)
                self._system_state = SystemState.KILLED
                self._log_event("KILL_SWITCH_TRIGGERED", "CRITICAL",
                              f"Drawdown {drawdown:.1%} exceeded kill switch threshold")
                logger.critical(f"KILL SWITCH TRIGGERED - Drawdown: {drawdown:.1%}")
    
    def _update_system_state(self) -> None:
        """Update system state based on conditions"""
        if self._kill_switch_triggered:
            self._system_state = SystemState.KILLED
            return
        
        drawdown = self.drawdown_analyzer.current_drawdown
        risk_score = self._risk_score_history[-1] if self._risk_score_history else 50
        
        if self.recovery_manager.in_recovery:
            self._system_state = SystemState.RECOVERY
        elif drawdown > self.limits.max_drawdown * 0.8 or risk_score > 80:
            self._system_state = SystemState.CRITICAL
        elif drawdown > self.limits.max_drawdown * 0.5 or risk_score > 60:
            self._system_state = SystemState.ELEVATED
        elif drawdown > self.limits.max_drawdown * 0.2 or risk_score > 40:
            self._system_state = SystemState.CAUTION
        else:
            self._system_state = SystemState.NORMAL
    
    def _calculate_sharpe(self) -> float:
        """Calculate Sharpe ratio"""
        if len(self._equity_curve) < 30:
            return 0.0
        
        returns = np.diff(self._equity_curve) / self._equity_curve[:-1]
        if len(returns) < 2:
            return 0.0
        
        mean_return = np.mean(returns) * 252  # Annualized
        std_return = np.std(returns) * np.sqrt(252)  # Annualized
        
        if std_return == 0:
            return 0.0
        
        return mean_return / std_return
    
    def _calculate_exposure_ratio(self) -> float:
        """Calculate current exposure ratio"""
        total_exposure = sum(
            p.size * p.current_price for p in self._positions.values()
        )
        return total_exposure / self._portfolio_value if self._portfolio_value > 0 else 0
    
    def _calculate_margin_utilization(self) -> float:
        """Calculate margin utilization (simplified)"""
        # Simplified - would integrate with actual broker
        return self._calculate_exposure_ratio() * 0.5  # Assume 50% margin requirement
    
    def _record_metrics(self, metrics: RiskMetrics) -> None:
        """Record metrics to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO risk_metrics (
                id, timestamp, portfolio_value, daily_pnl, daily_return,
                max_drawdown, current_drawdown, var_95, cvar_95,
                volatility_30d, sharpe_ratio, risk_score, system_state,
                concentration_risk, exposure_ratio, margin_utilization
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid4()),
            metrics.timestamp.isoformat(),
            metrics.portfolio_value,
            metrics.daily_pnl,
            metrics.daily_return,
            metrics.max_drawdown,
            metrics.current_drawdown,
            metrics.var_95,
            metrics.cvar_95,
            metrics.volatility_30d,
            metrics.sharpe_ratio,
            metrics.risk_score,
            metrics.system_state.value,
            metrics.concentration_risk,
            metrics.exposure_ratio,
            metrics.margin_utilization
        ))
        
        conn.commit()
        conn.close()
    
    def _record_position(
        self,
        position: Position,
        exit_price: float,
        pnl: float
    ) -> None:
        """Record closed position to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO positions (
                id, symbol, direction, size, entry_price, exit_price,
                pnl, confidence, open_time, close_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            position.id,
            position.symbol,
            position.direction,
            position.size,
            position.entry_price,
            exit_price,
            pnl,
            position.confidence,
            position.timestamp.isoformat(),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _log_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        data: Optional[Dict] = None
    ) -> None:
        """Log risk event to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO risk_events (
                id, timestamp, event_type, severity, description, data
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            str(uuid4()),
            datetime.now().isoformat(),
            event_type,
            severity,
            description,
            json.dumps(data) if data else None
        ))
        
        conn.commit()
        conn.close()
    
    def reset(self) -> None:
        """Reset engine state"""
        self._positions.clear()
        self._portfolio_value = self.initial_capital
        self._peak_value = self.initial_capital
        self._daily_pnl = 0.0
        self._system_state = SystemState.NORMAL
        self._is_paused = False
        self._kill_switch_triggered = False
        self._equity_curve = [self.initial_capital]
        self._drawdown_history = [0.0]
        self._risk_score_history = []
        
        self.drawdown_analyzer.reset()
        self.circuit_breaker.reset()
        self.recovery_manager.reset()
        
        logger.info("RiskIntelligenceEngine reset")
