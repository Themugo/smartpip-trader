"""
JSON Formatter for AI Explanations

Formats explanations as structured JSON for API responses.
"""

from typing import Any, Dict, List, Optional
import json


class JSONFormatter:
    """Format explanations as JSON"""
    
    def __init__(self, indent: int = 2):
        self.indent = indent
    
    def format(self, explanation: Dict[str, Any], pretty: bool = True) -> str:
        """
        Format explanation as JSON string.
        
        Args:
            explanation: Explanation dictionary
            pretty: Whether to pretty-print
            
        Returns:
            JSON string
        """
        if pretty:
            return json.dumps(explanation, indent=self.indent, default=str)
        return json.dumps(explanation, default=str)
    
    def format_compact(self, explanation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format explanation as compact dictionary (no unnecessary fields).
        
        Args:
            explanation: Explanation dictionary
            
        Returns:
            Compact explanation dictionary
        """
        return {
            "id": explanation.get("explanation_id"),
            "decision_id": explanation.get("decision_id"),
            "timestamp": explanation.get("timestamp"),
            
            # Summary
            "summary": explanation.get("executive_summary", {}).get("summary"),
            "action": explanation.get("executive_summary", {}).get("action"),
            "symbol": explanation.get("executive_summary", {}).get("symbol"),
            "confidence": explanation.get("executive_summary", {}).get("confidence"),
            "risk_level": explanation.get("executive_summary", {}).get("risk_level"),
            "expected_value": explanation.get("executive_summary", {}).get("expected_value"),
            
            # Brief explanations
            "why_opportunity": explanation.get("executive_summary", {}).get("why_opportunity_exists"),
            "why_confidence": explanation.get("executive_summary", {}).get("why_confidence_level"),
            
            # Key evidence
            "key_evidence": explanation.get("executive_summary", {}).get("key_evidence", []),
        }
    
    def format_detailed(self, explanation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format explanation with all details but organized.
        
        Args:
            explanation: Explanation dictionary
            
        Returns:
            Detailed explanation dictionary
        """
        return {
            # Metadata
            "metadata": {
                "explanation_id": explanation.get("explanation_id"),
                "decision_id": explanation.get("decision_id"),
                "timestamp": explanation.get("timestamp"),
                "generation_time_ms": explanation.get("generation_time_ms"),
            },
            
            # Summary
            "summary": explanation.get("executive_summary"),
            
            # Detailed explanations
            "explanations": {
                "beginner": explanation.get("beginner"),
                "advanced": explanation.get("advanced"),
                "developer": explanation.get("developer"),
                "researcher": explanation.get("researcher"),
            },
            
            # Evidence
            "evidence_chain": explanation.get("evidence_chain"),
            
            # Raw data
            "raw_data": explanation.get("raw_data"),
        }
    
    def format_api_response(
        self, 
        explanation: Optional[Dict[str, Any]],
        success: bool = True,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Format as API response.
        
        Args:
            explanation: Explanation dictionary or None
            success: Whether request was successful
            error: Error message if failed
            
        Returns:
            API response dictionary
        """
        return {
            "success": success,
            "error": error,
            "data": explanation,
        }
    
    def format_search_results(
        self, 
        results: List[Any]
    ) -> Dict[str, Any]:
        """
        Format search results.
        
        Args:
            results: List of SearchResult objects
            
        Returns:
            Formatted search results
        """
        formatted = []
        for result in results:
            formatted.append({
                "explanation_id": result.explanation_id,
                "decision_id": result.decision_id,
                "timestamp": result.timestamp,
                "action": result.action,
                "symbol": result.symbol,
                "confidence": result.confidence,
                "risk_level": result.risk_level,
                "expected_value": result.expected_value,
                "relevance_score": result.relevance_score,
                "match_highlights": result.match_highlights,
                "summary": result.summary,
            })
        
        return {
            "results": formatted,
            "count": len(formatted),
        }
