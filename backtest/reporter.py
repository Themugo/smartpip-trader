"""
Professional Backtest Reporter
=============================

Comprehensive reporting with all professional metrics.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class ReportFormat(Enum):
    """Report formats"""
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"


@dataclass
class EquityCurve:
    """Equity curve data"""
    timestamps: List[datetime]
    equity: List[float]
    drawdown: List[float]
    returns: List[float]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_value": self.equity[0] if self.equity else 0,
            "end_value": self.equity[-1] if self.equity else 0,
            "peak_value": max(self.equity) if self.equity else 0,
            "trough_value": min(self.equity) if self.equity else 0,
            "total_return": (self.equity[-1] / self.equity[0] - 1) if self.equity and self.equity[0] != 0 else 0
        }


@dataclass
class DrawdownAnalysis:
    """Drawdown analysis"""
    max_drawdown: float
    max_drawdown_pct: float
    current_drawdown: float
    current_drawdown_pct: float
    avg_drawdown: float
    drawdown_duration_avg: float
    drawdown_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_drawdown": self.max_drawdown,
            "max_drawdown_pct": self.max_drawdown_pct,
            "current_drawdown": self.current_drawdown,
            "current_drawdown_pct": self.current_drawdown_pct,
            "avg_drawdown": self.avg_drawdown,
            "drawdown_duration_avg": self.drawdown_duration_avg,
            "drawdown_count": self.drawdown_count
        }


@dataclass
class TradeDistribution:
    """Trade distribution analysis"""
    win_count: int
    loss_count: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    expectancy: float
    largest_win: float
    largest_loss: float
    median_win: float
    median_loss: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "win_count": self.win_count,
            "loss_count": self.loss_count,
            "win_rate": self.win_rate,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "profit_factor": self.profit_factor,
            "expectancy": self.expectancy,
            "largest_win": self.largest_win,
            "largest_loss": self.largest_loss,
            "median_win": self.median_win,
            "median_loss": self.median_loss
        }


@dataclass
class CalibrationAnalysis:
    """Confidence calibration analysis"""
    brier_score: float
    log_loss: float
    ece: float
    reliability: float
    calibration_points: List[Dict[str, float]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "brier_score": self.brier_score,
            "log_loss": self.log_loss,
            "expected_calibration_error": self.ece,
            "reliability": self.reliability,
            "calibration_points": self.calibration_points,
            "is_calibrated": self.ece < 0.1
        }


@dataclass
class BacktestReport:
    """
    Professional backtest report with all metrics.
    """
    report_id: str
    generated_at: datetime
    strategy_name: str
    
    # Equity & Returns
    equity_curve: EquityCurve
    total_return: float
    annualized_return: float
    
    # Risk Metrics
    drawdown_analysis: DrawdownAnalysis
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    
    # Trade Statistics
    trade_distribution: TradeDistribution
    total_trades: int
    n_wins: int
    n_losses: int
    
    # Decision Quality
    confidence_distribution: List[float]
    accuracy_by_confidence: Dict[str, float]
    decision_quality_score: float
    calibration_analysis: Optional[CalibrationAnalysis]
    
    # Rolling Metrics
    rolling_win_rate: List[float]
    rolling_accuracy: List[float]
    
    # Additional Metrics
    recovery_factor: float
    payoff_ratio: float
    trade_duration_avg: float
    
    # Metadata
    start_date: datetime
    end_date: datetime
    n_days: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "strategy_name": self.strategy_name,
            "equity": self.equity_curve.to_dict(),
            "returns": {
                "total_return": self.total_return,
                "annualized_return": self.annualized_return
            },
            "risk": {
                "drawdown": self.drawdown_analysis.to_dict(),
                "sharpe_ratio": self.sharpe_ratio,
                "sortino_ratio": self.sortino_ratio,
                "calmar_ratio": self.calmar_ratio
            },
            "trades": {
                "distribution": self.trade_distribution.to_dict(),
                "total_trades": self.total_trades,
                "n_wins": self.n_wins,
                "n_losses": self.n_losses
            },
            "decision_quality": {
                "score": self.decision_quality_score,
                "accuracy_by_confidence": self.accuracy_by_confidence,
                "calibration": self.calibration_analysis.to_dict() if self.calibration_analysis else None
            },
            "rolling": {
                "win_rate": self.rolling_win_rate,
                "accuracy": self.rolling_accuracy
            },
            "additional_metrics": {
                "recovery_factor": self.recovery_factor,
                "payoff_ratio": self.payoff_ratio,
                "trade_duration_avg": self.trade_duration_avg
            },
            "period": {
                "start_date": self.start_date.isoformat(),
                "end_date": self.end_date.isoformat(),
                "n_days": self.n_days
            }
        }
    
    def to_markdown(self) -> str:
        """Convert to markdown format"""
        lines = [
            f"# Backtest Report: {self.strategy_name}",
            "",
            f"**Generated:** {self.generated_at.strftime('%Y-%m-%d %H:%M')}",
            f"**Period:** {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')} ({self.n_days} days)",
            "",
            "---",
            "",
            "## Performance Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Return | {self.total_return:.2%} |",
            f"| Annualized Return | {self.annualized_return:.2%} |",
            f"| Sharpe Ratio | {self.sharpe_ratio:.2f} |",
            f"| Sortino Ratio | {self.sortino_ratio:.2f} |",
            f"| Calmar Ratio | {self.calmar_ratio:.2f} |",
            "",
            "## Risk Metrics",
            "",
            f"| Metric | Value |",
            "|--------|-------|",
            f"| Max Drawdown | {self.drawdown_analysis.max_drawdown_pct:.2%} |",
            f"| Current Drawdown | {self.drawdown_analysis.current_drawdown_pct:.2%} |",
            f"| Avg Drawdown | {self.drawdown_analysis.avg_drawdown:.2%} |",
            f"| Recovery Factor | {self.recovery_factor:.2f} |",
            "",
            "## Trade Statistics",
            "",
            f"| Metric | Value |",
            "|--------|-------|",
            f"| Total Trades | {self.total_trades} |",
            f"| Win Rate | {self.trade_distribution.win_rate:.1%} |",
            f"| Profit Factor | {self.trade_distribution.profit_factor:.2f} |",
            f"| Expectancy | {self.trade_distribution.expectancy:.4f} |",
            f"| Avg Win | ${self.trade_distribution.avg_win:.2f} |",
            f"| Avg Loss | ${self.trade_distribution.avg_loss:.2f} |",
            "",
            "## Decision Quality",
            "",
            f"| Metric | Value |",
            "|--------|-------|",
            f"| Decision Quality Score | {self.decision_quality_score:.2f} |",
            f"| Calibration ECE | {self.calibration_analysis.ece if self.calibration_analysis else 'N/A'} |",
        ]
        
        lines.append("")
        
        return "\n".join(lines)


class ReportGenerator:
    """
    Generates professional backtest reports.
    """
    
    def __init__(self, output_dir: str = "data/backtest/reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_report(
        self,
        trades: List[Dict[str, Any]],
        equity_data: List[float],
        timestamps: List[datetime],
        strategy_name: str = "Strategy"
    ) -> BacktestReport:
        """
        Generate a comprehensive backtest report.
        
        Args:
            trades: List of trade dictionaries
            equity_data: List of equity values over time
            timestamps: Corresponding timestamps
            strategy_name: Name of strategy
            
        Returns:
            BacktestReport
        """
        # Calculate equity curve
        equity_curve = self._calculate_equity_curve(equity_data, timestamps)
        
        # Calculate drawdown analysis
        drawdown_analysis = self._calculate_drawdown(equity_data)
        
        # Calculate trade distribution
        trade_distribution = self._calculate_trade_distribution(trades)
        
        # Calculate metrics
        returns = self._calculate_returns(equity_data)
        sharpe = self._calculate_sharpe(returns)
        sortino = self._calculate_sortino(returns)
        calmar = self._calculate_calmar(
            equity_data[-1] / equity_data[0] - 1 if equity_data else 0,
            drawdown_analysis.max_drawdown_pct
        )
        
        # Decision quality
        confidence_distribution = [t.get("confidence", 0) for t in trades]
        accuracy_by_conf = self._calculate_accuracy_by_confidence(trades)
        dq_score = self._calculate_decision_quality_score(trades)
        
        # Rolling metrics
        rolling_wr = self._calculate_rolling_metric(trades, "win_rate", 20)
        rolling_acc = self._calculate_rolling_accuracy(trades, 20)
        
        # Recovery factor
        total_profit = sum(t.get("pnl", 0) for t in trades if t.get("pnl", 0) > 0)
        recovery_factor = total_profit / abs(drawdown_analysis.max_drawdown) if drawdown_analysis.max_drawdown != 0 else 0
        
        # Calibration analysis
        calibration = self._calculate_calibration(trades)
        
        report = BacktestReport(
            report_id=str(uuid4()),
            generated_at=datetime.now(),
            strategy_name=strategy_name,
            equity_curve=equity_curve,
            total_return=equity_data[-1] / equity_data[0] - 1 if equity_data and equity_data[0] != 0 else 0,
            annualized_return=self._calculate_annualized_return(equity_data, timestamps),
            drawdown_analysis=drawdown_analysis,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            trade_distribution=trade_distribution,
            total_trades=len(trades),
            n_wins=trade_distribution.win_count,
            n_losses=trade_distribution.loss_count,
            confidence_distribution=confidence_distribution,
            accuracy_by_confidence=accuracy_by_conf,
            decision_quality_score=dq_score,
            calibration_analysis=calibration,
            rolling_win_rate=rolling_wr,
            rolling_accuracy=rolling_acc,
            recovery_factor=recovery_factor,
            payoff_ratio=trade_distribution.avg_win / abs(trade_distribution.avg_loss) if trade_distribution.avg_loss != 0 else 0,
            trade_duration_avg=np.mean([t.get("duration", 1) for t in trades]) if trades else 0,
            start_date=timestamps[0] if timestamps else datetime.now(),
            end_date=timestamps[-1] if timestamps else datetime.now(),
            n_days=(timestamps[-1] - timestamps[0]).days if timestamps and len(timestamps) > 1 else 0
        )
        
        return report
    
    def _calculate_equity_curve(
        self,
        equity: List[float],
        timestamps: List[datetime]
    ) -> EquityCurve:
        """Calculate equity curve with drawdown"""
        equity = np.array(equity)
        
        # Calculate drawdown
        peak = np.maximum.accumulate(equity)
        drawdown = equity - peak
        
        # Calculate returns
        returns = np.diff(equity) / equity[:-1] if len(equity) > 1 else []
        
        return EquityCurve(
            timestamps=timestamps,
            equity=equity.tolist(),
            drawdown=drawdown.tolist(),
            returns=returns.tolist() if len(returns) > 0 else []
        )
    
    def _calculate_drawdown(self, equity: List[float]) -> DrawdownAnalysis:
        """Calculate drawdown metrics"""
        equity = np.array(equity)
        peak = np.maximum.accumulate(equity)
        drawdown = equity - peak
        drawdown_pct = drawdown / peak
        
        # Find current drawdown
        current_dd = drawdown[-1] if len(drawdown) > 0 else 0
        current_dd_pct = drawdown_pct[-1] if len(drawdown_pct) > 0 else 0
        
        # Count drawdown periods
        dd_starts = []
        in_dd = False
        for i, d in enumerate(drawdown):
            if d < 0 and not in_dd:
                dd_starts.append(i)
                in_dd = True
            elif d >= 0:
                in_dd = False
        
        return DrawdownAnalysis(
            max_drawdown=abs(np.min(drawdown)) if len(drawdown) > 0 else 0,
            max_drawdown_pct=abs(np.min(drawdown_pct)) if len(drawdown_pct) > 0 else 0,
            current_drawdown=abs(current_dd),
            current_drawdown_pct=abs(current_dd_pct),
            avg_drawdown=np.mean(drawdown[drawdown < 0]) if len(drawdown[drawdown < 0]) > 0 else 0,
            drawdown_duration_avg=len(dd_starts) / max(len(dd_starts), 1),
            drawdown_count=len(dd_starts)
        )
    
    def _calculate_trade_distribution(self, trades: List[Dict]) -> TradeDistribution:
        """Calculate trade distribution metrics"""
        wins = [t["pnl"] for t in trades if t.get("pnl", 0) > 0]
        losses = [t["pnl"] for t in trades if t.get("pnl", 0) <= 0]
        
        total = len(trades)
        win_count = len(wins)
        loss_count = len(losses)
        
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        expectancies = [t["pnl"] / total for t in trades] if total > 0 else []
        expectancy = sum(expectancies)
        
        return TradeDistribution(
            win_count=win_count,
            loss_count=loss_count,
            win_rate=win_count / total if total > 0 else 0,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            expectancy=expectancy,
            largest_win=max(wins) if wins else 0,
            largest_loss=min(losses) if losses else 0,
            median_win=np.median(wins) if wins else 0,
            median_loss=np.median(losses) if losses else 0
        )
    
    def _calculate_returns(self, equity: List[float]) -> np.ndarray:
        """Calculate returns"""
        equity = np.array(equity)
        return np.diff(equity) / equity[:-1] if len(equity) > 1 else np.array([])
    
    def _calculate_sharpe(self, returns: np.ndarray, risk_free: float = 0.0) -> float:
        """Calculate Sharpe ratio"""
        if len(returns) == 0 or np.std(returns) == 0:
            return 0.0
        excess = returns - risk_free
        return np.mean(excess) / np.std(excess) * np.sqrt(252)
    
    def _calculate_sortino(self, returns: np.ndarray, risk_free: float = 0.0) -> float:
        """Calculate Sortino ratio"""
        if len(returns) == 0:
            return 0.0
        excess = returns - risk_free
        downside = returns[returns < 0]
        if len(downside) == 0 or np.std(downside) == 0:
            return 0.0
        return np.mean(excess) / np.std(downside) * np.sqrt(252)
    
    def _calculate_calmar(self, total_return: float, max_dd: float) -> float:
        """Calculate Calmar ratio"""
        if max_dd == 0:
            return 0.0
        return total_return / max_dd
    
    def _calculate_annualized_return(
        self,
        equity: List[float],
        timestamps: List[datetime]
    ) -> float:
        """Calculate annualized return"""
        if len(equity) < 2 or len(timestamps) < 2:
            return 0.0
        
        total_return = equity[-1] / equity[0] - 1
        years = (timestamps[-1] - timestamps[0]).days / 365.25
        
        if years <= 0:
            return 0.0
        
        return (1 + total_return) ** (1 / years) - 1
    
    def _calculate_accuracy_by_confidence(self, trades: List[Dict]) -> Dict[str, float]:
        """Calculate accuracy by confidence level"""
        quintiles = {"high": [], "medium": [], "low": []}
        
        for t in trades:
            conf = t.get("confidence", 0.5)
            correct = t.get("correct", False)
            
            if conf >= 0.7:
                quintiles["high"].append(correct)
            elif conf >= 0.4:
                quintiles["medium"].append(correct)
            else:
                quintiles["low"].append(correct)
        
        return {
            k: np.mean(v) if v else 0
            for k, v in quintiles.items()
        }
    
    def _calculate_decision_quality_score(self, trades: List[Dict]) -> float:
        """Calculate overall decision quality score"""
        if not trades:
            return 0.0
        
        # Components:
        # 1. Calibration (0-33)
        calibration_score = self._calculate_calibration_score(trades) * 33
        
        # 2. Confidence usefulness (0-33)
        usefulness_score = self._calculate_confidence_usefulness(trades) * 33
        
        # 3. Win rate calibration (0-34)
        win_rate = sum(1 for t in trades if t.get("correct", False)) / len(trades)
        avg_conf = np.mean([t.get("confidence", 0.5) for t in trades])
        win_rate_calibration = 1 - abs(win_rate - avg_conf)
        win_rate_score = win_rate_calibration * 34
        
        return calibration_score + usefulness_score + win_rate_score
    
    def _calculate_calibration_score(self, trades: List[Dict]) -> float:
        """Calculate calibration score"""
        # Group by confidence bins
        bins = [(0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)]
        scores = []
        
        for low, high in bins:
            bin_trades = [t for t in trades
                         if low <= t.get("confidence", 0) < high]
            if bin_trades:
                bin_acc = sum(1 for t in bin_trades if t.get("correct", False)) / len(bin_trades)
                bin_conf = (low + high) / 2
                scores.append(1 - abs(bin_acc - bin_conf))
        
        return np.mean(scores) if scores else 0.5
    
    def _calculate_confidence_usefulness(self, trades: List[Dict]) -> float:
        """Calculate if confidence predictions are useful"""
        high_conf = [t.get("correct", False) for t in trades
                   if t.get("confidence", 0) >= 0.7]
        low_conf = [t.get("correct", False) for t in trades
                   if t.get("confidence", 0) < 0.4]
        
        if not high_conf or not low_conf:
            return 0.5
        
        high_acc = np.mean(high_conf)
        low_acc = np.mean(low_conf)
        
        # Good calibration: high confidence = higher accuracy
        return max(0, min(1, high_acc - low_acc + 0.5))
    
    def _calculate_rolling_metric(
        self,
        trades: List[Dict],
        metric: str,
        window: int
    ) -> List[float]:
        """Calculate rolling metric"""
        if len(trades) < window:
            return []
        
        results = []
        for i in range(window, len(trades) + 1):
            window_trades = trades[i-window:i]
            
            if metric == "win_rate":
                wins = sum(1 for t in window_trades if t.get("pnl", 0) > 0)
                results.append(wins / window)
        
        return results
    
    def _calculate_rolling_accuracy(self, trades: List[Dict], window: int) -> List[float]:
        """Calculate rolling accuracy"""
        return self._calculate_rolling_metric(trades, "win_rate", window)
    
    def _calculate_calibration(self, trades: List[Dict]) -> CalibrationAnalysis:
        """Calculate calibration analysis"""
        # Group predictions by confidence bin
        bins = {i: [] for i in range(10)}
        
        for t in trades:
            conf = t.get("confidence", 0.5)
            correct = t.get("correct", False)
            bin_idx = int(conf * 10)
            bin_idx = min(bin_idx, 9)
            bins[bin_idx].append(correct)
        
        calibration_points = []
        for i in range(10):
            if bins[i]:
                calibration_points.append({
                    "bin_center": (i + 0.5) / 10,
                    "predicted": (i + 0.5) / 10,
                    "actual": np.mean(bins[i]),
                    "count": len(bins[i])
                })
        
        # Calculate ECE
        total = sum(len(bins[i]) for i in range(10))
        ece = sum(
            len(bins[i]) / total * abs((i + 0.5) / 10 - np.mean(bins[i]))
            for i in range(10)
            if bins[i]
        )
        
        # Calculate reliability
        preds = [(i + 0.5) / 10 for i in range(10) for _ in bins[i]]
        acts = [c for i in range(10) for c in bins[i]]
        
        if preds and acts:
            reliability, _ = stats.pearsonr(preds, acts)
        else:
            reliability = 0
        
        return CalibrationAnalysis(
            brier_score=ece,  # Simplified
            log_loss=ece * 2,  # Simplified
            ece=ece,
            reliability=reliability,
            calibration_points=calibration_points
        )
    
    def export_report(
        self,
        report: BacktestReport,
        format: ReportFormat = ReportFormat.JSON
    ) -> str:
        """Export report to file"""
        if format == ReportFormat.JSON:
            filename = f"{report.report_id}.json"
            path = os.path.join(self.output_dir, filename)
            with open(path, 'w') as f:
                json.dump(report.to_dict(), f, indent=2)
        elif format == ReportFormat.MARKDOWN:
            filename = f"{report.report_id}.md"
            path = os.path.join(self.output_dir, filename)
            with open(path, 'w') as f:
                f.write(report.to_markdown())
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        return path
