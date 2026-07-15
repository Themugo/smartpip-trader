"""
HTML Formatter for AI Explanations

Formats explanations as interactive HTML for web display.
"""

from typing import Any, Dict, List, Optional
import json


class HTMLFormatter:
    """Format explanations as HTML"""
    
    def __init__(self):
        self.template = """
        <div class="ai-explanation" data-explanation-id="{explanation_id}">
            <div class="explanation-header">
                <h2>AI Decision Explanation</h2>
                <span class="timestamp">{timestamp}</span>
            </div>
            
            <div class="explanation-summary">
                <div class="summary-badge {risk_level}">{risk_level} RISK</div>
                <p class="summary-text">{summary}</p>
            </div>
            
            <div class="confidence-meter">
                <label>Confidence</label>
                <div class="meter-bar">
                    <div class="meter-fill" style="width: {confidence}%"></div>
                </div>
                <span class="meter-value">{confidence}%</span>
            </div>
            
            <div class="tabs">
                <button class="tab-btn active" data-tab="beginner">Beginner</button>
                <button class="tab-btn" data-tab="advanced">Advanced</button>
                <button class="tab-btn" data-tab="developer">Developer</button>
                <button class="tab-btn" data-tab="researcher">Researcher</button>
            </div>
            
            <div class="tab-content active" id="tab-beginner">
                {beginner_content}
            </div>
            
            <div class="tab-content" id="tab-advanced">
                {advanced_content}
            </div>
            
            <div class="tab-content" id="tab-developer">
                {developer_content}
            </div>
            
            <div class="tab-content" id="tab-researcher">
                {researcher_content}
            </div>
            
            <div class="evidence-section">
                <h3>Evidence Chain</h3>
                <div class="evidence-timeline">
                    {evidence_timeline}
                </div>
            </div>
        </div>
        
        <style>
            .ai-explanation {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: #fff;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .explanation-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 1px solid #eee;
            }}
            .explanation-header h2 {{
                margin: 0;
                font-size: 1.5em;
                color: #333;
            }}
            .timestamp {{
                color: #666;
                font-size: 0.9em;
            }}
            .explanation-summary {{
                background: #f8f9fa;
                padding: 15px;
                border-radius: 6px;
                margin-bottom: 20px;
            }}
            .summary-badge {{
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.8em;
                font-weight: 600;
                margin-bottom: 10px;
            }}
            .summary-badge.LOW {{ background: #d4edda; color: #155724; }}
            .summary-badge.MEDIUM {{ background: #fff3cd; color: #856404; }}
            .summary-badge.HIGH {{ background: #f8d7da; color: #721c24; }}
            .summary-badge.CRITICAL {{ background: #721c24; color: #fff; }}
            .summary-text {{
                margin: 0;
                font-size: 1.1em;
                color: #333;
            }}
            .confidence-meter {{
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 20px;
            }}
            .confidence-meter label {{
                font-weight: 600;
                min-width: 80px;
            }}
            .meter-bar {{
                flex: 1;
                height: 20px;
                background: #e9ecef;
                border-radius: 10px;
                overflow: hidden;
            }}
            .meter-fill {{
                height: 100%;
                background: linear-gradient(90deg, #28a745, #17a2b8);
                transition: width 0.3s ease;
            }}
            .meter-value {{
                font-weight: 600;
                min-width: 50px;
                text-align: right;
            }}
            .tabs {{
                display: flex;
                gap: 5px;
                margin-bottom: 15px;
                border-bottom: 2px solid #eee;
            }}
            .tab-btn {{
                padding: 10px 20px;
                border: none;
                background: none;
                cursor: pointer;
                font-size: 1em;
                color: #666;
                border-bottom: 2px solid transparent;
                margin-bottom: -2px;
            }}
            .tab-btn.active {{
                color: #007bff;
                border-bottom-color: #007bff;
            }}
            .tab-content {{
                display: none;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 6px;
            }}
            .tab-content.active {{
                display: block;
            }}
            .evidence-section {{
                margin-top: 20px;
            }}
            .evidence-section h3 {{
                margin-top: 0;
            }}
            .evidence-timeline {{
                position: relative;
                padding-left: 20px;
            }}
            .evidence-item {{
                position: relative;
                padding: 10px 0 10px 30px;
                border-left: 2px solid #dee2e6;
            }}
            .evidence-item:last-child {{
                border-left-color: transparent;
            }}
            .evidence-item::before {{
                content: '';
                position: absolute;
                left: -6px;
                top: 15px;
                width: 10px;
                height: 10px;
                border-radius: 50%;
                background: #007bff;
            }}
        </style>
        
        <script>
            document.querySelectorAll('.tab-btn').forEach(btn => {{
                btn.addEventListener('click', () => {{
                    const tab = btn.dataset.tab;
                    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                    btn.classList.add('active');
                    document.getElementById('tab-' + tab).classList.add('active');
                }});
            }});
        </script>
        """
    
    def format(self, explanation: Dict[str, Any]) -> str:
        """Format explanation as HTML"""
        exec_summary = explanation.get("executive_summary", {})
        
        return self.template.format(
            explanation_id=explanation.get("explanation_id", ""),
            timestamp=explanation.get("timestamp", ""),
            risk_level=exec_summary.get("risk_level", "MEDIUM"),
            summary=exec_summary.get("summary", ""),
            confidence=exec_summary.get("confidence", 0),
            beginner_content=self._format_beginner(explanation.get("beginner", {})),
            advanced_content=self._format_advanced(explanation.get("advanced", {})),
            developer_content=self._format_developer(explanation.get("developer", {})),
            researcher_content=self._format_researcher(explanation.get("researcher", {})),
            evidence_timeline=self._format_evidence_timeline(explanation.get("evidence_chain", [])),
        )
    
    def _format_beginner(self, beginner: Dict) -> str:
        """Format beginner explanation"""
        if not beginner:
            return "<p>No beginner explanation available.</p>"
        
        return f"""
        <div class="beginner-content">
            <p><strong>What happened:</strong> {beginner.get('what_happened', 'N/A')}</p>
            <p><strong>Why:</strong> {beginner.get('why', 'N/A')}</p>
            <p><strong>Confidence:</strong> {beginner.get('how_confident', 'N/A')}</p>
            <p><strong>Risk:</strong> {beginner.get('how_risky', 'N/A')}</p>
            <p><strong>Recommendation:</strong> {beginner.get('recommendation', 'N/A')}</p>
        </div>
        """
    
    def _format_advanced(self, advanced: Dict) -> str:
        """Format advanced explanation"""
        if not advanced:
            return "<p>No advanced explanation available.</p>"
        
        signals = advanced.get("signal_breakdown", [])
        signals_html = ""
        for signal in signals[:5]:
            signals_html += f"""
            <div class="signal-item">
                <span class="signal-name">{signal.get('analyzer', '')}</span>
                <span class="signal-value">{signal.get('signal', '')} ({signal.get('confidence', 0):.0f}%)</span>
            </div>
            """
        
        return f"""
        <div class="advanced-content">
            <h4>Market Context</h4>
            <p><strong>Regime:</strong> {advanced.get('market_context', {}).get('regime', 'N/A')}</p>
            <p><strong>Volatility:</strong> {advanced.get('market_context', {}).get('volatility', 0):.4f}</p>
            
            <h4>Signal Breakdown</h4>
            {signals_html or '<p>No signals available.</p>'}
            
            <h4>Risk Metrics</h4>
            <p><strong>Risk Score:</strong> {advanced.get('risk_metrics', {}).get('risk_score', 0):.2f}</p>
            <p><strong>Risk Level:</strong> {advanced.get('risk_metrics', {}).get('risk_level', 'N/A')}</p>
        </div>
        """
    
    def _format_developer(self, developer: Dict) -> str:
        """Format developer explanation"""
        if not developer:
            return "<p>No developer explanation available.</p>"
        
        features = developer.get("top_features", [])
        features_html = ""
        for feature, importance in features[:5]:
            features_html += f"<li><code>{feature}</code>: {importance:.4f}</li>"
        
        return f"""
        <div class="developer-content">
            <h4>System Information</h4>
            <p><strong>Module:</strong> {developer.get('system_info', {}).get('module', 'N/A')}</p>
            <p><strong>Component:</strong> {developer.get('system_info', {}).get('component', 'N/A')}</p>
            
            <h4>Analyzers Used</h4>
            <ul>
                {''.join(f'<li>{a}</li>' for a in developer.get('analyzers_used', []))}
            </ul>
            
            <h4>Top Features</h4>
            <ul>{features_html or '<li>No features available.</li>'}</ul>
            
            <h4>Implementation</h4>
            <pre><code>{json.dumps(developer.get('implementation', {}), indent=2)}</code></pre>
        </div>
        """
    
    def _format_researcher(self, researcher: Dict) -> str:
        """Format researcher explanation"""
        if not researcher:
            return "<p>No researcher explanation available.</p>"
        
        stats = researcher.get("statistics", {})
        prob = researcher.get("probability_analysis", {})
        
        return f"""
        <div class="researcher-content">
            <h4>Methodology</h4>
            <p><strong>Approach:</strong> {researcher.get('methodology', {}).get('approach', 'N/A')}</p>
            
            <h4>Statistical Analysis</h4>
            <p><strong>Confidence:</strong> {stats.get('confidence', {}).get('value', 0):.2f}</p>
            <p><strong>Calibration Confidence:</strong> {stats.get('confidence', {}).get('calibration_confidence', 0):.2f}</p>
            <p><strong>Uncertainty Estimate:</strong> {stats.get('confidence', {}).get('uncertainty_estimate', 0):.4f}</p>
            
            <h4>Probability Analysis</h4>
            <p><strong>Expected Value:</strong> {prob.get('expected_value', 0):.4f}</p>
            <p><strong>Variance:</strong> {prob.get('variance', 0):.6f}</p>
            <p><strong>Sharpe Ratio:</strong> {prob.get('sharpe_ratio', 0):.4f}</p>
            
            <h4>Evidence Weights</h4>
            <pre><code>{json.dumps(researcher.get('evidence_weights', {}), indent=2)}</code></pre>
        </div>
        """
    
    def _format_evidence_timeline(self, evidence: List[Dict]) -> str:
        """Format evidence chain as timeline"""
        if not evidence:
            return "<p>No evidence available.</p>"
        
        items = []
        for e in evidence:
            items.append(f"""
            <div class="evidence-item">
                <strong>{e.get('type', 'Unknown').replace('_', ' ').title()}</strong>
                <p>{str(e.get('data', {}))[:100]}...</p>
                <small>Weight: {e.get('weight', 0):.2f}</small>
            </div>
            """)
        
        return "\n".join(items)
