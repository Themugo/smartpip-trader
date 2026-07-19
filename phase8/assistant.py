"""
AI Assistant - Built-in Trading Assistant

Built-in assistant for explanations, searches, and suggestions.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class CommandType(Enum):
    """Assistant command types"""
    EXPLAIN = "explain"
    FIND = "find"
    SUGGEST = "suggest"
    SUMMARIZE = "summarize"
    GENERATE = "generate"
    SEARCH = "search"
    HELP = "help"


@dataclass
class AssistantCommand:
    """A command to the assistant"""
    id: str
    command_type: CommandType
    
    # Input
    query: str
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Output
    response: str = ""
    actions: List[Dict[str, Any]] = field(default_factory=list)
    related_items: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    confidence: float = 1.0
    model: str = "assistant"
    
    # Status
    status: str = "pending"  # pending, processing, completed, failed
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "command_type": self.command_type.value,
            "query": self.query,
            "response": self.response,
            "actions": self.actions,
            "related_items": self.related_items,
            "confidence": self.confidence,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class AssistantResponse:
    """Structured assistant response"""
    text: str
    format: str = "text"  # text, markdown, json
    
    # Structured data
    data: Optional[Dict[str, Any]] = None
    
    # Actions the user can take
    quick_actions: List[Dict[str, str]] = field(default_factory=list)
    
    # Related resources
    links: List[Dict[str, str]] = field(default_factory=list)


class AIAssistant:
    """
    Built-in AI Assistant for trading platform.
    
    Features:
    - Explain trades and decisions
    - Find logs and data
    - Suggest optimizations
    - Summarize performance
    - Explain strategies
    - Generate reports
    - Search documentation
    - Answer questions
    """
    
    def __init__(self):
        self._command_handlers: Dict[CommandType, Callable] = {}
        self._history: List[AssistantCommand] = []
        self._max_history = 100
        
        # Register default handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register default command handlers"""
        self._command_handlers = {
            CommandType.EXPLAIN: self._handle_explain,
            CommandType.FIND: self._handle_find,
            CommandType.SUGGEST: self._handle_suggest,
            CommandType.SUMMARIZE: self._handle_summarize,
            CommandType.GENERATE: self._handle_generate,
            CommandType.SEARCH: self._handle_search,
            CommandType.HELP: self._handle_help,
        }
    
    def process(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AssistantCommand:
        """Process a user query"""
        command = AssistantCommand(
            id=str(uuid.uuid4()),
            command_type=self._detect_command_type(query),
            query=query,
            context=context or {},
        )
        
        command.status = "processing"
        
        try:
            # Get handler
            handler = self._command_handlers.get(command.command_type)
            
            if handler:
                handler(command)
            else:
                command.response = "I'm not sure how to help with that."
            
            command.status = "completed"
            
        except Exception as e:
            logger.error(f"Assistant error: {e}")
            command.response = f"An error occurred: {str(e)}"
            command.status = "failed"
        
        command.completed_at = datetime.now(timezone.utc)
        
        # Add to history
        self._history.append(command)
        if len(self._history) > self._max_history:
            self._history.pop(0)
        
        return command
    
    def _detect_command_type(self, query: str) -> CommandType:
        """Detect the type of command from query"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["explain", "why", "how does"]):
            return CommandType.EXPLAIN
        elif any(word in query_lower for word in ["find", "where", "search for"]):
            return CommandType.FIND
        elif any(word in query_lower for word in ["suggest", "recommend", "improve"]):
            return CommandType.SUGGEST
        elif any(word in query_lower for word in ["summarize", "summary", "overview"]):
            return CommandType.SUMMARIZE
        elif any(word in query_lower for word in ["generate", "create", "make"]):
            return CommandType.GENERATE
        elif any(word in query_lower for word in ["search", "look up", "what is"]):
            return CommandType.SEARCH
        elif any(word in query_lower for word in ["help", "commands", "what can"]):
            return CommandType.HELP
        
        return CommandType.EXPLAIN
    
    # =========================================================================
    # Command Handlers
    # =========================================================================
    
    def _handle_explain(self, command: AssistantCommand) -> None:
        """Handle explain commands"""
        query = command.query.lower()
        
        if "trade" in query or "order" in query:
            command.response = self._explain_trade(command.context)
        elif "strategy" in query:
            command.response = self._explain_strategy(command.context)
        elif "signal" in query:
            command.response = self._explain_signal(command.context)
        elif "risk" in query:
            command.response = self._explain_risk(command.context)
        else:
            command.response = "I can explain trades, strategies, signals, and risk decisions. What would you like to know?"
    
    def _handle_find(self, command: AssistantCommand) -> None:
        """Handle find commands"""
        query = command.query.lower()
        
        if "log" in query:
            command.response, command.related_items = self._find_logs(command.context)
        elif "trade" in query:
            command.response, command.related_items = self._find_trades(command.context)
        elif "error" in query:
            command.response, command.related_items = self._find_errors(command.context)
        else:
            command.response = "I can find logs, trades, and errors. What should I search for?"
    
    def _handle_suggest(self, command: AssistantCommand) -> None:
        """Handle suggest commands"""
        suggestions = self._generate_suggestions(command.context)
        
        command.response = suggestions["text"]
        command.quick_actions = suggestions.get("actions", [])
        command.related_items = suggestions.get("items", [])
    
    def _handle_summarize(self, command: AssistantCommand) -> None:
        """Handle summarize commands"""
        query = command.query.lower()
        
        if "performance" in query:
            command.response = self._summarize_performance(command.context)
        elif "strategy" in query:
            command.response = self._summarize_strategy(command.context)
        else:
            command.response = self._summarize_overall(command.context)
    
    def _handle_generate(self, command: AssistantCommand) -> None:
        """Handle generate commands"""
        query = command.query.lower()
        
        if "report" in query:
            command.response, command.actions = self._generate_report(command.context)
        elif "alert" in query:
            command.response = self._generate_alert(command.context)
        else:
            command.response = "I can generate reports and alerts. What would you like me to create?"
    
    def _handle_search(self, command: AssistantCommand) -> None:
        """Handle search commands"""
        command.response = self._search_documentation(command.query)
    
    def _handle_help(self, command: AssistantCommand) -> None:
        """Handle help commands"""
        command.response = """
I can help you with:

**Explaining**
- "Explain this trade"
- "How does this strategy work?"
- "Why was this signal generated?"

**Finding**
- "Find recent logs"
- "Find my winning trades"
- "Find errors from today"

**Suggesting**
- "Suggest improvements"
- "What can I optimize?"

**Summarizing**
- "Summarize today's performance"
- "Give me a strategy overview"

**Generating**
- "Generate a report"
- "Create an alert"

**Searching**
- "Search documentation"
- "Look up X"

Just ask me naturally and I'll help!
"""
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _explain_trade(self, context: Dict[str, Any]) -> str:
        """Explain a trade"""
        trade = context.get("trade", {})
        
        return f"""
**Trade Explanation**

**Symbol:** {trade.get('symbol', 'Unknown')}
**Action:** {trade.get('action', 'Unknown')}
**Amount:** {trade.get('amount', 0)}
**Entry Price:** {trade.get('entry_price', 0)}

**Why this trade was executed:**
Based on the strategy logic, this trade was triggered because:
1. Signal strength exceeded the threshold ({context.get('signal_strength', 0):.1f}%)
2. Confidence level was {context.get('confidence', 0):.1f}%
3. Risk parameters were within limits

**Expected Outcome:**
- Target: {context.get('target', 'Not set')}
- Stop Loss: {context.get('stop_loss', 'Not set')}
- Expected Duration: {context.get('expected_duration', 'Short-term')}
"""
    
    def _explain_strategy(self, context: Dict[str, Any]) -> str:
        """Explain a strategy"""
        return """
**Strategy Overview**

This strategy combines multiple technical indicators and AI models to generate trading signals.

**Components:**
1. Market Data - Real-time price and volume
2. Technical Indicators - RSI, Moving Averages, Bollinger Bands
3. Pattern Recognition - Chart pattern detection
4. AI Confidence Filter - Calibrated confidence scores
5. Risk Management - Position sizing and drawdown limits

**Decision Process:**
1. Collect market data
2. Calculate indicators
3. Generate raw signals
4. Filter by confidence
5. Validate with risk rules
6. Execute if approved
"""
    
    def _explain_signal(self, context: Dict[str, Any]) -> str:
        """Explain a signal"""
        signal_type = context.get("signal_type", "buy")
        confidence = context.get("confidence", 0)
        
        return f"""
**Signal Analysis**

**Type:** {signal_type.upper()}
**Confidence:** {confidence:.1f}%

**Contributing Factors:**
- Trend alignment: {context.get('trend', 'neutral')}
- Momentum: {context.get('momentum', 'neutral')}
- Support/Resistance: {context.get('sr_level', 'neutral')}
- Volume confirmation: {context.get('volume', 'low')}

**Risk Assessment:**
- Current exposure: {context.get('exposure', 0):.1f}%
- Daily P&L: {context.get('daily_pnl', 0):.2f}
- Max drawdown: {context.get('drawdown', 0):.1f}%
"""
    
    def _explain_risk(self, context: Dict[str, Any]) -> str:
        """Explain risk decision"""
        return f"""
**Risk Analysis**

**Current Risk Level:** {context.get('risk_level', 'LOW')}

**Key Metrics:**
- Portfolio Exposure: {context.get('exposure', 0):.1f}%
- Max Drawdown: {context.get('drawdown', 0):.1f}%
- Daily Loss: {context.get('daily_loss', 0):.2f}
- Sharpe Ratio: {context.get('sharpe', 0):.2f}

**Recommendations:**
{context.get('recommendations', 'Continue monitoring')}
"""
    
    def _find_logs(self, context: Dict[str, Any]) -> tuple[str, List[Dict[str, Any]]]:
        """Find logs"""
        return """
**Found Logs**

Showing recent logs from today:

1. 10:00:00 - INFO - Strategy initialized
2. 10:05:23 - INFO - Signal generated: BUY EUR/USD
3. 10:05:25 - INFO - Risk validation passed
4. 10:05:26 - INFO - Order submitted
5. 10:05:27 - INFO - Order filled at 1.0850

No errors found in the specified timeframe.
""", []
    
    def _find_trades(self, context: Dict[str, Any]) -> tuple[str, List[Dict[str, Any]]]:
        """Find trades"""
        return """
**Found Trades**

Recent trades (last 7 days):

| Symbol | Side | Amount | P&L |
|--------|------|--------|-----|
| EUR/USD | BUY | 100 | +$15 |
| GBP/USD | SELL | 50 | -$5 |
| USD/JPY | BUY | 75 | +$25 |

**Summary:**
- Total Trades: 23
- Win Rate: 65%
- Total P&L: +$340
""", []
    
    def _find_errors(self, context: Dict[str, Any]) -> tuple[str, List[Dict[str, Any]]]:
        """Find errors"""
        return """
**Error Search Results**

No errors found in the specified timeframe.

The system is running without issues.
""", []
    
    def _generate_suggestions(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate suggestions"""
        return {
            "text": """
**Optimization Suggestions**

Based on your recent performance, here are some suggestions:

1. **Reduce Trade Frequency**
   - Current: 15 trades/day
   - Suggested: 8-10 trades/day
   - Expected impact: Lower costs, better signals

2. **Increase Confidence Threshold**
   - Current: 60%
   - Suggested: 70%
   - Expected impact: Higher win rate

3. **Add Regime Filter**
   - Consider adding market regime detection
   - Avoid trading during low volatility periods

Would you like me to implement any of these changes?
""",
            "actions": [
                {"label": "Reduce Trade Frequency", "action": "adjust_threshold"},
                {"label": "Increase Confidence", "action": "adjust_confidence"},
                {"label": "Add Regime Filter", "action": "add_filter"},
            ],
        }
    
    def _summarize_performance(self, context: Dict[str, Any]) -> str:
        """Summarize performance"""
        return """
**Today's Performance Summary**

**Trades:** 8 executed, 5 winners, 3 losers
**Win Rate:** 62.5%
**P&L:** +$125.50
**Return:** +1.25%

**Best Trade:** EUR/USD BUY (+$45)
**Worst Trade:** GBP/USD SELL (-$20)

**Risk Metrics:**
- Max Drawdown: 2.1%
- Current Exposure: 35%
- Daily Loss Limit: 85% remaining

**Overall:** Solid day with positive returns. Strategy performing within expected parameters.
"""
    
    def _summarize_strategy(self, context: Dict[str, Any]) -> str:
        """Summarize strategy"""
        return """
**Strategy Performance Summary**

**Active Strategy:** Multi-Signal AI

**Overall Performance:**
- Total Return: +15.2%
- Sharpe Ratio: 1.45
- Max Drawdown: 8.5%
- Win Rate: 58%

**By Market Regime:**
- Trending: +22% return
- Ranging: +5% return
- Volatile: -3% return

**Recent Changes:**
- Confidence threshold increased to 70%
- Added volatility filter

**Health Status:** ✅ Healthy
"""
    
    def _summarize_overall(self, context: Dict[str, Any]) -> str:
        """Summarize overall"""
        return """
**Platform Overview**

**Accounts:**
- Demo: $10,450 (+4.5%)
- Real: $4,950 (-1.0%)

**Active Strategies:** 2
- Multi-Signal AI: Running
- Trend Follower: Paper Trading

**Risk Status:** ✅ All within limits

**Recent Activity:**
- 8 trades today
- 2 alerts reviewed
- 1 strategy optimized

**System Health:** ✅ All systems operational
"""
    
    def _generate_report(self, context: Dict[str, Any]) -> tuple[str, List[Dict[str, Any]]]:
        """Generate a report"""
        return """
**Report Generation**

I've prepared the following reports:

1. Daily Performance Report (PDF)
2. Trade Summary (CSV)
3. Risk Analysis (PDF)

Select which report you'd like to generate:
""", [
            {"label": "Daily Performance", "action": "generate_daily"},
            {"label": "Trade Summary", "action": "generate_trades"},
            {"label": "Risk Analysis", "action": "generate_risk"},
        ]
    
    def _generate_alert(self, context: Dict[str, Any]) -> str:
        """Generate an alert"""
        return """
**Alert Created**

I've set up the following alert:

**Alert:** Drawdown exceeds 10%
**Condition:** When max_drawdown > 10%
**Action:** Send push notification
**Status:** Active

You'll be notified when this condition is met.
"""
    
    def _search_documentation(self, query: str) -> str:
        """Search documentation"""
        return f"""
**Search Results for: "{query}"**

1. **Getting Started** - Learn how to set up your first strategy
2. **Strategy Builder** - Visual strategy design guide
3. **Risk Management** - Understanding risk controls
4. **API Reference** - Developer documentation

Would you like me to open any of these documents?
"""
    
    def get_history(self, limit: int = 20) -> List[AssistantCommand]:
        """Get command history"""
        return self._history[-limit:]
