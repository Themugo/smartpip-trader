"""
Event Selector
=============

Filter and select specific events for replay.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

logger = logging.getLogger(__name__)


class SelectionMode(Enum):
    """Event selection mode"""
    ALL = "all"
    SPECIFIC = "specific"
    BY_TYPE = "by_type"
    BY_CHANNEL = "by_channel"
    BY_TRADE = "by_trade"
    CUSTOM = "custom"


@dataclass
class EventFilter:
    """Filter criteria for events"""
    # By type
    event_types: Set[str] = field(default_factory=set)
    
    # By trade ID
    trade_ids: Set[str] = field(default_factory=set)
    
    # By timestamp range
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # By sequence range
    start_sequence: Optional[int] = None
    end_sequence: Optional[int] = None
    
    # By custom predicate
    custom_filter: Optional[Callable] = None
    
    # Polarity
    exclude: bool = False  # If True, excludes matching events
    
    def matches(self, event) -> bool:
        """Check if event matches filter"""
        # Check event type
        if self.event_types:
            if event.event_type.value not in self.event_types:
                return False
        
        # Check trade ID
        if self.trade_ids:
            trade_id = event.data.get("trade_id") or event.data.get("order_id")
            if trade_id not in self.trade_ids:
                return False
        
        # Check timestamp range
        if self.start_time and event.timestamp < self.start_time:
            return False
        if self.end_time and event.timestamp > self.end_time:
            return False
        
        # Check sequence range
        if self.start_sequence and event.sequence < self.start_sequence:
            return False
        if self.end_sequence and event.sequence > self.end_sequence:
            return False
        
        # Check custom filter
        if self.custom_filter:
            if not self.custom_filter(event):
                return False
        
        return True


class EventSelector:
    """
    Selects specific events for replay.
    
    Supports:
    - Replay specific trade IDs
    - Replay strategy decisions only
    - Replay AI reasoning only
    - Replay execution events only
    """
    
    def __init__(self):
        self.selection_mode = SelectionMode.ALL
        self.filter = EventFilter()
        self._selected_events: List[Any] = []
    
    def select_all(self) -> "EventSelector":
        """Select all events"""
        self.selection_mode = SelectionMode.ALL
        self.filter = EventFilter()
        logger.info("Selection mode: ALL")
        return self
    
    def select_by_types(self, event_types: List[str]) -> "EventSelector":
        """Select events by type"""
        self.selection_mode = SelectionMode.BY_TYPE
        self.filter.event_types = set(event_types)
        logger.info(f"Selection mode: BY_TYPE - {event_types}")
        return self
    
    def select_trades_only(self, trade_ids: List[str] = None) -> "EventSelector":
        """
        Select only trade-related events.
        
        Args:
            trade_ids: Optional specific trade IDs to select
        """
        self.selection_mode = SelectionMode.BY_TRADE
        
        if trade_ids:
            self.filter.trade_ids = set(trade_ids)
        
        # Include trade-related event types
        trade_types = {
            "trade_entry", "trade_exit", "order_placed",
            "order_filled", "order_cancelled"
        }
        self.filter.event_types = trade_types
        
        logger.info(f"Selection mode: TRADES_ONLY - {trade_ids or 'all trades'}")
        return self
    
    def select_strategy_decisions_only(self) -> "EventSelector":
        """Select only strategy decision events"""
        self.selection_mode = SelectionMode.SPECIFIC
        
        strategy_types = {
            "strategy_decision", "signal_generated", "parameter_update"
        }
        self.filter.event_types = strategy_types
        
        logger.info("Selection mode: STRATEGY_DECISIONS_ONLY")
        return self
    
    def select_ai_reasoning_only(self) -> "EventSelector":
        """Select only AI reasoning events"""
        self.selection_mode = SelectionMode.SPECIFIC
        
        ai_types = {
            "ai_confidence", "ai_reasoning", "ai_recommendation"
        }
        self.filter.event_types = ai_types
        
        logger.info("Selection mode: AI_REASONING_ONLY")
        return self
    
    def select_execution_only(self) -> "EventSelector":
        """Select only execution events"""
        self.selection_mode = SelectionMode.SPECIFIC
        
        execution_types = {
            "trade_entry", "trade_exit", "order_placed",
            "order_filled", "order_cancelled"
        }
        self.filter.event_types = execution_types
        
        logger.info("Selection mode: EXECUTION_ONLY")
        return self
    
    def select_risk_checks_only(self) -> "EventSelector":
        """Select only risk check events"""
        self.selection_mode = SelectionMode.SPECIFIC
        
        risk_types = {
            "risk_check", "risk_limit_hit"
        }
        self.filter.event_types = risk_types
        
        logger.info("Selection mode: RISK_CHECKS_ONLY")
        return self
    
    def select_market_data_only(self) -> "EventSelector":
        """Select only market data events"""
        self.selection_mode = SelectionMode.SPECIFIC
        
        market_types = {
            "tick", "ohlcv", "orderbook"
        }
        self.filter.event_types = market_types
        
        logger.info("Selection mode: MARKET_DATA_ONLY")
        return self
    
    def select_dashboard_updates_only(self) -> "EventSelector":
        """Select only dashboard update events"""
        self.selection_mode = SelectionMode.SPECIFIC
        
        dashboard_types = {
            "dashboard_update", "metric_recorded"
        }
        self.filter.event_types = dashboard_types
        
        logger.info("Selection mode: DASHBOARD_UPDATES_ONLY")
        return self
    
    def select_time_range(
        self,
        start: datetime,
        end: datetime
    ) -> "EventSelector":
        """Select events in time range"""
        self.filter.start_time = start
        self.filter.end_time = end
        logger.info(f"Time range: {start} to {end}")
        return self
    
    def select_sequence_range(
        self,
        start: int,
        end: int
    ) -> "EventSelector":
        """Select events in sequence range"""
        self.filter.start_sequence = start
        self.filter.end_sequence = end
        logger.info(f"Sequence range: {start} to {end}")
        return self
    
    def with_custom_filter(
        self,
        filter_func: Callable[[Any], bool]
    ) -> "EventSelector":
        """Add custom filter function"""
        self.selection_mode = SelectionMode.CUSTOM
        self.filter.custom_filter = filter_func
        logger.info("Custom filter applied")
        return self
    
    def exclude_types(self, event_types: List[str]) -> "EventSelector":
        """Exclude specific event types"""
        self.filter.exclude = True
        self.filter.event_types = set(event_types)
        logger.info(f"Excluding types: {event_types}")
        return self
    
    def apply(self, events: List[Any]) -> List[Any]:
        """
        Apply selection filter to events.
        
        Args:
            events: List of events to filter
            
        Returns:
            Filtered list of events
        """
        if self.selection_mode == SelectionMode.ALL:
            return events
        
        filtered = [e for e in events if self.filter.matches(e)]
        
        logger.info(f"Selected {len(filtered)} of {len(events)} events")
        
        self._selected_events = filtered
        return filtered
    
    def get_selected(self) -> List[Any]:
        """Get currently selected events"""
        return self._selected_events
    
    def invert_selection(self) -> "EventSelector":
        """Invert current selection"""
        self.filter.exclude = not self.filter.exclude
        logger.info(f"Inverted selection (exclude={self.filter.exclude})")
        return self
    
    def union(self, other: "EventSelector") -> "EventSelector":
        """Combine with another selector (union)"""
        if self.selection_mode == SelectionMode.ALL:
            return other
        
        # Combine event types
        combined_types = self.filter.event_types | other.filter.event_types
        self.filter.event_types = combined_types
        
        # Combine trade IDs
        combined_trades = self.filter.trade_ids | other.filter.trade_ids
        self.filter.trade_ids = combined_trades
        
        logger.info("Combined selectors (union)")
        return self
    
    def intersect(self, other: "EventSelector") -> "EventSelector":
        """Intersect with another selector"""
        if self.selection_mode == SelectionMode.ALL:
            return other
        
        # Intersect event types
        combined_types = self.filter.event_types & other.filter.event_types
        self.filter.event_types = combined_types
        
        # Intersect trade IDs
        combined_trades = self.filter.trade_ids & other.filter.trade_ids
        self.filter.trade_ids = combined_trades
        
        logger.info("Combined selectors (intersection)")
        return self
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get selection statistics"""
        return {
            "mode": self.selection_mode.value,
            "event_types": list(self.filter.event_types),
            "trade_ids": list(self.filter.trade_ids),
            "time_range": {
                "start": self.filter.start_time.isoformat() if self.filter.start_time else None,
                "end": self.filter.end_time.isoformat() if self.filter.end_time else None
            },
            "sequence_range": {
                "start": self.filter.start_sequence,
                "end": self.filter.end_sequence
            },
            "exclude_mode": self.filter.exclude,
            "selected_count": len(self._selected_events)
        }
    
    def reset(self) -> None:
        """Reset selection"""
        self.selection_mode = SelectionMode.ALL
        self.filter = EventFilter()
        self._selected_events.clear()
        logger.info("Selection reset")


class TradeSelector:
    """
    Specialized selector for trade-centric replay.
    """
    
    def __init__(self):
        self.selected_trade_ids: Set[str] = set()
        self.include_related_events: bool = True
    
    def select_trade(self, trade_id: str) -> "TradeSelector":
        """Select a specific trade"""
        self.selected_trade_ids.add(trade_id)
        logger.info(f"Selected trade: {trade_id}")
        return self
    
    def select_trades(self, trade_ids: List[str]) -> "TradeSelector":
        """Select multiple trades"""
        self.selected_trade_ids.update(trade_ids)
        logger.info(f"Selected {len(trade_ids)} trades")
        return self
    
    def include_related(self, include: bool = True) -> "TradeSelector":
        """Include events related to selected trades"""
        self.include_related_events = include
        logger.info(f"Include related events: {include}")
        return self
    
    def get_filter(self) -> EventFilter:
        """Get filter for these trades"""
        filter = EventFilter()
        
        # Trade-related event types
        trade_types = {
            "trade_entry", "trade_exit", "order_placed",
            "order_filled", "order_cancelled", "risk_check"
        }
        filter.event_types = trade_types
        filter.trade_ids = self.selected_trade_ids
        
        return filter
    
    def get_trade_ids(self) -> Set[str]:
        """Get selected trade IDs"""
        return self.selected_trade_ids.copy()
