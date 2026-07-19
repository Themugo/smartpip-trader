"""
Feature Marketplace - Reusable Feature Repository

Repository for reusable feature modules with versioning.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class FeatureCategory(Enum):
    """Feature categories"""
    TECHNICAL = "technical"
    STATISTICAL = "statistical"
    PATTERN = "pattern"
    MACHINE_LEARNING = "machine_learning"
    CUSTOM = "custom"


@dataclass
class FeatureDependency:
    """A dependency of a feature"""
    name: str
    version: str
    optional: bool = False


@dataclass
class Feature:
    """A reusable feature module"""
    id: str
    name: str
    category: FeatureCategory
    
    # Description
    description: str
    long_description: str = ""
    
    # Versioning
    version: str = "1.0.0"
    previous_versions: List[str] = field(default_factory=list)
    
    # Implementation
    code: str = ""
    function_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Dependencies
    dependencies: List[FeatureDependency] = field(default_factory=list)
    
    # Metadata
    author: str = ""
    license: str = "MIT"
    tags: List[str] = field(default_factory=list)
    
    # Stats
    downloads: int = 0
    ratings: List[float] = field(default_factory=list)
    usage_count: int = 0
    
    # Status
    is_verified: bool = False
    is_premium: bool = False
    is_beta: bool = False
    
    # Documentation
    examples: List[str] = field(default_factory=list)
    changelog: str = ""
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def avg_rating(self) -> float:
        return sum(self.ratings) / len(self.ratings) if self.ratings else 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "downloads": self.downloads,
            "avg_rating": self.avg_rating,
            "usage_count": self.usage_count,
            "is_verified": self.is_verified,
            "is_premium": self.is_premium,
            "created_at": self.created_at.isoformat(),
        }


class FeatureMarketplace:
    """
    Feature Marketplace for reusable feature modules.
    
    Features:
    - Feature catalog
    - Version control
    - Dependency management
    - Search and filtering
    - Ratings and reviews
    - Installation management
    - Usage tracking
    """
    
    def __init__(self):
        self._features: Dict[str, Feature] = {}
        self._installations: Dict[str, List[str]] = {}  # user_id -> feature_ids
        
        # Register built-in features
        self._register_builtin_features()
    
    def _register_builtin_features(self) -> None:
        """Register built-in features"""
        features = [
            Feature(
                id="technical_rsi",
                name="Relative Strength Index (RSI)",
                category=FeatureCategory.TECHNICAL,
                description="Classic momentum oscillator measuring speed of price changes",
                long_description="""
                    The Relative Strength Index (RSI) is a momentum oscillator that measures the 
                    speed and magnitude of price changes. It oscillates between 0 and 100.
                    
                    **Interpretation:**
                    - RSI > 70: Overbought condition
                    - RSI < 30: Oversold condition
                    - RSI = 50: Neutral
                    
                    **Parameters:**
                    - period: Number of periods (default: 14)
                    - overbought: Overbought threshold (default: 70)
                    - oversold: Oversold threshold (default: 30)
                """,
                code="def calculate_rsi(prices, period=14): ...",
                function_name="calculate_rsi",
                parameters={"period": 14, "overbought": 70, "oversold": 30},
                author="SmartPip Team",
                tags=["momentum", "oscillator", "overbought", "oversold"],
                is_verified=True,
                examples=["calculate_rsi(prices, period=14)"],
            ),
            Feature(
                id="statistical_entropy",
                name="Shannon Entropy",
                category=FeatureCategory.STATISTICAL,
                description="Measure of uncertainty or randomness in data",
                long_description="""
                    Shannon Entropy quantifies the amount of information uncertainty.
                    Lower entropy indicates more predictable patterns.
                    
                    **Applications:**
                    - Market regime detection
                    - Pattern recognition
                    - Signal strength measurement
                """,
                code="def calculate_entropy(data, window=20): ...",
                function_name="calculate_entropy",
                parameters={"window": 20},
                author="SmartPip Team",
                tags=["entropy", "information", "uncertainty"],
                is_verified=True,
            ),
            Feature(
                id="technical_macd",
                name="MACD (Moving Average Convergence Divergence)",
                category=FeatureCategory.TECHNICAL,
                description="Trend-following momentum indicator showing relationship between two moving averages",
                long_description="""
                    The MACD consists of:
                    - MACD Line: 12-period EMA - 26-period EMA
                    - Signal Line: 9-period EMA of MACD Line
                    - Histogram: MACD Line - Signal Line
                """,
                code="def calculate_macd(prices, fast=12, slow=26, signal=9): ...",
                function_name="calculate_macd",
                parameters={"fast": 12, "slow": 26, "signal": 9},
                author="SmartPip Team",
                tags=["trend", "momentum", "convergence", "divergence"],
                is_verified=True,
            ),
            Feature(
                id="statistical_volatility",
                name="Historical Volatility",
                category=FeatureCategory.STATISTICAL,
                description="Statistical measure of asset price dispersion over time",
                long_description="""
                    Historical Volatility measures the standard deviation of logarithmic returns.
                    It's used for:
                    - Risk assessment
                    - Position sizing
                    - Option pricing
                """,
                code="def calculate_historical_volatility(returns, period=20): ...",
                function_name="calculate_historical_volatility",
                parameters={"period": 20, "annualize": True},
                author="SmartPip Team",
                tags=["volatility", "risk", "standard_deviation"],
                is_verified=True,
            ),
            Feature(
                id="pattern_head_shoulders",
                name="Head and Shoulders Pattern",
                category=FeatureCategory.PATTERN,
                description="Technical analysis pattern indicating trend reversal",
                long_description="""
                    The Head and Shoulders pattern is a chart formation that appears
                    as a baseline with three peaks, where the middle peak is highest.
                    
                    **Variants:**
                    - Standard Head and Shoulders (bearish reversal)
                    - Inverse Head and Shoulders (bullish reversal)
                """,
                code="def detect_head_shoulders(prices, tolerance=0.02): ...",
                function_name="detect_head_shoulders",
                parameters={"tolerance": 0.02, "lookback": 100},
                author="SmartPip Team",
                tags=["pattern", "reversal", "technical"],
                is_verified=True,
            ),
            Feature(
                id="ml_random_forest",
                name="Random Forest Classifier",
                category=FeatureCategory.MACHINE_LEARNING,
                description="Ensemble learning method for classification using multiple decision trees",
                long_description="""
                    Random Forest is an ensemble method that constructs multiple decision trees
                    and outputs the mode of their predictions.
                    
                    **Advantages:**
                    - Handles high-dimensional data
                    - Resistant to overfitting
                    - Provides feature importance
                """,
                code="class RandomForestClassifier: ...",
                function_name="predict",
                parameters={
                    "n_estimators": 100,
                    "max_depth": 10,
                    "min_samples_split": 5,
                },
                dependencies=[
                    FeatureDependency("sklearn", "1.0"),
                ],
                author="SmartPip Team",
                tags=["ml", "classification", "ensemble", "trees"],
                is_verified=True,
            ),
            Feature(
                id="statistical_momentum",
                name="Price Momentum",
                category=FeatureCategory.STATISTICAL,
                description="Rate of change in price over a period",
                long_description="""
                    Momentum measures the rate of acceleration of price.
                    High momentum suggests strong trends.
                """,
                code="def calculate_momentum(prices, period=10): ...",
                function_name="calculate_momentum",
                parameters={"period": 10, "method": "roc"},
                author="SmartPip Team",
                tags=["momentum", "rate_of_change"],
                is_verified=True,
            ),
            Feature(
                id="statistical_ autocorrelation",
                name="Autocorrelation",
                category=FeatureCategory.STATISTICAL,
                description="Correlation of a signal with a delayed copy of itself",
                long_description="""
                    Autocorrelation measures how correlated a time series is with itself
                    at different lags. Useful for detecting seasonality and patterns.
                """,
                code="def calculate_autocorrelation(series, lags=20): ...",
                function_name="calculate_autocorrelation",
                parameters={"lags": 20, "method": "pearson"},
                author="SmartPip Team",
                tags=["autocorrelation", "lag", "correlation"],
                is_verified=True,
            ),
        ]
        
        for feature in features:
            self._features[feature.id] = feature
        
        logger.info(f"Registered {len(features)} built-in features")
    
    def add_feature(self, feature: Feature) -> str:
        """Add a feature to the marketplace"""
        feature.id = feature.id or str(uuid.uuid4())
        self._features[feature.id] = feature
        return feature.id
    
    def get_feature(self, feature_id: str) -> Optional[Feature]:
        """Get a feature by ID"""
        return self._features.get(feature_id)
    
    def search_features(
        self,
        query: Optional[str] = None,
        category: Optional[FeatureCategory] = None,
        tags: Optional[List[str]] = None,
        verified_only: bool = False,
        sort_by: str = "downloads",
        limit: int = 50,
    ) -> List[Feature]:
        """Search for features"""
        results = list(self._features.values())
        
        # Filter by query
        if query:
            query_lower = query.lower()
            results = [
                f for f in results
                if query_lower in f.name.lower() or query_lower in f.description.lower()
            ]
        
        # Filter by category
        if category:
            results = [f for f in results if f.category == category]
        
        # Filter by tags
        if tags:
            results = [f for f in results if any(t in f.tags for t in tags)]
        
        # Filter verified only
        if verified_only:
            results = [f for f in results if f.is_verified]
        
        # Sort
        if sort_by == "downloads":
            results.sort(key=lambda f: f.downloads, reverse=True)
        elif sort_by == "rating":
            results.sort(key=lambda f: f.avg_rating, reverse=True)
        elif sort_by == "recent":
            results.sort(key=lambda f: f.created_at, reverse=True)
        elif sort_by == "usage":
            results.sort(key=lambda f: f.usage_count, reverse=True)
        
        return results[:limit]
    
    def get_features_by_category(self, category: FeatureCategory) -> List[Feature]:
        """Get all features in a category"""
        return self.search_features(category=category)
    
    def install_feature(self, user_id: str, feature_id: str) -> bool:
        """Install a feature for a user"""
        feature = self._features.get(feature_id)
        if not feature:
            return False
        
        if user_id not in self._installations:
            self._installations[user_id] = []
        
        if feature_id not in self._installations[user_id]:
            self._installations[user_id].append(feature_id)
            feature.downloads += 1
        
        return True
    
    def uninstall_feature(self, user_id: str, feature_id: str) -> bool:
        """Uninstall a feature for a user"""
        if user_id in self._installations:
            if feature_id in self._installations[user_id]:
                self._installations[user_id].remove(feature_id)
                return True
        return False
    
    def get_installed_features(self, user_id: str) -> List[Feature]:
        """Get all installed features for a user"""
        installed_ids = self._installations.get(user_id, [])
        return [self._features[fid] for fid in installed_ids if fid in self._features]
    
    def rate_feature(self, feature_id: str, rating: float) -> bool:
        """Rate a feature (1-5 stars)"""
        feature = self._features.get(feature_id)
        if not feature:
            return False
        
        feature.ratings.append(min(5, max(1, rating)))
        return True
    
    def increment_usage(self, feature_id: str) -> None:
        """Increment feature usage count"""
        feature = self._features.get(feature_id)
        if feature:
            feature.usage_count += 1
    
    def get_feature_code(self, feature_id: str) -> Optional[str]:
        """Get the code for a feature"""
        feature = self._features.get(feature_id)
        return feature.code if feature else None
    
    def validate_dependencies(
        self,
        feature_id: str,
        installed_features: List[str],
    ) -> tuple[bool, List[str]]:
        """Validate feature dependencies"""
        feature = self._features.get(feature_id)
        if not feature:
            return False, ["Feature not found"]
        
        missing = []
        
        for dep in feature.dependencies:
            if dep.name not in installed_features:
                if not dep.optional:
                    missing.append(f"{dep.name} (version {dep.version})")
        
        return len(missing) == 0, missing
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get marketplace statistics"""
        features = list(self._features.values())
        
        return {
            "total_features": len(features),
            "by_category": {
                cat.value: sum(1 for f in features if f.category == cat)
                for cat in FeatureCategory
            },
            "total_downloads": sum(f.downloads for f in features),
            "avg_rating": sum(f.avg_rating for f in features) / len(features) if features else 0,
            "verified_count": sum(1 for f in features if f.is_verified),
            "total_installations": sum(len(installs) for installs in self._installations.values()),
        }
