"""
Trading Events
=============

Events related to trade execution and approvals.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .core import Event, EventType, EventMetadata


@dataclass
class TradeApprovalEvent(Event):
    """Trade approval event"""
    
    def __init__(
        self,
        order_id: str,
        symbol: str,
        action: str,
        quantity: float,
        price: float,
        approved_by: str,  # "ai", "manual", "risk_manager"
        timestamp: float,
        conditions: List[str] = None,
        risk_metrics: Optional[Dict[str, float]] = None,
        metadata: Optional[EventMetadata] = None,
    ):
        payload = {
            "order_id": order_id,
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "price": price,
            "approved_by": approved_by,
            "conditions": conditions or [],
            "risk_metrics": risk_metrics or {},
            "timestamp": timestamp,
        }
        
        if metadata is None:
            metadata = EventMetadata()
        
        super().__init__(
            event_type=EventType.TRADE_APPROVAL,
            metadata=metadata,
            payload=payload,
        )


@dataclass
class TradeRejectionEvent(Event):
    """Trade rejection event"""
    
    def __init__(
        self,
        order_id: str,
        symbol: str,
        action: str,
        rejected_by: str,  # "risk_manager", "validator", "manual"
        reason: str,
        rejection_code: str,
        timestamp: float,
        risk_metrics: Optional[Dict[str, float]] = None,
        metadata: Optional[EventMetadata] = None,
    ):
        payload = {
            "order_id": order_id,
            "symbol": symbol,
            "action": action,
            "rejected_by": rejected_by,
            "reason": reason,
            "rejection_code": rejection_code,
            "risk_metrics": risk_metrics or {},
            "timestamp": timestamp,
        }
        
        if metadata is None:
            metadata = EventMetadata()
        
        super().__init__(
            event_type=EventType.TRADE_REJECTION,
            metadata=metadata,
            payload=payload,
        )


@dataclass
class ExecutionRequestEvent(Event):
    """Execution request event"""
    
    def __init__(
        self,
        order_id: str,
        symbol: str,
        side: str,  # buy, sell
        order_type: str,  # market, limit, stop
        quantity: float,
        price: float,
        timestamp: float,
        exchange: str = "",
        client_order_id: str = "",
        metadata: Optional[EventMetadata] = None,
    ):
        payload = {
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "order_type": order_type,
            "quantity": quantity,
            "price": price,
            "exchange": exchange,
            "client_order_id": client_order_id,
            "timestamp": timestamp,
        }
        
        if metadata is None:
            metadata = EventMetadata()
        
        super().__init__(
            event_type=EventType.EXECUTION_REQUEST,
            metadata=metadata,
            payload=payload,
        )


@dataclass
class ExecutionConfirmationEvent(Event):
    """Execution confirmation event"""
    
    def __init__(
        self,
        order_id: str,
        execution_id: str,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        commission: float,
        timestamp: float,
        execution_time_ms: float = 0,
        slippage: float = 0,
        metadata: Optional[EventMetadata] = None,
    ):
        payload = {
            "order_id": order_id,
            "execution_id": execution_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "commission": commission,
            "execution_time_ms": execution_time_ms,
            "slippage": slippage,
            "total_cost": quantity * price + commission,
            "timestamp": timestamp,
        }
        
        if metadata is None:
            metadata = EventMetadata()
        
        super().__init__(
            event_type=EventType.EXECUTION_CONFIRMATION,
            metadata=metadata,
            payload=payload,
        )


@dataclass
class ExecutionFailureEvent(Event):
    """Execution failure event"""
    
    def __init__(
        self,
        order_id: str,
        failure_code: str,
        reason: str,
        timestamp: float,
        retryable: bool = False,
        retry_count: int = 0,
        exchange_error_code: str = "",
        metadata: Optional[EventMetadata] = None,
    ):
        payload = {
            "order_id": order_id,
            "failure_code": failure_code,
            "reason": reason,
            "retryable": retryable,
            "retry_count": retry_count,
            "exchange_error_code": exchange_error_code,
            "timestamp": timestamp,
        }
        
        if metadata is None:
            metadata = EventMetadata()
        
        super().__init__(
            event_type=EventType.EXECUTION_FAILURE,
            metadata=metadata,
            payload=payload,
        )
