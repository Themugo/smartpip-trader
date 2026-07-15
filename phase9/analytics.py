"""
Advanced Analytics - Comprehensive Trading Analytics

Advanced analytics for performance, risk, and market analysis.
"""

import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AnalyticsType(Enum):
    """Types of analytics"""
    PERFORMANCE = "performance"
    RISK = "risk"
    MARKET = "market"
    CORRELATION = "correlation"
    REGRESSION = "regression"
    TIME_SERIES = "time_series"


@dataclass
class AnalyticsResult:
    """Result of an analytics calculation"""
    id: str
    analytics_type: AnalyticsType
    name: str
    
    # Data
    data: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    
    # Visualization data
    chart_data: Dict[str, Any] = field(default_factory=dict)
    
    # Summary
    summary: str = ""
    
    # Timestamps
    calculated_at: datetime = field(default_factory=datetime.utcnow)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "analytics_type": self.analytics_type.value,
            "name": self.name,
            "metrics": self.metrics,
            "summary": self.summary,
            "calculated_at": self.calculated_at.isoformat(),
        }


@dataclass
class CorrelationResult:
    """Correlation analysis result"""
    asset_pairs: List[Dict[str, Any]] = field(default_factory=list)
    matrix: List[List[float]] = field(default_factory=list)
    significant_correlations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class TimeSeriesAnalysis:
    """Time series analysis result"""
    trend: str = "unknown"  # "up", "down", "stable"
    trend_strength: float = 0
    seasonality_detected: bool = False
    seasonality_period: int = 0
    anomalies: List[Dict[str, Any]] = field(default_factory=list)
    forecast: List[float] = field(default_factory=list)


class AnalyticsDashboard:
    """Dashboard data container"""
    
    def __init__(self):
        self._widgets: Dict[str, Dict[str, Any]] = {}
        self._refresh_interval: int = 60  # seconds
    
    def add_widget(
        self,
        widget_id: str,
        widget_type: str,
        title: str,
        data: Dict[str, Any],
    ) -> None:
        """Add a widget to the dashboard"""
        self._widgets[widget_id] = {
            "type": widget_type,
            "title": title,
            "data": data,
            "updated_at": datetime.utcnow(),
        }
    
    def get_dashboard(self) -> Dict[str, Any]:
        """Get full dashboard data"""
        return {
            "widgets": self._widgets,
            "refresh_interval": self._refresh_interval,
            "generated_at": datetime.utcnow().isoformat(),
        }


class AdvancedAnalytics:
    """
    Advanced Analytics for comprehensive trading analysis.
    
    Features:
    - Performance analytics
    - Risk analytics
    - Market analytics
    - Correlation analysis
    - Time series analysis
    - Regression analysis
    - Statistical tests
    - Dashboard generation
    """
    
    def __init__(self):
        self._results: Dict[str, AnalyticsResult] = {}
        self._dashboard = AnalyticsDashboard()
    
    # =========================================================================
    # Performance Analytics
    # =========================================================================
    
    def analyze_performance(
        self,
        trades: List[Dict[str, Any]],
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> AnalyticsResult:
        """Analyze trading performance"""
        result = AnalyticsResult(
            id=str(uuid.uuid4()),
            analytics_type=AnalyticsType.PERFORMANCE,
            name="Performance Analysis",
            period_start=period_start,
            period_end=period_end,
        )
        
        # Filter trades by period
        if period_start:
            trades = [t for t in trades if t.get("timestamp", datetime.min) >= period_start]
        if period_end:
            trades = [t for t in trades if t.get("timestamp", datetime.max) <= period_end]
        
        if not trades:
            result.summary = "No trades found in the specified period"
            return result
        
        # Calculate metrics
        winning_trades = [t for t in trades if t.get("pnl", 0) > 0]
        losing_trades = [t for t in trades if t.get("pnl", 0) < 0]
        
        total_pnl = sum(t.get("pnl", 0) for t in trades)
        win_rate = len(winning_trades) / len(trades) if trades else 0
        
        avg_win = sum(t.get("pnl", 0) for t in winning_trades) / max(len(winning_trades), 1)
        avg_loss = abs(sum(t.get("pnl", 0) for t in losing_trades) / max(len(losing_trades), 1))
        
        expectancy = (win_rate * avg_win - (1 - win_rate) * avg_loss) if avg_loss > 0 else 0
        
        profit_factor = (
            sum(t.get("pnl", 0) for t in winning_trades) / max(avg_loss * len(losing_trades), 1)
        )
        
        # Calculate drawdown
        equity = 10000  # Starting equity
        peak = equity
        max_drawdown = 0
        
        running_equity = equity
        equity_curve = []
        
        for trade in trades:
            running_equity += trade.get("pnl", 0)
            equity_curve.append(running_equity)
            
            if running_equity > peak:
                peak = running_equity
            
            drawdown = (peak - running_equity) / peak if peak > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)
        
        # Calculate Sharpe ratio (simplified)
        returns = [t.get("pnl", 0) / equity for t in trades]
        avg_return = sum(returns) / len(returns) if returns else 0
        std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5 if returns else 0
        sharpe_ratio = (avg_return / std_return * (252 ** 0.5)) if std_return > 0 else 0
        
        result.metrics = {
            "total_trades": len(trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "expectancy": expectancy,
            "profit_factor": profit_factor,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "avg_trade": total_pnl / len(trades) if trades else 0,
        }
        
        result.data = {
            "trades": trades,
            "equity_curve": equity_curve,
            "period_days": (period_end - period_start).days if period_start and period_end else 0,
        }
        
        result.chart_data = {
            "equity_curve": equity_curve,
            "drawdown_curve": self._calculate_drawdown_curve(equity_curve),
            "trade_distribution": {
                "wins": len(winning_trades),
                "losses": len(losing_trades),
            },
        }
        
        result.summary = (
            f"Analyzed {len(trades)} trades with {len(winning_trades)} winners "
            f"({win_rate:.1%} win rate). Total P&L: ${total_pnl:.2f}, "
            f"Sharpe: {sharpe_ratio:.2f}, Max Drawdown: {max_drawdown:.1%}"
        )
        
        self._results[result.id] = result
        return result
    
    def _calculate_drawdown_curve(self, equity_curve: List[float]) -> List[float]:
        """Calculate drawdown curve from equity curve"""
        if not equity_curve:
            return []
        
        peak = equity_curve[0]
        drawdowns = []
        
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak if peak > 0 else 0
            drawdowns.append(drawdown)
        
        return drawdowns
    
    # =========================================================================
    # Risk Analytics
    # =========================================================================
    
    def analyze_risk(
        self,
        positions: List[Dict[str, Any]],
        portfolio_value: float,
    ) -> AnalyticsResult:
        """Analyze portfolio risk"""
        result = AnalyticsResult(
            id=str(uuid.uuid4()),
            analytics_type=AnalyticsType.RISK,
            name="Risk Analysis",
        )
        
        if not positions:
            result.summary = "No positions to analyze"
            return result
        
        # Calculate exposure
        total_exposure = sum(
            abs(p.get("size", 0) * p.get("price", 0))
            for p in positions
        )
        exposure_ratio = total_exposure / portfolio_value if portfolio_value > 0 else 0
        
        # Calculate concentration
        exposures = [
            abs(p.get("size", 0) * p.get("price", 0)) / total_exposure
            for p in positions
            if total_exposure > 0
        ]
        max_concentration = max(exposures) if exposures else 0
        
        # Calculate VaR (simplified)
        returns = [p.get("return", 0) for p in positions]
        
        if returns:
            sorted_returns = sorted(returns)
            var_95_index = int(len(sorted_returns) * 0.05)
            var_95 = abs(sorted_returns[var_95_index]) if var_95_index < len(sorted_returns) else 0
        else:
            var_95 = 0
        
        # Risk metrics
        result.metrics = {
            "total_exposure": total_exposure,
            "exposure_ratio": exposure_ratio,
            "max_concentration": max_concentration,
            "var_95": var_95,
            "num_positions": len(positions),
            "diversification_score": 1 - max_concentration,
        }
        
        result.data = {
            "positions": positions,
            "exposures": exposures,
        }
        
        result.summary = (
            f"Portfolio exposure: ${total_exposure:.2f} ({exposure_ratio:.1%} of portfolio). "
            f"Max concentration: {max_concentration:.1%}. VaR (95%): {var_95:.2%}"
        )
        
        self._results[result.id] = result
        return result
    
    # =========================================================================
    # Correlation Analysis
    # =========================================================================
    
    def analyze_correlation(
        self,
        symbols: List[str],
        price_data: Dict[str, List[float]],
    ) -> CorrelationResult:
        """Analyze correlations between symbols"""
        result = CorrelationResult()
        
        n = len(symbols)
        
        # Calculate correlation matrix
        result.matrix = [[0.0] * n for _ in range(n)]
        
        for i, sym1 in enumerate(symbols):
            for j, sym2 in enumerate(symbols):
                if i == j:
                    result.matrix[i][j] = 1.0
                else:
                    corr = self._calculate_correlation(
                        price_data.get(sym1, []),
                        price_data.get(sym2, []),
                    )
                    result.matrix[i][j] = corr
                    
                    # Track significant correlations
                    if abs(corr) > 0.7:
                        result.significant_correlations.append({
                            "symbol1": sym1,
                            "symbol2": sym2,
                            "correlation": corr,
                            "type": "positive" if corr > 0 else "negative",
                        })
        
        # Build asset pairs
        for i, sym1 in enumerate(symbols):
            for j, sym2 in enumerate(symbols):
                if i < j:
                    result.asset_pairs.append({
                        "symbol1": sym1,
                        "symbol2": sym2,
                        "correlation": result.matrix[i][j],
                    })
        
        return result
    
    def _calculate_correlation(
        self,
        series1: List[float],
        series2: List[float],
    ) -> float:
        """Calculate Pearson correlation between two series"""
        if len(series1) != len(series2) or len(series1) < 2:
            return 0
        
        n = len(series1)
        mean1 = sum(series1) / n
        mean2 = sum(series2) / n
        
        numerator = sum((s1 - mean1) * (s2 - mean2) for s1, s2 in zip(series1, series2))
        denom1 = sum((s1 - mean1) ** 2 for s1 in series1) ** 0.5
        denom2 = sum((s2 - mean2) ** 2 for s2 in series2) ** 0.5
        
        if denom1 == 0 or denom2 == 0:
            return 0
        
        return numerator / (denom1 * denom2)
    
    # =========================================================================
    # Time Series Analysis
    # =========================================================================
    
    def analyze_time_series(
        self,
        data: List[float],
        timestamps: List[datetime],
    ) -> TimeSeriesAnalysis:
        """Analyze time series data"""
        result = TimeSeriesAnalysis()
        
        if len(data) < 2:
            return result
        
        # Calculate trend
        n = len(data)
        x_mean = (n - 1) / 2
        y_mean = sum(data) / n
        
        numerator = sum((i - x_mean) * (data[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator != 0 else 0
        
        if abs(slope) < 0.001:
            result.trend = "stable"
            result.trend_strength = 0
        elif slope > 0:
            result.trend = "up"
            result.trend_strength = min(1, abs(slope) / (max(data) - min(data) + 1))
        else:
            result.trend = "down"
            result.trend_strength = min(1, abs(slope) / (max(data) - min(data) + 1))
        
        # Simple anomaly detection (using standard deviation)
        mean = sum(data) / len(data)
        std = (sum((x - mean) ** 2 for x in data) / len(data)) ** 0.5
        
        for i, (value, ts) in enumerate(zip(data, timestamps)):
            if abs(value - mean) > 3 * std:
                result.anomalies.append({
                    "index": i,
                    "timestamp": ts.isoformat(),
                    "value": value,
                    "deviation": (value - mean) / std if std > 0 else 0,
                })
        
        return result
    
    # =========================================================================
    # Statistical Tests
    # =========================================================================
    
    def normality_test(self, data: List[float]) -> Dict[str, Any]:
        """Test if data follows normal distribution (simplified)"""
        n = len(data)
        mean = sum(data) / n
        
        # Calculate skewness and kurtosis
        std = (sum((x - mean) ** 2 for x in data) / n) ** 0.5
        
        if std == 0:
            return {"is_normal": False, "reason": "No variance"}
        
        skewness = sum((x - mean) ** 3 for x in data) / (n * std ** 3)
        kurtosis = sum((x - mean) ** 4 for x in data) / (n * std ** 4) - 3
        
        # Simple heuristic
        is_normal = abs(skewness) < 1 and abs(kurtosis) < 3
        
        return {
            "is_normal": is_normal,
            "skewness": skewness,
            "kurtosis": kurtosis,
            "mean": mean,
            "std": std,
        }
    
    def stationarity_test(self, data: List[float]) -> Dict[str, Any]:
        """Simple stationarity test (simplified ADF equivalent)"""
        if len(data) < 10:
            return {"is_stationary": False, "reason": "Insufficient data"}
        
        # Calculate differences
        differences = [data[i] - data[i - 1] for i in range(1, len(data))]
        
        # Compare variance
        var_original = sum((x - sum(data) / len(data)) ** 2 for x in data) / len(data)
        var_diff = sum((x - sum(differences) / len(differences)) ** 2 for x in differences) / max(len(differences), 1)
        
        # If differencing reduces variance significantly, might be non-stationary
        is_stationary = var_diff < var_original
        
        return {
            "is_stationary": is_stationary,
            "variance_original": var_original,
            "variance_differenced": var_diff,
            "variance_ratio": var_diff / var_original if var_original > 0 else 0,
        }
    
    # =========================================================================
    # Dashboard
    # =========================================================================
    
    def generate_dashboard(
        self,
        performance_result: AnalyticsResult,
        risk_result: AnalyticsResult,
    ) -> Dict[str, Any]:
        """Generate analytics dashboard"""
        dashboard = {
            "generated_at": datetime.utcnow().isoformat(),
            "widgets": {},
        }
        
        # Performance widget
        dashboard["widgets"]["performance"] = {
            "type": "performance",
            "title": "Performance Overview",
            "metrics": performance_result.metrics,
            "chart": performance_result.chart_data,
        }
        
        # Risk widget
        dashboard["widgets"]["risk"] = {
            "type": "risk",
            "title": "Risk Metrics",
            "metrics": risk_result.metrics,
        }
        
        # Summary widget
        dashboard["widgets"]["summary"] = {
            "type": "summary",
            "title": "Executive Summary",
            "content": f"{performance_result.summary} {risk_result.summary}",
        }
        
        return dashboard
    
    def get_result(self, result_id: str) -> Optional[AnalyticsResult]:
        """Get an analytics result by ID"""
        return self._results.get(result_id)
    
    def get_all_results(self) -> List[AnalyticsResult]:
        """Get all analytics results"""
        return list(self._results.values())
