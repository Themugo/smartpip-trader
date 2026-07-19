"""
Performance Analytics - Comprehensive Trading Analytics

Complete analytics system with:
- Equity curves
- Rolling returns
- Risk-adjusted metrics (Sharpe, Sortino, Calmar)
- Drawdown analysis
- Trade statistics
- Confidence calibration
- Decision quality metrics
"""

import json
import logging
import uuid
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import defaultdict
import numpy as np

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of performance metrics"""
    RETURN = "return"
    RISK = "risk"
    EFFICIENCY = "efficiency"
    TRADING = "trading"
    QUALITY = "quality"


@dataclass
class EquityPoint:
    """A single point on the equity curve"""
    timestamp: datetime
    equity: float
    drawdown: float = 0.0
    drawdown_pct: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "equity": self.equity,
            "drawdown": self.drawdown,
            "drawdown_pct": self.drawdown_pct,
        }


@dataclass
class EquityCurve:
    """Complete equity curve with analysis"""
    curve_id: str
    
    # Data
    points: List[EquityPoint] = field(default_factory=list)
    
    # Starting capital
    starting_capital: float = 1000.0
    
    # Current values
    current_equity: float = 1000.0
    peak_equity: float = 1000.0
    
    # Metadata
    strategy_id: str = ""
    period_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    period_end: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "curve_id": self.curve_id,
            "points": [p.to_dict() for p in self.points],
            "starting_capital": self.starting_capital,
            "current_equity": self.current_equity,
            "peak_equity": self.peak_equity,
            "strategy_id": self.strategy_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
        }
    
    def total_return(self) -> float:
        """Calculate total return"""
        return (self.current_equity - self.starting_capital) / self.starting_capital
    
    def annualized_return(self, periods_per_year: int = 252) -> float:
        """Calculate annualized return"""
        if not self.points or len(self.points) < 2:
            return 0.0
        
        total_return = self.total_return()
        num_years = len(self.points) / periods_per_year
        
        if num_years <= 0:
            return 0.0
        
        return (1 + total_return) ** (1 / num_years) - 1


@dataclass
class RollingWindow:
    """Rolling window metrics"""
    window_size: int  # e.g., 20 for 20-period rolling window
    window_type: str = "trades"  # "trades" or "time"
    
    # Rolling values
    returns: List[float] = field(default_factory=list)
    sharpe: List[float] = field(default_factory=list)
    volatility: List[float] = field(default_factory=list)
    drawdown: List[float] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "window_size": self.window_size,
            "window_type": self.window_type,
            "returns": self.returns,
            "sharpe": self.sharpe,
            "volatility": self.volatility,
            "drawdown": self.drawdown,
        }


@dataclass
class DrawdownAnalysis:
    """Detailed drawdown analysis"""
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    max_drawdown_duration: int = 0  # In periods
    
    # Current state
    current_drawdown: float = 0.0
    current_drawdown_pct: float = 0.0
    
    # Recovery
    recovery_factor: float = 0.0
    
    # History
    drawdown_events: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_drawdown": self.max_drawdown,
            "max_drawdown_pct": self.max_drawdown_pct,
            "max_drawdown_duration": self.max_drawdown_duration,
            "current_drawdown": self.current_drawdown,
            "current_drawdown_pct": self.current_drawdown_pct,
            "recovery_factor": self.recovery_factor,
            "drawdown_events": self.drawdown_events,
        }


@dataclass
class TradeStatistics:
    """Comprehensive trade statistics"""
    # Counts
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    # P&L
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_profit: float = 0.0
    
    # Averages
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_trade: float = 0.0
    
    # Ratios
    win_rate: float = 0.0
    loss_rate: float = 0.0
    win_loss_ratio: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    
    # Duration
    avg_trade_duration: float = 0.0  # In seconds
    min_trade_duration: float = 0.0
    max_trade_duration: float = 0.0
    
    # Distribution
    trade_pnl_distribution: Dict[str, int] = field(default_factory=dict)  # bins -> counts
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "gross_profit": self.gross_profit,
            "gross_loss": self.gross_loss,
            "net_profit": self.net_profit,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "avg_trade": self.avg_trade,
            "win_rate": self.win_rate,
            "loss_rate": self.loss_rate,
            "win_loss_ratio": self.win_loss_ratio,
            "profit_factor": self.profit_factor,
            "expectancy": self.expectancy,
            "avg_trade_duration": self.avg_trade_duration,
            "min_trade_duration": self.min_trade_duration,
            "max_trade_duration": self.max_trade_duration,
            "trade_pnl_distribution": self.trade_pnl_distribution,
        }


@dataclass
class RiskMetrics:
    """Risk-adjusted performance metrics"""
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    information_ratio: float = 0.0
    
    # Volatility
    annualized_volatility: float = 0.0
    downside_deviation: float = 0.0
    
    # VaR and CVaR
    value_at_risk_95: float = 0.0
    value_at_risk_99: float = 0.0
    conditional_var_95: float = 0.0
    
    # Beta (for comparison with benchmark)
    beta: float = 0.0
    alpha: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "calmar_ratio": self.calmar_ratio,
            "information_ratio": self.information_ratio,
            "annualized_volatility": self.annualized_volatility,
            "downside_deviation": self.downside_deviation,
            "value_at_risk_95": self.value_at_risk_95,
            "value_at_risk_99": self.value_at_risk_99,
            "conditional_var_95": self.conditional_var_95,
            "beta": self.beta,
            "alpha": self.alpha,
        }


@dataclass
class ConfidenceCalibration:
    """Confidence calibration metrics"""
    # Calibration data
    confidence_bins: List[float] = field(default_factory=list)  # e.g., [0.5, 0.6, 0.7, ...]
    actual_win_rates: List[float] = field(default_factory=list)
    predicted_confidences: List[float] = field(default_factory=list)
    
    # Calibration metrics
    calibration_error: float = 0.0  # Expected Calibration Error (ECE)
    brier_score: float = 0.0
    
    # Reliability
    reliability_score: float = 0.0  # 0-100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "confidence_bins": self.confidence_bins,
            "actual_win_rates": self.actual_win_rates,
            "predicted_confidences": self.predicted_confidences,
            "calibration_error": self.calibration_error,
            "brier_score": self.brier_score,
            "reliability_score": self.reliability_score,
        }


@dataclass
class DecisionQualityMetrics:
    """Metrics for decision quality analysis"""
    # Accuracy metrics
    overall_accuracy: float = 0.0
    balanced_accuracy: float = 0.0
    
    # Confusion matrix metrics
    true_positives: int = 0
    true_negatives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    
    # Derived metrics
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    
    # Specific metrics
    correlation_with_outcome: float = 0.0  # How well confidence correlates with actual outcome
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_accuracy": self.overall_accuracy,
            "balanced_accuracy": self.balanced_accuracy,
            "true_positives": self.true_positives,
            "true_negatives": self.true_negatives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "correlation_with_outcome": self.correlation_with_outcome,
        }


class PerformanceAnalytics:
    """
    Performance Analytics for comprehensive trading analysis.
    
    Features:
    - Equity curve generation and analysis
    - Rolling window metrics
    - Risk-adjusted performance metrics
    - Drawdown analysis
    - Trade statistics
    - Confidence calibration
    - Decision quality metrics
    """
    
    RISK_FREE_RATE = 0.05  # 5% annual
    
    def __init__(self, storage_path: str = "data/analytics"):
        self._storage_path = storage_path
        self._curves: Dict[str, EquityCurve] = {}
        
        import os
        os.makedirs(storage_path, exist_ok=True)
    
    # Equity Curve Analysis
    def generate_equity_curve(
        self,
        trades: List[Dict[str, Any]],
        starting_capital: float = 1000.0,
        strategy_id: str = "",
    ) -> EquityCurve:
        """Generate equity curve from trades"""
        curve = EquityCurve(
            curve_id=str(uuid.uuid4()),
            starting_capital=starting_capital,
            current_equity=starting_capital,
            peak_equity=starting_capital,
            strategy_id=strategy_id,
        )
        
        equity = starting_capital
        peak = starting_capital
        
        for trade in trades:
            # Get trade info
            timestamp = self._parse_timestamp(trade.get("timestamp") or trade.get("closed_at"))
            pnl = trade.get("pnl", 0)
            
            # Update equity
            equity += pnl
            curve.current_equity = equity
            
            # Track peak
            if equity > peak:
                peak = equity
            
            # Calculate drawdown
            drawdown = peak - equity
            drawdown_pct = (drawdown / peak * 100) if peak > 0 else 0
            
            # Add point
            point = EquityPoint(
                timestamp=timestamp,
                equity=equity,
                drawdown=drawdown,
                drawdown_pct=drawdown_pct,
            )
            curve.points.append(point)
            
            # Update peak
            curve.peak_equity = peak
        
        # Set period
        if curve.points:
            curve.period_start = curve.points[0].timestamp
            curve.period_end = curve.points[-1].timestamp
        
        self._curves[curve.curve_id] = curve
        return curve
    
    def _parse_timestamp(self, ts: Any) -> datetime:
        """Parse timestamp from various formats"""
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, str):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return datetime.now(timezone.utc)
    
    def get_equity_curve(self, curve_id: str) -> Optional[EquityCurve]:
        """Get equity curve by ID"""
        return self._curves.get(curve_id)
    
    # Rolling Metrics
    def calculate_rolling_metrics(
        self,
        trades: List[Dict[str, Any]],
        window_size: int = 20,
        window_type: str = "trades",
    ) -> RollingWindow:
        """Calculate rolling metrics over a window"""
        rolling = RollingWindow(
            window_size=window_size,
            window_type=window_type,
        )
        
        if not trades:
            return rolling
        
        # Extract returns
        returns = [t.get("pnl", 0) / t.get("amount", 1) for t in trades if t.get("amount", 0) > 0]
        
        if len(returns) < window_size:
            return rolling
        
        # Calculate rolling metrics
        for i in range(window_size, len(returns) + 1):
            window_returns = returns[i - window_size:i]
            
            # Rolling return
            rolling.returns.append(sum(window_returns))
            
            # Rolling volatility
            if len(window_returns) > 1:
                volatility = np.std(window_returns)
                rolling.volatility.append(volatility)
                
                # Rolling Sharpe
                mean_ret = np.mean(window_returns)
                if volatility > 0:
                    sharpe = (mean_ret - self.RISK_FREE_RATE / 252) / volatility * np.sqrt(252)
                    rolling.sharpe.append(sharpe)
                else:
                    rolling.sharpe.append(0.0)
            else:
                rolling.volatility.append(0.0)
                rolling.sharpe.append(0.0)
            
            # Rolling drawdown
            cumulative = np.cumsum(window_returns)
            peak = np.maximum.accumulate(cumulative)
            drawdown = (peak - cumulative) / peak if len(peak) > 0 and peak[-1] > 0 else 0
            rolling.drawdown.append(float(drawdown[-1]) if len(drawdown) > 0 else 0)
        
        return rolling
    
    # Risk Metrics
    def calculate_risk_metrics(
        self,
        trades: List[Dict[str, Any]],
        benchmark_returns: Optional[List[float]] = None,
        periods_per_year: int = 252,
    ) -> RiskMetrics:
        """Calculate risk-adjusted performance metrics"""
        metrics = RiskMetrics()
        
        if not trades:
            return metrics
        
        # Extract returns
        returns = [t.get("pnl", 0) / t.get("amount", 1) for t in trades if t.get("amount", 0) > 0]
        
        if len(returns) < 2:
            return metrics
        
        returns = np.array(returns)
        
        # Volatility
        metrics.annualized_volatility = float(np.std(returns) * np.sqrt(periods_per_year))
        
        # Sharpe Ratio
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return > 0:
            daily_rf = self.RISK_FREE_RATE / periods_per_year
            metrics.sharpe_ratio = float((mean_return - daily_rf) / std_return * np.sqrt(periods_per_year))
        
        # Sortino Ratio (downside deviation)
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 1:
            downside_dev = np.std(downside_returns)
            if downside_dev > 0:
                daily_rf = self.RISK_FREE_RATE / periods_per_year
                metrics.sortino_ratio = float((mean_return - daily_rf) / downside_dev * np.sqrt(periods_per_year))
                metrics.downside_deviation = float(downside_dev * np.sqrt(periods_per_year))
        
        # Calmar Ratio
        dd_analysis = self.analyze_drawdowns(trades)
        if dd_analysis.max_drawdown_pct != 0:
            total_return = np.sum(returns)
            num_years = len(returns) / periods_per_year
            if num_years > 0:
                annualized_return = total_return / num_years
                metrics.calmar_ratio = float(annualized_return / (dd_analysis.max_drawdown_pct / 100))
        
        # VaR and CVaR
        metrics.value_at_risk_95 = float(np.percentile(returns, 5))
        metrics.value_at_risk_99 = float(np.percentile(returns, 1))
        
        # Conditional VaR (Expected Shortfall)
        var_95 = np.percentile(returns, 5)
        cvar_95 = returns[returns <= var_95]
        if len(cvar_95) > 0:
            metrics.conditional_var_95 = float(np.mean(cvar_95))
        
        # Beta and Alpha (if benchmark provided)
        if benchmark_returns and len(benchmark_returns) == len(returns):
            benchmark = np.array(benchmark_returns)
            
            covariance = np.cov(returns, benchmark)[0, 1]
            benchmark_variance = np.var(benchmark)
            
            if benchmark_variance > 0:
                metrics.beta = float(covariance / benchmark_variance)
                metrics.alpha = float(mean_return - metrics.beta * np.mean(benchmark))
        
        return metrics
    
    # Drawdown Analysis
    def analyze_drawdowns(self, trades: List[Dict[str, Any]]) -> DrawdownAnalysis:
        """Analyze drawdowns in detail"""
        analysis = DrawdownAnalysis()
        
        if not trades:
            return analysis
        
        # Build equity curve
        equity = 1000.0
        peak = 1000.0
        current_drawdown = 0.0
        current_drawdown_pct = 0.0
        
        max_duration = 0
        current_duration = 0
        
        for trade in trades:
            pnl = trade.get("pnl", 0)
            equity += pnl
            
            if equity > peak:
                peak = equity
                current_duration = 0
            else:
                current_duration += 1
            
            dd = peak - equity
            dd_pct = (dd / peak * 100) if peak > 0 else 0
            
            if dd > analysis.max_drawdown:
                analysis.max_drawdown = dd
                analysis.max_drawdown_pct = dd_pct
                analysis.max_drawdown_duration = current_duration
            
            if current_duration > analysis.max_drawdown_duration:
                analysis.max_drawdown_duration = current_duration
        
        analysis.current_drawdown = peak - equity
        analysis.current_drawdown_pct = analysis.current_drawdown / peak * 100 if peak > 0 else 0
        
        # Recovery factor
        if analysis.max_drawdown > 0:
            total_profit = equity - 1000
            analysis.recovery_factor = total_profit / analysis.max_drawdown if analysis.max_drawdown > 0 else 0
        
        return analysis
    
    # Trade Statistics
    def calculate_trade_statistics(
        self,
        trades: List[Dict[str, Any]],
    ) -> TradeStatistics:
        """Calculate comprehensive trade statistics"""
        stats = TradeStatistics()
        
        if not trades:
            return stats
        
        winning_trades = [t for t in trades if t.get("pnl", 0) > 0]
        losing_trades = [t for t in trades if t.get("pnl", 0) < 0]
        
        stats.total_trades = len(trades)
        stats.winning_trades = len(winning_trades)
        stats.losing_trades = len(losing_trades)
        
        # P&L
        stats.gross_profit = sum(t.get("pnl", 0) for t in winning_trades)
        stats.gross_loss = abs(sum(t.get("pnl", 0) for t in losing_trades))
        stats.net_profit = stats.gross_profit - stats.gross_loss
        
        # Averages
        if winning_trades:
            stats.avg_win = stats.gross_profit / len(winning_trades)
        if losing_trades:
            stats.avg_loss = stats.gross_loss / len(losing_trades)
        if trades:
            stats.avg_trade = stats.net_profit / len(trades)
        
        # Ratios
        stats.win_rate = (stats.winning_trades / stats.total_trades * 100) if stats.total_trades > 0 else 0
        stats.loss_rate = (stats.losing_trades / stats.total_trades * 100) if stats.total_trades > 0 else 0
        stats.win_loss_ratio = stats.avg_win / stats.avg_loss if stats.avg_loss > 0 else 0
        stats.profit_factor = stats.gross_profit / stats.gross_loss if stats.gross_loss > 0 else 0
        stats.expectancy = stats.avg_trade
        
        # Duration
        durations = []
        for trade in trades:
            opened = self._parse_timestamp(trade.get("opened_at") or trade.get("timestamp"))
            closed = self._parse_timestamp(trade.get("closed_at") or trade.get("timestamp"))
            duration = (closed - opened).total_seconds()
            durations.append(duration)
        
        if durations:
            stats.avg_trade_duration = np.mean(durations)
            stats.min_trade_duration = np.min(durations)
            stats.max_trade_duration = np.max(durations)
        
        # Distribution
        pnls = [t.get("pnl", 0) for t in trades]
        if pnls:
            hist, bins = np.histogram(pnls, bins=10)
            stats.trade_pnl_distribution = {
                f"{bins[i]:.2f}-{bins[i+1]:.2f}": int(hist[i])
                for i in range(len(hist))
            }
        
        return stats
    
    # Confidence Calibration
    def analyze_confidence_calibration(
        self,
        trades: List[Dict[str, Any]],
        num_bins: int = 10,
    ) -> ConfidenceCalibration:
        """Analyze how well confidence levels predict outcomes"""
        calibration = ConfidenceCalibration()
        
        # Filter trades with confidence
        trades_with_confidence = [
            t for t in trades
            if t.get("confidence") is not None and t.get("pnl") is not None
        ]
        
        if len(trades_with_confidence) < num_bins:
            return calibration
        
        # Create bins
        bin_size = 100 / num_bins
        bins = [(i * bin_size, (i + 1) * bin_size) for i in range(num_bins)]
        
        for low, high in bins:
            # Get trades in this confidence bin
            bin_trades = [
                t for t in trades_with_confidence
                if low <= t.get("confidence", 0) < high
            ]
            
            if bin_trades:
                # Calculate actual win rate
                wins = sum(1 for t in bin_trades if t.get("pnl", 0) > 0)
                actual_win_rate = wins / len(bin_trades) * 100
                
                calibration.confidence_bins.append((low + high) / 2)
                calibration.actual_win_rates.append(actual_win_rate)
                calibration.predicted_confidences.append((low + high) / 2)
        
        # Calculate calibration error (ECE)
        if calibration.confidence_bins:
            ece = 0
            total = len(trades_with_confidence)
            
            for conf, actual in zip(calibration.confidence_bins, calibration.actual_win_rates):
                bin_trades = [
                    t for t in trades_with_confidence
                    if abs(t.get("confidence", 0) - conf) < bin_size / 2
                ]
                weight = len(bin_trades) / total if total > 0 else 0
                ece += weight * abs(actual - conf)
            
            calibration.calibration_error = ece
            
            # Brier score
            brier = 0
            for trade in trades_with_confidence:
                conf = trade.get("confidence", 50) / 100
                outcome = 1 if trade.get("pnl", 0) > 0 else 0
                brier += (conf - outcome) ** 2
            calibration.brier_score = brier / len(trades_with_confidence) if trades_with_confidence else 0
            
            # Reliability score (inverse of ECE)
            calibration.reliability_score = max(0, 100 - calibration.calibration_error * 10)
        
        return calibration
    
    # Decision Quality
    def analyze_decision_quality(
        self,
        trades: List[Dict[str, Any]],
    ) -> DecisionQualityMetrics:
        """Analyze decision quality metrics"""
        metrics = DecisionQualityMetrics()
        
        # Filter trades with direction predictions
        predicted_trades = [
            t for t in trades
            if t.get("predicted_direction") is not None and t.get("pnl") is not None
        ]
        
        if not predicted_trades:
            return metrics
        
        # Confusion matrix
        for trade in predicted_trades:
            predicted = trade.get("predicted_direction")
            actual = "long" if trade.get("pnl", 0) > 0 else "short"
            
            if predicted == "long" and actual == "long":
                metrics.true_positives += 1
            elif predicted == "short" and actual == "short":
                metrics.true_negatives += 1
            elif predicted == "long" and actual == "short":
                metrics.false_positives += 1
            else:
                metrics.false_negatives += 1
        
        # Calculate metrics
        total = metrics.true_positives + metrics.true_negatives + metrics.false_positives + metrics.false_negatives
        
        if total > 0:
            metrics.overall_accuracy = (metrics.true_positives + metrics.true_negatives) / total
            metrics.balanced_accuracy = (
                (metrics.true_positives / (metrics.true_positives + metrics.false_negatives) +
                 metrics.true_negatives / (metrics.true_negatives + metrics.false_positives)) / 2
            )
        
        # Precision and Recall
        tp_fp = metrics.true_positives + metrics.false_positives
        tp_fn = metrics.true_positives + metrics.false_negatives
        
        if tp_fp > 0:
            metrics.precision = metrics.true_positives / tp_fp
        if tp_fn > 0:
            metrics.recall = metrics.true_positives / tp_fn
        
        # F1 Score
        if metrics.precision + metrics.recall > 0:
            metrics.f1_score = 2 * (metrics.precision * metrics.recall) / (metrics.precision + metrics.recall)
        
        # Correlation with outcome
        confidences = [t.get("confidence", 50) for t in predicted_trades]
        outcomes = [1 if t.get("pnl", 0) > 0 else 0 for t in predicted_trades]
        
        if len(confidences) > 1:
            corr = np.corrcoef(confidences, outcomes)
            if len(corr) > 0 and corr[0, 1] == corr[0, 1]:  # Check for NaN
                metrics.correlation_with_outcome = corr[0, 1]
        
        return metrics
    
    # Comprehensive Report
    def generate_full_report(
        self,
        trades: List[Dict[str, Any]],
        strategy_id: str = "",
        starting_capital: float = 1000.0,
    ) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            "strategy_id": strategy_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "period": {},
            "equity_curve": {},
            "risk_metrics": {},
            "trade_statistics": {},
            "drawdown_analysis": {},
            "confidence_calibration": {},
            "decision_quality": {},
        }
        
        if not trades:
            return report
        
        # Period
        timestamps = [self._parse_timestamp(t.get("timestamp") or t.get("closed_at")) for t in trades]
        report["period"] = {
            "start": min(timestamps).isoformat() if timestamps else None,
            "end": max(timestamps).isoformat() if timestamps else None,
            "num_trades": len(trades),
        }
        
        # Equity curve
        equity_curve = self.generate_equity_curve(trades, starting_capital, strategy_id)
        report["equity_curve"] = {
            "starting_capital": equity_curve.starting_capital,
            "current_equity": equity_curve.current_equity,
            "total_return": equity_curve.total_return(),
            "annualized_return": equity_curve.annualized_return(),
        }
        
        # Risk metrics
        risk_metrics = self.calculate_risk_metrics(trades)
        report["risk_metrics"] = risk_metrics.to_dict()
        
        # Trade statistics
        trade_stats = self.calculate_trade_statistics(trades)
        report["trade_statistics"] = trade_stats.to_dict()
        
        # Drawdown analysis
        dd_analysis = self.analyze_drawdowns(trades)
        report["drawdown_analysis"] = dd_analysis.to_dict()
        
        # Confidence calibration
        confidence_cal = self.analyze_confidence_calibration(trades)
        report["confidence_calibration"] = confidence_cal.to_dict()
        
        # Decision quality
        decision_quality = self.analyze_decision_quality(trades)
        report["decision_quality"] = decision_quality.to_dict()
        
        return report
    
    # Rolling Returns
    def calculate_rolling_returns(
        self,
        trades: List[Dict[str, Any]],
        window_size: int = 20,
    ) -> List[Dict[str, Any]]:
        """Calculate rolling returns"""
        if not trades or len(trades) < window_size:
            return []
        
        results = []
        
        for i in range(window_size, len(trades) + 1):
            window_trades = trades[i - window_size:i]
            
            # Get timestamp
            timestamp = self._parse_timestamp(
                window_trades[-1].get("timestamp") or window_trades[-1].get("closed_at")
            )
            
            # Calculate return
            returns = sum(t.get("pnl", 0) for t in window_trades)
            
            results.append({
                "timestamp": timestamp.isoformat(),
                "return": returns,
                "num_trades": len(window_trades),
            })
        
        return results


import os
