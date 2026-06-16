from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from models import AnalysisResult


class BaseAnalyzer(ABC):
    """Base class for all analysis models with early termination support"""
    
    def __init__(self, min_data_points: int = 10):
        """
        Initialize base analyzer
        
        Args:
            min_data_points: Minimum data points required for analysis
        """
        self.enabled = True
        self.confidence = 0
        self.predictions = []
        self.min_data_points = min_data_points
    
    @abstractmethod
    def analyze(self, data: Dict[str, Any]) -> AnalysisResult:
        """Analyze data and return prediction"""
        pass
    
    def should_skip_analysis(self, data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Check if analysis should be skipped (early termination)
        
        Args:
            data: Input data for analysis
            
        Returns:
            Tuple of (should_skip, reason)
        """
        # Check if analyzer is enabled
        if not self.enabled:
            return True, "Analyzer disabled"
        
        # Check minimum data requirements
        last_20_digits = data.get("last_20_digits", [])
        if len(last_20_digits) < self.min_data_points:
            return True, f"Insufficient data ({len(last_20_digits)} < {self.min_data_points})"
        
        return False, ""
    
    def set_enabled(self, enabled: bool):
        """Enable or disable analyzer"""
        self.enabled = enabled
    
    def is_enabled(self) -> bool:
        """Check if analyzer is enabled"""
        return self.enabled
