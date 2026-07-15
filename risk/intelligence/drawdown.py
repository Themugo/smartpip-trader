"""
Rolling Drawdown Analysis
=========================

Tracks and analyzes drawdowns over time.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DrawdownPeriod:
    """A drawdown period"""
    start_date: datetime
    peak_value: float
    trough_date: Optional[datetime]
    trough_value: float
    end_date: Optional[datetime]
    current_value: float
    max_drawdown: float
    duration_days: int
    recovery_days: Optional[int]
    is_recovered: bool
    
    @property
    def drawdown_pct(self) -> float:
        return self.max_drawdown / self.peak_value if self.peak_value > 0 else 0


class DrawdownAnalyzer:
    """
    Analyzes portfolio drawdowns.
    """
    
    def __init__(
        self,
        window_size: int = 252,  # 1 year
        rolling_window: int = 30  # 30-day rolling
    ):
        self.window_size = window_size
        self.rolling_window = rolling_window
        
        # State
        self.current_drawdown = 0.0
        self.max_drawdown = 0.0
        self.max_drawdown_duration = 0  # Days
        self.current_drawdown_duration = 0  # Days
        
        # History
        self.peak = 0.0
        self.equity_curve: List[float] = []
        self.drawdown_curve: List[float] = []
        self.drawdown_periods: List[DrawdownPeriod] = []
        self.in_drawdown = False
        self.drawdown_start: Optional[datetime] = None
        
        # Rolling metrics
        self.rolling_max: List[float] = []
        self.rolling_drawdown: List[float] = []
    
    def update(self, current_value: float, peak_value: float) -> None:
        """Update drawdown metrics with new value"""
        self.peak = peak_value
        self.equity_curve.append(current_value)
        
        # Calculate current drawdown
        if self.peak > 0:
            self.current_drawdown = (self.peak - current_value) / self.peak
        else:
            self.current_drawdown = 0.0
        
        self.drawdown_curve.append(self.current_drawdown)
        
        # Update max drawdown
        if self.current_drawdown > self.max_drawdown:
            self.max_drawdown = self.current_drawdown
        
        # Track drawdown period
        if self.current_drawdown > 0.01:  # 1% threshold
            if not self.in_drawdown:
                self.in_drawdown = True
                self.drawdown_start = datetime.now()
            
            self.current_drawdown_duration += 1
            
            if self.current_drawdown_duration > self.max_drawdown_duration:
                self.max_drawdown_duration = self.current_drawdown_duration
        else:
            if self.in_drawdown:
                self._end_drawdown_period(current_value)
            self.in_drawdown = False
            self.current_drawdown_duration = 0
        
        # Update rolling metrics
        self._update_rolling_metrics()
    
    def _end_drawdown_period(self, current_value: float) -> None:
        """End current drawdown period"""
        if self.drawdown_start:
            period = DrawdownPeriod(
                start_date=self.drawdown_start,
                peak_value=self.peak,
                trough_date=None,
                trough_value=current_value,
                end_date=datetime.now(),
                current_value=current_value,
                max_drawdown=self.max_drawdown,
                duration_days=self.current_drawdown_duration,
                recovery_days=0,
                is_recovered=True
            )
            self.drawdown_periods.append(period)
    
    def _update_rolling_metrics(self) -> None:
        """Update rolling drawdown metrics"""
        if len(self.equity_curve) >= self.rolling_window:
            window = self.equity_curve[-self.rolling_window:]
            rolling_max = max(window)
            rolling_dd = (rolling_max - window[-1]) / rolling_max if rolling_max > 0 else 0
            
            self.rolling_max.append(rolling_max)
            self.rolling_drawdown.append(rolling_dd)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current drawdown metrics"""
        return {
            "current_drawdown": self.current_drawdown,
            "current_drawdown_pct": self.current_drawdown * 100,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_pct": self.max_drawdown * 100,
            "current_duration_days": self.current_drawdown_duration,
            "max_duration_days": self.max_drawdown_duration,
            "in_drawdown": self.in_drawdown,
            "drawdown_periods_count": len(self.drawdown_periods)
        }
    
    def get_recent_drawdowns(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get recent drawdown periods"""
        recent = self.drawdown_periods[-n:]
        return [
            {
                "start": p.start_date.isoformat(),
                "peak": p.peak_value,
                "trough": p.trough_value,
                "drawdown_pct": p.drawdown_pct * 100,
                "duration_days": p.duration_days,
                "is_recovered": p.is_recovered
            }
            for p in recent
        ]
    
    def get_rolling_stats(self) -> Dict[str, Any]:
        """Get rolling drawdown statistics"""
        if len(self.rolling_drawdown) < 2:
            return {"mean": 0, "std": 0, "max": 0}
        
        return {
            "mean": np.mean(self.rolling_drawdown),
            "std": np.std(self.rolling_drawdown),
            "max": max(self.rolling_drawdown),
            "current": self.rolling_drawdown[-1] if self.rolling_drawdown else 0
        }
    
    def calculate_recovery_time(
        self,
        drawdown: float,
        avg_return: float = 0.0005  # ~13% annualized
    ) -> int:
        """Estimate recovery time in days"""
        if drawdown <= 0:
            return 0
        
        if avg_return <= 0:
            return float('inf')
        
        # Using logarithm for compound growth
        # (1 + r)^n = 1 / (1 - drawdown)
        # n = log(1/(1-d)) / log(1+r)
        import math
        recovery_return = 1 / (1 - drawdown)
        days = math.log(recovery_return) / math.log(1 + avg_return)
        
        return int(days)
    
    def get_risk_adjusted_metrics(self) -> Dict[str, float]:
        """Calculate risk-adjusted drawdown metrics"""
        if len(self.drawdown_curve) < 2:
            return {"calmar_ratio": 0, "pain_ratio": 0}
        
        total_return = (self.equity_curve[-1] - self.equity_curve[0]) / self.equity_curve[0] if self.equity_curve[0] > 0 else 0
        annualized_return = total_return * (252 / len(self.equity_curve)) if len(self.equity_curve) > 0 else 0
        
        # Calmar Ratio: annualized return / max drawdown
        calmar = annualized_return / self.max_drawdown if self.max_drawdown > 0 else 0
        
        # Pain Ratio: return / average drawdown
        avg_drawdown = np.mean([d for d in self.drawdown_curve if d > 0]) if any(d > 0 for d in self.drawdown_curve) else 0
        pain = total_return / avg_drawdown if avg_drawdown > 0 else 0
        
        return {
            "calmar_ratio": calmar,
            "pain_ratio": pain,
            "annualized_return": annualized_return
        }
    
    def reset(self) -> None:
        """Reset analyzer state"""
        self.current_drawdown = 0.0
        self.max_drawdown = 0.0
        self.max_drawdown_duration = 0
        self.current_drawdown_duration = 0
        self.peak = 0.0
        self.equity_curve.clear()
        self.drawdown_curve.clear()
        self.drawdown_periods.clear()
        self.in_drawdown = False
        self.drawdown_start = None
        self.rolling_max.clear()
        self.rolling_drawdown.clear()
