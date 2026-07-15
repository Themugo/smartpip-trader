"""
Markdown Formatter for AI Explanations

Formats explanations as Markdown for documentation and export.
"""

from typing import Any, Dict, List
import json


class MarkdownFormatter:
    """Format explanations as Markdown"""
    
    def format(self, explanation: Dict[str, Any]) -> str:
        """Format explanation as Markdown"""
        exec_summary = explanation.get("executive_summary", {})
        beginner = explanation.get("beginner", {})
        advanced = explanation.get("advanced", {})
        developer = explanation.get("developer", {})
        researcher = explanation.get("researcher", {})
        
        md = []
        
        # Header
        md.append("# AI Decision Explanation\n")
        md.append(f"**Explanation ID:** `{explanation.get('explanation_id', 'N/A')}`  ")
        md.append(f"**Decision ID:** `{explanation.get('decision_id', 'N/A')}`  ")
        md.append(f"**Timestamp:** {explanation.get('timestamp', 'N/A')}\n")
        
        # Executive Summary
        md.append("## Executive Summary\n")
        md.append(f"- **Action:** {exec_summary.get('action', 'N/A')}")
        md.append(f"- **Symbol:** {exec_summary.get('symbol', 'N/A')}")
        md.append(f"- **Confidence:** {exec_summary.get('confidence', 0):.1f}%")
        md.append(f"- **Risk Level:** {exec_summary.get('risk_level', 'N/A')}")
        md.append(f"- **Expected Value:** {exec_summary.get('expected_value', 0):.4f}")
        md.append(f"- **Summary:** {exec_summary.get('summary', 'N/A')}\n")
        
        md.append(f"**Why Opportunity Exists:** {exec_summary.get('why_opportunity_exists', 'N/A')}\n")
        md.append(f"**Why Confidence Level:** {exec_summary.get('why_confidence_level', 'N/A')}\n")
        
        # Beginner Explanation
        if beginner:
            md.append("---\n## Beginner Level\n")
            md.append(f"### What Happened\n{beginner.get('what_happened', 'N/A')}\n")
            md.append(f"### Why\n{beginner.get('why', 'N/A')}\n")
            md.append(f"### How Confident\n{beginner.get('how_confident', 'N/A')}\n")
            md.append(f"### How Risky\n{beginner.get('how_risky', 'N/A')}\n")
            md.append(f"### What to Expect\n{beginner.get('what_to_expect', 'N/A')}\n")
            md.append(f"### Recommendation\n{beginner.get('recommendation', 'N/A')}\n")
            
            if beginner.get('key_points'):
                md.append("### Key Points\n")
                for point in beginner.get('key_points', []):
                    md.append(f"- {point}")
                md.append("")
        
        # Advanced Explanation
        if advanced:
            md.append("---\n## Advanced Level\n")
            
            md.append("### Market Context\n")
            ctx = advanced.get('market_context', {})
            md.append(f"- Regime: `{ctx.get('regime', 'N/A')}`")
            md.append(f"- Volatility: `{ctx.get('volatility', 0):.4f}`")
            md.append(f"- Balance: `${ctx.get('balance', 0):.2f}`")
            md.append(f"- Equity: `${ctx.get('equity', 0):.2f}`")
            md.append(f"- Exposure: `{ctx.get('exposure', 0):.1f}%`\n")
            
            md.append("### Signal Breakdown\n")
            for signal in advanced.get('signal_breakdown', [])[:5]:
                md.append(f"- **{signal.get('analyzer', 'Unknown')}**: {signal.get('signal', 'N/A')} "
                         f"({signal.get('confidence', 0):.0f}% confidence, weight: {signal.get('weight', 0):.2f})")
            md.append("")
            
            md.append("### Risk Metrics\n")
            risk = advanced.get('risk_metrics', {})
            md.append(f"- Risk Score: `{risk.get('risk_score', 0):.2f}`")
            md.append(f"- Risk Level: `{risk.get('risk_level', 'N/A')}`")
            md.append(f"- Uncertainty: `{risk.get('uncertainty', 0):.2f}`")
            md.append(f"- Calibration Confidence: `{risk.get('calibration_confidence', 0):.0f}%`\n")
            
            md.append("### Trade Management\n")
            mgmt = advanced.get('trade_management', {})
            md.append(f"- Entry Strategy: {mgmt.get('entry_strategy', {}).get('type', 'N/A')}")
            md.append(f"- Exit Strategy: {mgmt.get('exit_strategy', {}).get('time_based', 'N/A')}")
            md.append("")
        
        # Developer Explanation
        if developer:
            md.append("---\n## Developer Level\n")
            
            md.append("### System Information\n")
            sys_info = developer.get('system_info', {})
            md.append(f"- Module: `{sys_info.get('module', 'N/A')}`")
            md.append(f"- Component: `{sys_info.get('component', 'N/A')}`")
            md.append(f"- API Version: `{sys_info.get('api_version', 'N/A')}`\n")
            
            md.append("### Analyzers Used\n")
            for analyzer in developer.get('analyzers_used', []):
                md.append(f"- `{analyzer}`")
            md.append("")
            
            md.append("### Feature Importance (Top 10)\n")
            for feature, importance in developer.get('top_features', [])[:10]:
                md.append(f"- `{feature}`: {importance:.4f}")
            md.append("")
            
            md.append("### Decision Tree\n")
            for step in developer.get('decision_tree', []):
                md.append(f"{step}")
            md.append("")
            
            md.append("### Calibration\n")
            calib = developer.get('calibration', {})
            md.append(f"- Confidence: `{calib.get('confidence', 0):.0f}%`")
            md.append(f"- Historical Accuracy: `{calib.get('historical_accuracy', 0):.0f}%`\n")
        
        # Researcher Explanation
        if researcher:
            md.append("---\n## Researcher Level\n")
            
            md.append("### Methodology\n")
            method = researcher.get('methodology', {})
            md.append(f"- Approach: `{method.get('approach', 'N/A')}`\n")
            
            md.append("### Statistics\n")
            stats = researcher.get('statistics', {})
            conf_stats = stats.get('confidence', {})
            md.append(f"- Confidence: `{conf_stats.get('value', 0):.2f}`")
            md.append(f"- Calibration Confidence: `{conf_stats.get('calibration_confidence', 0):.2f}`")
            md.append(f"- Uncertainty Estimate: `{conf_stats.get('uncertainty_estimate', 0):.4f}`")
            md.append(f"- Standard Error: `{conf_stats.get('standard_error', 0):.4f}`\n")
            
            md.append("### Probability Analysis\n")
            prob = researcher.get('probability_analysis', {})
            md.append(f"- Expected Value: `{prob.get('expected_value', 0):.4f}`")
            md.append(f"- Variance: `{prob.get('variance', 0):.6f}`")
            md.append(f"- Sharpe Ratio: `{prob.get('sharpe_ratio', 0):.4f}`\n")
            
            md.append("### Probability Distribution\n")
            for outcome, prob_val in prob.get('distribution', {}).items():
                md.append(f"- {outcome}: `{prob_val:.4f}`")
            md.append("")
            
            md.append("### Evidence Weights\n")
            for etype, weight in researcher.get('evidence_weights', {}).items():
                md.append(f"- {etype}: `{weight:.2f}`")
            md.append("")
            
            if researcher.get('historical_analogues'):
                md.append("### Historical Analogues\n")
                analogues = researcher.get('historical_analogues')
                md.append(f"- Count: `{analogue.get('count', 0)}` similar decisions")
                avg = analogues.get('avg_outcome')
                if avg:
                    md.append(f"- Average Outcome: `{avg:.4f}`")
                md.append("")
        
        # Evidence Chain
        if explanation.get('evidence_chain'):
            md.append("---\n## Evidence Chain\n")
            for i, evidence in enumerate(explanation.get('evidence_chain', []), 1):
                md.append(f"### {i}. {evidence.get('type', 'Unknown').replace('_', ' ').title()}")
                md.append(f"- Timestamp: `{evidence.get('timestamp', 'N/A')}`")
                md.append(f"- Weight: `{evidence.get('weight', 0):.2f}`")
                md.append(f"- Data: `{json.dumps(evidence.get('data', {}))}`")
                md.append("")
        
        return "\n".join(md)
    
    def format_comparison(
        self, 
        explanations: List[Dict[str, Any]]
    ) -> str:
        """Format comparison of multiple explanations"""
        md = ["# AI Decision Comparison\n"]
        
        # Table header
        md.append("| Decision ID | Action | Confidence | Risk | Expected Value | Timestamp |")
        md.append("|-------------|--------|------------|------|----------------|-----------|")
        
        # Table rows
        for exp in explanations:
            exec_sum = exp.get('executive_summary', {})
            md.append(
                f"| `{exp.get('decision_id', 'N/A')[:8]}...` "
                f"| {exec_sum.get('action', 'N/A')} "
                f"| {exec_sum.get('confidence', 0):.1f}% "
                f"| {exec_sum.get('risk_level', 'N/A')} "
                f"| {exec_sum.get('expected_value', 0):.4f} "
                f"| {exp.get('timestamp', 'N/A')[:19]} |"
            )
        
        md.append("")
        return "\n".join(md)
