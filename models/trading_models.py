from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class Prediction:
    """Trading prediction from analysis models"""
    type: str
    direction: str
    confidence: float
    reason: str


@dataclass
class AnalysisResult:
    """Result from analysis model"""
    model_name: str
    prediction: Optional[str]
    confidence: float
    data: Dict[str, Any]


@dataclass
class Trade:
    """Trade information"""
    id: str
    market: str
    type: str
    direction: str
    amount: float
    confidence: float
    reason: str
    entry_price: float
    entry_time: str
    profit: Optional[float] = None
    exit_time: Optional[str] = None
