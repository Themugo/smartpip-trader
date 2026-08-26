"""
AI Explainability Integration - Hook into AI Core Orchestrator

This module integrates the explainability system with the AI Core Orchestrator
to automatically generate and store explanations for every AI decision.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from dataclasses import asdict

from ai_explainability import AIExplainer, ExplanationStorage, ExplanationSearch
from ai_explainability.explainer import ExplanationRequest

logger = logging.getLogger(__name__)


class ExplainabilityIntegrator:
    """
    Integrates AI explainability with the trading system.
    
    This class:
    - Hooks into the AI Core Orchestrator
    - Automatically generates explanations for every decision
    - Stores explanations for audit and compliance
    - Provides search and retrieval capabilities
    """
    
    def __init__(self, storage_path: str = "ai_explanations.db"):
        """
        Initialize the integrator.
        
        Args:
            storage_path: Path to the explanation database
        """
        self.storage = ExplanationStorage(storage_path)
        self.explainer = AIExplainer()
        self.search = ExplanationSearch(self.storage)
        
        self._hooks: List[Callable] = []
        self._enabled = True
        
        logger.info("ExplainabilityIntegrator initialized")
    
    def enable(self):
        """Enable automatic explanation generation"""
        self._enabled = True
        logger.info("Explainability enabled")
    
    def disable(self):
        """Disable automatic explanation generation"""
        self._enabled = False
        logger.info("Explainability disabled")
    
    def add_hook(self, callback: Callable):
        """Add a callback to be called when explanations are generated"""
        self._hooks.append(callback)
    
    async def explain_decision(
        self,
        decision_id: str,
        decision_result: Any,
        context: Dict[str, Any],
    ) -> Optional[str]:
        """
        Generate explanation for a decision result.
        
        Args:
            decision_id: Unique decision identifier
            decision_result: The decision result from orchestrator
            context: Decision context data
            
        Returns:
            Explanation ID if generated, None otherwise
        """
        if not self._enabled:
            return None
        
        try:
            # Build explanation request from context
            request = self._build_request(decision_id, decision_result, context)
            
            # Generate explanation
            response = await self.explainer.generate_explanation(request)
            
            # Store explanation
            self.storage.save_explanation(response)
            
            # Call hooks
            for hook in self._hooks:
                try:
                    hook(response)
                except Exception as e:
                    logger.error(f"Hook error: {e}")
            
            logger.info(f"Generated explanation {response.explanation_id} for decision {decision_id}")
            return response.explanation_id
            
        except Exception as e:
            logger.error(f"Error generating explanation: {e}")
            return None
    
    def _build_request(
        self,
        decision_id: str,
        decision_result: Any,
        context: Dict[str, Any],
    ) -> ExplanationRequest:
        """Build explanation request from decision data"""
        
        # Extract decision info
        action = getattr(decision_result, 'action', '') or context.get('action', 'HOLD')
        confidence = getattr(decision_result, 'confidence', 0) or context.get('confidence', 0)
        expected_value = getattr(decision_result, 'expected_value', 0) or context.get('expected_value', 0)
        risk_score = getattr(decision_result, 'risk_score', 0) or context.get('risk_score', 0)
        
        # Get analyzer signals from context
        analyzer_signals = context.get('analyzer_signals', {})
        consensus = context.get('consensus', {})
        
        # Get market data
        market_regime = context.get('regime', 'unknown')
        volatility = context.get('volatility', 0)
        symbol = context.get('symbol', '')
        price = context.get('price', 0)
        
        # Build request
        request = ExplanationRequest(
            decision_id=decision_id,
            action=action,
            confidence=confidence,
            symbol=symbol,
            price=price,
            market_regime=market_regime,
            volatility=volatility,
            analyzer_signals=analyzer_signals,
            consensus=consensus,
            feature_importance=context.get('feature_importance', {}),
            decision_tree=context.get('decision_tree', []),
            alternatives_considered=context.get('alternatives', []),
            rejection_reasons=context.get('rejection_reasons', []),
            expected_value=expected_value,
            risk_score=risk_score,
            uncertainty_estimate=context.get('uncertainty', 0),
            probability_distribution=context.get('probability_distribution', {}),
            calibration_confidence=context.get('calibration_confidence', 70),
            historical_accuracy=context.get('historical_accuracy', 50),
            similar_past_decisions=context.get('historical_analogues', []),
            balance=context.get('balance', 0),
            equity=context.get('equity', 0),
            current_exposure=context.get('current_exposure', 0),
        )
        
        return request
    
    def get_explanation(self, explanation_id: str) -> Optional[Dict[str, Any]]:
        """Get explanation by ID"""
        return self.storage.get_explanation(explanation_id)
    
    def search_explanations(
        self,
        query: str = "",
        action: Optional[str] = None,
        symbol: Optional[str] = None,
        min_confidence: Optional[float] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search explanations"""
        from ai_explainability.search import SearchQuery, SortField, SortOrder
        
        search_query = SearchQuery(
            text_query=query,
            action=action,
            symbol=symbol,
            min_confidence=min_confidence,
            limit=limit,
            sort_by=SortField.TIMESTAMP,
            sort_order=SortOrder.DESC,
        )
        
        results = self.search.search(search_query)
        return [
            {
                "explanation_id": r.explanation_id,
                "decision_id": r.decision_id,
                "timestamp": r.timestamp,
                "action": r.action,
                "symbol": r.symbol,
                "confidence": r.confidence,
                "risk_level": r.risk_level,
                "expected_value": r.expected_value,
                "summary": r.summary,
            }
            for r in results
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get explanation statistics"""
        return self.storage.get_explanation_statistics()


class ExplainabilityMiddleware:
    """
    Middleware to wrap orchestrator decisions with explanation generation.
    
    Usage:
        middleware = ExplainabilityMiddleware(integrator)
        orchestrator.add_validator(middleware)
    """
    
    def __init__(self, integrator: ExplainabilityIntegrator):
        self.integrator = integrator
        self.name = "explainability"
    
    async def on_decision(
        self,
        decision_id: str,
        decision_result: Any,
        context: Dict[str, Any],
    ) -> None:
        """Called after each decision"""
        await self.integrator.explain_decision(decision_id, decision_result, context)


def create_integrator(config: Optional[Dict[str, Any]] = None) -> ExplainabilityIntegrator:
    """
    Create and configure an explainability integrator.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Configured ExplainabilityIntegrator
    """
    config = config or {}
    storage_path = config.get('storage_path', 'ai_explanations.db')
    
    integrator = ExplainabilityIntegrator(storage_path)
    
    # Add logging hook
    def log_hook(response):
        logger.info(
            f"Explanation {response.explanation_id}: "
            f"{response.executive_summary.get('action')} "
            f"{response.executive_summary.get('symbol')} "
            f"@ {response.executive_summary.get('confidence')}% confidence"
        )
    
    integrator.add_hook(log_hook)
    
    return integrator


# Global instance
_integration: Optional[ExplainabilityIntegrator] = None


def get_integrator() -> ExplainabilityIntegrator:
    """Get the global integrator instance"""
    global _integration
    if _integration is None:
        _integration = create_integrator()
    return _integration


def init_integration(config: Optional[Dict[str, Any]] = None) -> ExplainabilityIntegrator:
    """Initialize the global integration"""
    global _integration
    _integration = create_integrator(config)
    return _integration
