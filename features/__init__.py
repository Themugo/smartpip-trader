"""
Feature Engineering Studio

Visual feature engineering system:
- Rolling statistics
- Entropy measures
- Momentum features
- Volatility measures
- Lag features
- Frequency-domain features
- Feature selection
- Feature importance
"""

from features.engineer import FeatureEngineer, FeatureDefinition, FeatureSet

__all__ = [
    "FeatureEngineer",
    "FeatureDefinition",
    "FeatureSet",
]
