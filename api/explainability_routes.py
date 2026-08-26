"""
AI Explainability API Routes

REST API endpoints for AI decision explanations.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from dataclasses import asdict

from aiohttp import web
from ai_explainability import (
    AIExplainer,
    ExplanationStorage,
    ExplanationSearch,
    AuditViewer,
    ExplanationRequest,
    ExplanationLevel,
)
from ai_explainability.formatters import HTMLFormatter, MarkdownFormatter, JSONFormatter

logger = logging.getLogger(__name__)


class ExplainabilityRoutes:
    """API routes for AI explainability"""
    
    def __init__(self, storage: ExplanationStorage):
        self.storage = storage
        self.explainer = AIExplainer()
        self.search = ExplanationSearch(storage)
        self.audit_viewer = AuditViewer(storage)
        
        self.html_formatter = HTMLFormatter()
        self.markdown_formatter = MarkdownFormatter()
        self.json_formatter = JSONFormatter()
        
        logger.info("ExplainabilityRoutes initialized")
    
    def setup_routes(self, app: web.Application):
        """Setup routes for the application"""
        routes = [
            # Explanation generation
            ("POST", "/api/explainability/explain", self.handle_explain),
            
            # Explanation retrieval
            ("GET", "/api/explainability/explanation/{id}", self.handle_get_explanation),
            ("GET", "/api/explainability/explanation/decision/{decision_id}", self.handle_get_by_decision),
            
            # Search
            ("GET", "/api/explainability/search", self.handle_search),
            ("GET", "/api/explainability/recent", self.handle_recent),
            
            # Audit
            ("GET", "/api/explainability/audit/{id}", self.handle_audit),
            ("GET", "/api/explainability/reconstruct/{id}", self.handle_reconstruct),
            ("GET", "/api/explainability/audit-package/{id}", self.handle_audit_package),
            
            # Replay
            ("GET", "/api/explainability/replay/{id}", self.handle_replay),
            
            # Statistics
            ("GET", "/api/explainability/stats", self.handle_stats),
            
            # Formatted output
            ("GET", "/api/explainability/html/{id}", self.handle_html),
            ("GET", "/api/explainability/markdown/{id}", self.handle_markdown),
            ("GET", "/api/explainability/json/{id}", self.handle_json),
        ]
        
        for method, path, handler in routes:
            if method == "GET":
                app.router.add_get(path, handler)
            elif method == "POST":
                app.router.add_post(path, handler)
        
        logger.info(f"Setup {len(routes)} explainability routes")
    
    async def handle_explain(self, request: web.Request) -> web.Response:
        """
        Generate explanation for a decision.
        
        POST /api/explainability/explain
        {
            "decision_id": "...",
            "action": "BUY",
            "confidence": 75,
            ...
        }
        """
        try:
            data = await request.json()
            
            # Convert to ExplanationRequest
            request_obj = ExplanationRequest(
                decision_id=data.get("decision_id", ""),
                action=data.get("action", ""),
                confidence=data.get("confidence", 0),
                symbol=data.get("symbol", ""),
                price=data.get("price", 0),
                market_regime=data.get("market_regime", "unknown"),
                volatility=data.get("volatility", 0),
                analyzer_signals=data.get("analyzer_signals", {}),
                consensus=data.get("consensus", {}),
                feature_importance=data.get("feature_importance", {}),
                decision_tree=data.get("decision_tree", []),
                alternatives_considered=data.get("alternatives_considered", []),
                rejection_reasons=data.get("rejection_reasons", []),
                expected_value=data.get("expected_value", 0),
                risk_score=data.get("risk_score", 0),
                uncertainty_estimate=data.get("uncertainty_estimate", 0),
                probability_distribution=data.get("probability_distribution", {}),
                calibration_confidence=data.get("calibration_confidence", 0),
                historical_accuracy=data.get("historical_accuracy", 0),
                similar_past_decisions=data.get("similar_past_decisions", []),
                balance=data.get("balance", 0),
                equity=data.get("equity", 0),
                current_exposure=data.get("current_exposure", 0),
            )
            
            # Generate explanation
            response = await self.explainer.generate_explanation(request_obj)
            
            # Save to storage
            response_dict = response.to_dict()
            self.storage.save_explanation_from_request(
                explanation_id=response.explanation_id,
                decision_id=response.decision_id,
                request_data=data,
                response_data=response_dict,
            )
            
            return web.json_response({
                "success": True,
                "explanation_id": response.explanation_id,
                "explanation": response_dict,
            })
            
        except Exception as e:
            logger.error(f"Error generating explanation: {e}")
            return web.json_response({
                "success": False,
                "error": str(e),
            }, status=500)
    
    async def handle_get_explanation(self, request: web.Request) -> web.Response:
        """Get explanation by ID"""
        explanation_id = request.match_info["id"]
        
        explanation = self.storage.get_explanation(explanation_id)
        
        if not explanation:
            return web.json_response({
                "success": False,
                "error": "Explanation not found",
            }, status=404)
        
        return web.json_response({
            "success": True,
            "explanation": explanation,
        })
    
    async def handle_get_by_decision(self, request: web.Request) -> web.Response:
        """Get explanation by decision ID"""
        decision_id = request.match_info["decision_id"]
        
        explanation = self.storage.get_explanation_by_decision(decision_id)
        
        if not explanation:
            return web.json_response({
                "success": False,
                "error": "Explanation not found for this decision",
            }, status=404)
        
        return web.json_response({
            "success": True,
            "explanation": explanation,
        })
    
    async def handle_search(self, request: web.Request) -> web.Response:
        """Search explanations"""
        try:
            # Parse query parameters
            query_params = dict(request.query)
            
            # Build search query
            from ai_explainability.search import SearchQuery, SortField, SortOrder
            
            query = SearchQuery(
                text_query=query_params.get("q", ""),
                action=query_params.get("action"),
                symbol=query_params.get("symbol"),
                min_confidence=float(query_params["min_conf"]) if "min_conf" in query_params else None,
                max_confidence=float(query_params["max_conf"]) if "max_conf" in query_params else None,
                risk_level=query_params.get("risk_level"),
                limit=int(query_params.get("limit", 50)),
                offset=int(query_params.get("offset", 0)),
            )
            
            # Handle sort
            sort_by = query_params.get("sort_by", "timestamp")
            if sort_by == "confidence":
                query.sort_by = SortField.CONFIDENCE
            elif sort_by == "expected_value":
                query.sort_by = SortField.EXPECTED_VALUE
            
            sort_order = query_params.get("sort_order", "desc")
            query.sort_order = SortOrder.DESC if sort_order == "desc" else SortOrder.ASC
            
            # Execute search
            results = self.search.search(query)
            
            # Format results
            formatted_results = self.json_formatter.format_search_results(results)
            
            return web.json_response({
                "success": True,
                **formatted_results,
            })
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return web.json_response({
                "success": False,
                "error": str(e),
            }, status=500)
    
    async def handle_recent(self, request: web.Request) -> web.Response:
        """Get recent explanations"""
        try:
            limit = int(request.query.get("limit", 20))
            action = request.query.get("action")
            symbol = request.query.get("symbol")
            
            explanations = self.storage.get_recent_explanations(
                limit=limit,
                action_filter=action,
                symbol_filter=symbol,
            )
            
            # Format as compact
            formatted = [
                self.json_formatter.format_compact(exp) for exp in explanations
            ]
            
            return web.json_response({
                "success": True,
                "explanations": formatted,
                "count": len(formatted),
            })
            
        except Exception as e:
            logger.error(f"Error getting recent explanations: {e}")
            return web.json_response({
                "success": False,
                "error": str(e),
            }, status=500)
    
    async def handle_audit(self, request: web.Request) -> web.Response:
        """Generate audit report for explanation"""
        explanation_id = request.match_info["id"]
        
        try:
            report = self.audit_viewer.generate_audit_report(explanation_id)
            
            if not report:
                return web.json_response({
                    "success": False,
                    "error": "Explanation not found",
                }, status=404)
            
            # Convert to dict
            report_dict = {
                "report_id": report.report_id,
                "generated_at": report.generated_at.isoformat(),
                "explanation_id": report.explanation_id,
                "decision_id": report.decision_id,
                "integrity_check": report.integrity_check,
                "completeness_score": report.completeness_score,
                "decision_validity": report.decision_validity,
                "confidence_validity": report.confidence_validity,
                "risk_assessment_validity": report.risk_assessment_validity,
                "findings": report.findings,
                "recommendations": report.recommendations,
            }
            
            return web.json_response({
                "success": True,
                "report": report_dict,
            })
            
        except Exception as e:
            logger.error(f"Error generating audit: {e}")
            return web.json_response({
                "success": False,
                "error": str(e),
            }, status=500)
    
    async def handle_reconstruct(self, request: web.Request) -> web.Response:
        """Reconstruct historical decision"""
        explanation_id = request.match_info["id"]
        
        reconstruction = self.audit_viewer.reconstruct_decision(explanation_id)
        
        if not reconstruction:
            return web.json_response({
                "success": False,
                "error": "Explanation not found",
            }, status=404)
        
        # Convert to dict
        recon_dict = {
            "explanation_id": reconstruction.explanation_id,
            "decision_id": reconstruction.decision_id,
            "timestamp": reconstruction.timestamp.isoformat(),
            "original_action": reconstruction.original_action,
            "original_confidence": reconstruction.original_confidence,
            "original_expected_value": reconstruction.original_expected_value,
            "evidence_chain": reconstruction.evidence_chain,
            "analyzer_signals": reconstruction.analyzer_signals,
            "decision_tree": reconstruction.decision_tree,
            "alternatives": reconstruction.alternatives,
            "rejection_reasons": reconstruction.rejection_reasons,
            "feature_importance": reconstruction.feature_importance,
            "historical_analogues": reconstruction.historical_analogues,
            "market_conditions": reconstruction.market_conditions,
            "integrity_verified": reconstruction.integrity_verified,
            "reconstruction_notes": reconstruction.reconstruction_notes,
        }
        
        return web.json_response({
            "success": True,
            "reconstruction": recon_dict,
        })
    
    async def handle_audit_package(self, request: web.Request) -> web.Response:
        """Export complete audit package"""
        explanation_id = request.match_info["id"]
        format_type = request.query.get("format", "json")
        
        package = self.audit_viewer.export_audit_package(explanation_id, format_type)
        
        if not package:
            return web.json_response({
                "success": False,
                "error": "Explanation not found",
            }, status=404)
        
        return web.json_response({
            "success": True,
            "package": package,
        })
    
    async def handle_replay(self, request: web.Request) -> web.Response:
        """Replay explanation at specific level"""
        explanation_id = request.match_info["id"]
        level = request.query.get("level", "advanced")
        
        explanation = self.audit_viewer.replay_explanation(explanation_id, level)
        
        if not explanation:
            return web.json_response({
                "success": False,
                "error": "Explanation not found",
            }, status=404)
        
        return web.json_response({
            "success": True,
            "level": level,
            "explanation": explanation,
        })
    
    async def handle_stats(self, request: web.Request) -> web.Response:
        """Get explanation statistics"""
        stats = self.storage.get_explanation_statistics()
        
        # Add search stats
        confidence_dist = self.search.get_confidence_distribution()
        action_breakdown = self.search.get_action_breakdown()
        
        return web.json_response({
            "success": True,
            "statistics": stats,
            "confidence_distribution": confidence_dist,
            "action_breakdown": action_breakdown,
        })
    
    async def handle_html(self, request: web.Request) -> web.Response:
        """Get explanation as HTML"""
        explanation_id = request.match_info["id"]
        
        explanation = self.storage.get_explanation(explanation_id)
        
        if not explanation:
            return web.Response(text="Explanation not found", status=404)
        
        html = self.html_formatter.format(explanation)
        
        return web.Response(
            text=html,
            content_type="text/html",
        )
    
    async def handle_markdown(self, request: web.Request) -> web.Response:
        """Get explanation as Markdown"""
        explanation_id = request.match_info["id"]
        
        explanation = self.storage.get_explanation(explanation_id)
        
        if not explanation:
            return web.Response(text="Explanation not found", status=404)
        
        md = self.markdown_formatter.format(explanation)
        
        return web.Response(
            text=md,
            content_type="text/markdown",
        )
    
    async def handle_json(self, request: web.Request) -> web.Response:
        """Get explanation as JSON"""
        explanation_id = request.match_info["id"]
        compact = request.query.get("compact", "false") == "true"
        
        explanation = self.storage.get_explanation(explanation_id)
        
        if not explanation:
            return web.json_response({"error": "Explanation not found"}, status=404)
        
        if compact:
            explanation = self.json_formatter.format_compact(explanation)
        
        return web.json_response(explanation)


def setup_explainability_routes(app: web.Application, storage: ExplanationStorage):
    """Setup explainability routes for app"""
    routes = ExplainabilityRoutes(storage)
    routes.setup_routes(app)
    return routes
