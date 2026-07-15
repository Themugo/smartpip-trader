"""
Feature Engineering Studio

Visual feature engineering system for generating statistical features from historical data.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import deque
import numpy as np
from scipy import stats, signal
from scipy.fft import fft

logger = logging.getLogger(__name__)


class FeatureType(Enum):
    """Types of features"""
    ROLLING_STAT = "rolling_stat"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    ENTROPY = "entropy"
    LAG = "lag"
    FREQUENCY = "frequency"
    PATTERN = "pattern"
    DERIVATIVE = "derivative"


class FeatureCategory(Enum):
    """Feature categories"""
    PRICE = "price"
    VOLUME = "volume"
    DIGIT = "digit"
    REGIME = "regime"
    VOLATILITY = "volatility"
    CUSTOM = "custom"


@dataclass
class FeatureDefinition:
    """Definition of a feature"""
    id: str
    name: str
    feature_type: FeatureType
    category: FeatureCategory
    description: str
    
    # Parameters
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "feature_type": self.feature_type.value,
            "category": self.category.value,
            "description": self.description,
            "parameters": self.parameters,
            "created_at": self.created_at.isoformat(),
            "tags": self.tags,
            "is_active": self.is_active,
        }


@dataclass
class FeatureSet:
    """A collection of features"""
    id: str
    name: str
    description: str
    features: List[FeatureDefinition] = field(default_factory=list)
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "features": [f.to_dict() for f in self.features],
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class FeatureEngineer:
    """
    Visual feature engineering system.
    
    Features:
    - Rolling statistics (mean, std, min, max)
    - Entropy measures (Shannon, sample entropy)
    - Momentum indicators (ROC, momentum)
    - Volatility measures (ATR, std)
    - Lag features
    - Frequency-domain features (FFT)
    - Feature selection
    - Feature importance ranking
    """
    
    # Built-in feature definitions
    BUILTIN_FEATURES = {
        # Rolling statistics
        "rolling_mean_5": FeatureDefinition(
            id="rolling_mean_5",
            name="5-Period Rolling Mean",
            feature_type=FeatureType.ROLLING_STAT,
            category=FeatureCategory.PRICE,
            description="Simple moving average over 5 periods",
            parameters={"window": 5, "stat": "mean"},
        ),
        "rolling_std_10": FeatureDefinition(
            id="rolling_std_10",
            name="10-Period Rolling Std",
            feature_type=FeatureType.ROLLING_STAT,
            category=FeatureCategory.VOLATILITY,
            description="Rolling standard deviation over 10 periods",
            parameters={"window": 10, "stat": "std"},
        ),
        "rolling_min_5": FeatureDefinition(
            id="rolling_min_5",
            name="5-Period Rolling Min",
            feature_type=FeatureType.ROLLING_STAT,
            category=FeatureCategory.PRICE,
            description="Minimum price over 5 periods",
            parameters={"window": 5, "stat": "min"},
        ),
        "rolling_max_5": FeatureDefinition(
            id="rolling_max_5",
            name="5-Period Rolling Max",
            feature_type=FeatureType.ROLLING_STAT,
            category=FeatureCategory.PRICE,
            description="Maximum price over 5 periods",
            parameters={"window": 5, "stat": "max"},
        ),
        
        # Momentum
        "roc_5": FeatureDefinition(
            id="roc_5",
            name="Rate of Change (5)",
            feature_type=FeatureType.MOMENTUM,
            category=FeatureCategory.PRICE,
            description="Rate of change over 5 periods",
            parameters={"period": 5},
        ),
        "momentum_10": FeatureDefinition(
            id="momentum_10",
            name="Momentum (10)",
            feature_type=FeatureType.MOMENTUM,
            category=FeatureCategory.PRICE,
            description="Price momentum over 10 periods",
            parameters={"period": 10},
        ),
        
        # Volatility
        "atr_14": FeatureDefinition(
            id="atr_14",
            name="ATR (14)",
            feature_type=FeatureType.VOLATILITY,
            category=FeatureCategory.VOLATILITY,
            description="Average True Range over 14 periods",
            parameters={"period": 14, "method": "atr"},
        ),
        "historical_vol_20": FeatureDefinition(
            id="historical_vol_20",
            name="Historical Volatility (20)",
            feature_type=FeatureType.VOLATILITY,
            category=FeatureCategory.VOLATILITY,
            description="Rolling historical volatility over 20 periods",
            parameters={"period": 20},
        ),
        
        # Entropy
        "shannon_entropy_10": FeatureDefinition(
            id="shannon_entropy_10",
            name="Shannon Entropy (10)",
            feature_type=FeatureType.ENTROPY,
            category=FeatureCategory.DIGIT,
            description="Shannon entropy of last digit distribution over 10 periods",
            parameters={"window": 10, "method": "shannon"},
        ),
        "sample_entropy_20": FeatureDefinition(
            id="sample_entropy_20",
            name="Sample Entropy (20)",
            feature_type=FeatureType.ENTROPY,
            category=FeatureCategory.DIGIT,
            description="Sample entropy over 20 periods",
            parameters={"window": 20, "method": "sample"},
        ),
        
        # Lag features
        "price_lag_1": FeatureDefinition(
            id="price_lag_1",
            name="Price Lag 1",
            feature_type=FeatureType.LAG,
            category=FeatureCategory.PRICE,
            description="Previous price (1 period lag)",
            parameters={"lag": 1},
        ),
        "price_lag_5": FeatureDefinition(
            id="price_lag_5",
            name="Price Lag 5",
            feature_type=FeatureType.LAG,
            category=FeatureCategory.PRICE,
            description="Price from 5 periods ago",
            parameters={"lag": 5},
        ),
        "return_lag_1": FeatureDefinition(
            id="return_lag_1",
            name="Return Lag 1",
            feature_type=FeatureType.LAG,
            category=FeatureCategory.PRICE,
            description="Log return from 1 period ago",
            parameters={"lag": 1, "return": True},
        ),
        
        # Frequency features
        "dominant_frequency": FeatureDefinition(
            id="dominant_frequency",
            name="Dominant Frequency",
            feature_type=FeatureType.FREQUENCY,
            category=FeatureCategory.PRICE,
            description="Dominant frequency from FFT analysis",
            parameters={"window": 50},
        ),
        "spectral_entropy": FeatureDefinition(
            id="spectral_entropy",
            name="Spectral Entropy",
            feature_type=FeatureType.FREQUENCY,
            category=FeatureCategory.PRICE,
            description="Spectral entropy from frequency analysis",
            parameters={"window": 50},
        ),
        
        # Digit features
        "last_digit": FeatureDefinition(
            id="last_digit",
            name="Last Digit",
            feature_type=FeatureType.DERIVATIVE,
            category=FeatureCategory.DIGIT,
            description="Last digit of current price",
            parameters={"digit_position": -1},
        ),
        "digit_imbalance": FeatureDefinition(
            id="digit_imbalance",
            name="Digit Imbalance",
            feature_type=FeatureType.DERIVATIVE,
            category=FeatureCategory.DIGIT,
            description="Imbalance between even/odd digits",
            parameters={"window": 20},
        ),
    }
    
    def __init__(self, storage_path: str = "data/features"):
        self._storage_path = storage_path
        self._feature_sets: Dict[str, FeatureSet] = {}
        self._custom_features: Dict[str, FeatureDefinition] = {}
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_feature_sets()
    
    def _load_feature_sets(self) -> None:
        """Load feature sets from storage"""
        sets_file = os.path.join(self._storage_path, "feature_sets.json")
        
        if os.path.exists(sets_file):
            try:
                with open(sets_file, "r") as f:
                    data = json.load(f)
                
                for set_data in data.get("sets", []):
                    features = [
                        FeatureDefinition(**f) if isinstance(f, dict) else f
                        for f in set_data.get("features", [])
                    ]
                    set_data["features"] = features
                    self._feature_sets[set_data["id"]] = FeatureSet(**set_data)
                
                logger.info(f"Loaded {len(self._feature_sets)} feature sets")
            except Exception as e:
                logger.error(f"Failed to load feature sets: {e}")
    
    def _save_feature_sets(self) -> None:
        """Save feature sets to storage"""
        sets_file = os.path.join(self._storage_path, "feature_sets.json")
        
        data = {
            "sets": [fs.to_dict() for fs in self._feature_sets.values()]
        }
        
        try:
            with open(sets_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save feature sets: {e}")
    
    def create_feature_set(
        self,
        name: str,
        description: str,
        feature_ids: List[str],
    ) -> FeatureSet:
        """Create a new feature set"""
        import uuid
        
        features = []
        for fid in feature_ids:
            # Check built-in features
            if fid in self.BUILTIN_FEATURES:
                features.append(self.BUILTIN_FEATURES[fid])
            # Check custom features
            elif fid in self._custom_features:
                features.append(self._custom_features[fid])
        
        feature_set = FeatureSet(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            features=features,
        )
        
        self._feature_sets[feature_set.id] = feature_set
        self._save_feature_sets()
        
        return feature_set
    
    def get_feature_set(self, set_id: str) -> Optional[FeatureSet]:
        """Get a feature set by ID"""
        return self._feature_sets.get(set_id)
    
    def get_all_feature_sets(self) -> List[FeatureSet]:
        """Get all feature sets"""
        return list(self._feature_sets.values())
    
    def compute_features(
        self,
        feature_set: FeatureSet,
        price_data: List[float],
        digit_data: Optional[List[int]] = None,
    ) -> Dict[str, float]:
        """
        Compute features for given data.
        
        Args:
            feature_set: Feature set to compute
            price_data: List of price values
            digit_data: Optional list of last digits
            
        Returns:
            Dictionary of feature_id -> computed value
        """
        results = {}
        prices = np.array(price_data)
        
        for feature in feature_set.features:
            try:
                value = self._compute_feature(feature, prices, digit_data)
                results[feature.id] = value
            except Exception as e:
                logger.error(f"Error computing feature {feature.id}: {e}")
                results[feature.id] = None
        
        return results
    
    def _compute_feature(
        self,
        feature: FeatureDefinition,
        prices: np.ndarray,
        digits: Optional[np.ndarray],
    ) -> Optional[float]:
        """Compute a single feature"""
        params = feature.parameters
        
        if feature.feature_type == FeatureType.ROLLING_STAT:
            return self._compute_rolling_stat(prices, params)
        
        elif feature.feature_type == FeatureType.MOMENTUM:
            return self._compute_momentum(prices, params)
        
        elif feature.feature_type == FeatureType.VOLATILITY:
            return self._compute_volatility(prices, params)
        
        elif feature.feature_type == FeatureType.ENTROPY:
            return self._compute_entropy(digits or self._extract_digits(prices), params)
        
        elif feature.feature_type == FeatureType.LAG:
            return self._compute_lag(prices, params)
        
        elif feature.feature_type == FeatureType.FREQUENCY:
            return self._compute_frequency_feature(prices, params)
        
        elif feature.feature_type == FeatureType.DERIVATIVE:
            return self._compute_derivative(prices, params)
        
        return None
    
    def _compute_rolling_stat(
        self,
        prices: np.ndarray,
        params: Dict[str, Any],
    ) -> float:
        """Compute rolling statistic"""
        window = params.get("window", 5)
        stat = params.get("stat", "mean")
        
        if len(prices) < window:
            return None
        
        window_prices = prices[-window:]
        
        if stat == "mean":
            return float(np.mean(window_prices))
        elif stat == "std":
            return float(np.std(window_prices))
        elif stat == "min":
            return float(np.min(window_prices))
        elif stat == "max":
            return float(np.max(window_prices))
        elif stat == "median":
            return float(np.median(window_prices))
        
        return None
    
    def _compute_momentum(
        self,
        prices: np.ndarray,
        params: Dict[str, Any],
    ) -> float:
        """Compute momentum indicator"""
        period = params.get("period", 10)
        
        if len(prices) < period + 1:
            return None
        
        current = prices[-1]
        past = prices[-(period + 1)]
        
        # Rate of change
        if params.get("method") == "roc":
            return float((current - past) / past * 100) if past != 0 else 0
        
        # Simple momentum
        return float(current - past)
    
    def _compute_volatility(
        self,
        prices: np.ndarray,
        params: Dict[str, Any],
    ) -> float:
        """Compute volatility measure"""
        method = params.get("method", "std")
        period = params.get("period", 20)
        
        if len(prices) < period:
            return None
        
        returns = np.diff(np.log(prices[-period:]))
        
        if method == "atr":
            # Average True Range approximation
            diffs = np.abs(np.diff(prices[-period:]))
            return float(np.mean(diffs))
        
        elif method == "std":
            return float(np.std(returns)) * np.sqrt(period)
        
        return None
    
    def _compute_entropy(
        self,
        digits: np.ndarray,
        params: Dict[str, Any],
    ) -> float:
        """Compute entropy measure"""
        window = params.get("window", 10)
        method = params.get("method", "shannon")
        
        if len(digits) < window:
            return None
        
        window_digits = digits[-window:]
        
        # Count frequencies
        unique, counts = np.unique(window_digits, return_counts=True)
        probs = counts / len(window_digits)
        
        if method == "shannon":
            # Shannon entropy
            return float(-np.sum(probs * np.log2(probs + 1e-10)))
        
        elif method == "sample":
            # Sample entropy approximation
            m = 2
            r = 0.2 * np.std(window_digits)
            
            # Count matches
            def _count_matches(data, m, r):
                count = 0
                for i in range(len(data) - m):
                    for j in range(i + 1, len(data) - m):
                        if np.abs(data[i] - data[j]) < r:
                            count += 1
                return count
            
            matches_m = _count_matches(window_digits, m, r)
            matches_m1 = _count_matches(window_digits, m + 1, r)
            
            if matches_m1 == 0 or matches_m == 0:
                return None
            
            return float(-np.log(matches_m1 / matches_m))
        
        return None
    
    def _compute_lag(
        self,
        prices: np.ndarray,
        params: Dict[str, Any],
    ) -> Optional[float]:
        """Compute lag feature"""
        lag = params.get("lag", 1)
        is_return = params.get("return", False)
        
        if len(prices) < lag + 1:
            return None
        
        if is_return:
            return float(np.log(prices[-1] / prices[-(lag + 1)]))
        
        return float(prices[-(lag + 1)])
    
    def _compute_frequency_feature(
        self,
        prices: np.ndarray,
        params: Dict[str, Any],
    ) -> float:
        """Compute frequency-domain feature"""
        window = params.get("window", 50)
        method = params.get("method", "dominant")
        
        if len(prices) < window:
            return None
        
        window_prices = prices[-window:]
        
        # FFT
        fft_vals = fft(window_prices - np.mean(window_prices))
        power = np.abs(fft_vals[:len(fft_vals) // 2]) ** 2
        
        freqs = np.fft.fftfreq(len(window_prices))[:len(window_prices) // 2]
        
        if method == "dominant":
            # Dominant frequency
            dominant_idx = np.argmax(power[1:]) + 1
            return float(abs(freqs[dominant_idx]))
        
        elif method == "spectral_entropy":
            # Spectral entropy
            power_norm = power / (np.sum(power) + 1e-10)
            return float(-np.sum(power_norm * np.log2(power_norm + 1e-10)))
        
        return None
    
    def _compute_derivative(
        self,
        prices: np.ndarray,
        params: Dict[str, Any],
    ) -> float:
        """Compute derivative features"""
        if len(prices) < 2:
            return None
        
        if params.get("digit_position") == -1:
            # Last digit
            return float(int(str(int(prices[-1]))[-1]) if prices[-1] >= 0 else 0)
        
        # Price change
        return float(prices[-1] - prices[-2])
    
    def _extract_digits(self, prices: np.ndarray) -> np.ndarray:
        """Extract last digits from prices"""
        digits = []
        for p in prices:
            price_str = f"{p:.4f}"
            last_digit = int(price_str[-1])
            digits.append(last_digit)
        return np.array(digits)
    
    def compute_feature_importance(
        self,
        feature_set: FeatureSet,
        X: np.ndarray,
        y: np.ndarray,
    ) -> Dict[str, float]:
        """
        Compute feature importance using correlation.
        
        Args:
            feature_set: Feature set
            X: Feature matrix (n_samples, n_features)
            y: Target values
            
        Returns:
            Dictionary of feature_id -> importance score
        """
        from sklearn.ensemble import RandomForestClassifier
        
        importance_scores = {}
        
        for i, feature in enumerate(feature_set.features):
            if i >= X.shape[1]:
                continue
            
            # Correlation with target
            corr = abs(np.corrcoef(X[:, i], y)[0, 1])
            importance_scores[feature.id] = float(corr) if not np.isnan(corr) else 0
        
        return importance_scores
    
    def get_builtin_features(self) -> Dict[str, FeatureDefinition]:
        """Get all built-in features"""
        return self.BUILTIN_FEATURES.copy()
    
    def delete_feature_set(self, set_id: str) -> bool:
        """Delete a feature set"""
        if set_id in self._feature_sets:
            del self._feature_sets[set_id]
            self._save_feature_sets()
            return True
        return False
