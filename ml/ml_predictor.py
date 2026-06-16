import numpy as np
from typing import Dict, Any, Optional, List
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os
from datetime import datetime

from .feature_engineer import FeatureEngineer
from models import Prediction


class MLPredictor:
    """Machine Learning predictor for trading signals"""
    
    def __init__(self, model_type: str = "random_forest"):
        """
        Initialize ML predictor
        
        Args:
            model_type: Type of model ('random_forest' or 'gradient_boosting')
        """
        self.model_type = model_type
        self.feature_engineer = FeatureEngineer()
        self.scaler = StandardScaler()
        self.model = None
        self.is_trained = False
        self.model_path = "ml_model.pkl"
        self.scaler_path = "ml_scaler.pkl"
        
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the ML model"""
        if self.model_type == "random_forest":
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
        elif self.model_type == "gradient_boosting":
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                random_state=42
            )
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")
    
    def train(self, historical_data: List[Dict[str, Any]], labels: List[str]) -> Dict[str, Any]:
        """
        Train the ML model
        
        Args:
            historical_data: List of historical market data points
            labels: Corresponding labels ('CALL' or 'PUT')
            
        Returns:
            Training metrics
        """
        # Extract features
        features = []
        valid_indices = []
        
        for i, data in enumerate(historical_data):
            try:
                feature_vector = self.feature_engineer.extract_features(data)
                features.append(feature_vector)
                valid_indices.append(i)
            except Exception as e:
                continue
        
        if not features:
            raise ValueError("No valid features extracted")
        
        X = np.array(features)
        y = np.array([labels[i] for i in valid_indices])
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model
        self.model.fit(X_train_scaled, y_train)
        self.is_trained = True
        
        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        
        # Save model
        self._save_model()
        
        return {
            "accuracy": accuracy,
            "classification_report": classification_report(y_test, y_pred),
            "training_samples": len(X_train),
            "test_samples": len(X_test)
        }
    
    def predict(self, data: Dict[str, Any]) -> Optional[Prediction]:
        """
        Make prediction on new data
        
        Args:
            data: Market data
            
        Returns:
            Prediction object
        """
        if not self.is_trained:
            return None
        
        try:
            # Extract features
            features = self.feature_engineer.extract_features(data)
            features_scaled = self.scaler.transform([features])
            
            # Predict
            prediction = self.model.predict(features_scaled)[0]
            probabilities = self.model.predict_proba(features_scaled)[0]
            confidence = max(probabilities) * 100
            
            return Prediction(
                type="ML",
                direction=prediction,
                confidence=confidence,
                reason=f"ML prediction using {self.model_type}"
            )
        except Exception as e:
            return None
    
    def predict_proba(self, data: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """
        Get prediction probabilities
        
        Args:
            data: Market data
            
        Returns:
            Dictionary of class probabilities
        """
        if not self.is_trained:
            return None
        
        try:
            features = self.feature_engineer.extract_features(data)
            features_scaled = self.scaler.transform([features])
            probabilities = self.model.predict_proba(features_scaled)[0]
            
            return {
                "CALL": float(probabilities[0]),
                "PUT": float(probabilities[1])
            }
        except Exception as e:
            return None
    
    def _save_model(self):
        """Save model and scaler to disk"""
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)
    
    def load_model(self):
        """Load model and scaler from disk"""
        if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
            self.model = joblib.load(self.model_path)
            self.scaler = joblib.load(self.scaler_path)
            self.is_trained = True
            return True
        return False
    
    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """Get feature importance from trained model"""
        if not self.is_trained or not hasattr(self.model, 'feature_importances_'):
            return None
        
        feature_names = self.feature_engineer.get_feature_names()
        importances = self.model.feature_importances_
        
        return dict(zip(feature_names, importances))
