"""
AI Explainability Module - Making Every AI Decision Transparent

This module provides comprehensive explainability for all AI trading decisions:
- Executive summaries for stakeholders
- Detailed reasoning chains for analysts
- Technical explanations for developers
- Research-grade analysis for researchers
- Full audit trail for compliance

Quick Start:
    from ai_explainability import init_integration, ExplanationStorage
    
    # Initialize integration
    integrator = init_integration({'storage_path': 'explanations.db'})
    
    # Or use storage directly
    storage = ExplanationStorage('explanations.db')
    
    # Search explanations
    results = integrator.search_explanations(query="EUR/USD", min_confidence=70)
"""

from .explainer import AIExplainer, ExplanationRequest, ExplanationResponse, ExplanationLevel
from .storage import ExplanationStorage
from .audit_viewer import AuditViewer, DecisionReconstruction
from .search import ExplanationSearch
from .integration import (
    ExplainabilityIntegrator,
    ExplainabilityMiddleware,
    create_integrator,
    get_integrator,
    init_integration,
)

__all__ = [
    # Core classes
    "AIExplainer",
    "ExplanationRequest", 
    "ExplanationResponse",
    "ExplanationLevel",
    
    # Storage
    "ExplanationStorage",
    
    # Search
    "ExplanationSearch",
    
    # Audit
    "AuditViewer",
    "DecisionReconstruction",
    
    # Integration
    "ExplainabilityIntegrator",
    "ExplainabilityMiddleware",
    "create_integrator",
    "get_integrator",
    "init_integration",
]
