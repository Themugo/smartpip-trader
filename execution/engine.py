"""
Execution Engine - Professional Trade Execution

Professional execution engine with validation, retry, and journaling.
"""

import asyncio
import hashlib
import logging
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    """Order side"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order status"""
    PENDING = "pending"
    VALIDATING = "validating"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    FAILED = "failed"


class TimeInForce(Enum):
    """Time in force"""
    GTC = "gtc"  # Good till cancelled
    IOC = "ioc"  # Immediate or cancel
    FOK = "fok"  # Fill or kill


@dataclass
class Order:
    """A trading order"""
    id: str
    symbol: str
    order_type: OrderType
    side: OrderSide
    amount: float
    price: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.GTC
    
    # Status
    status: OrderStatus = OrderStatus.PENDING
    
    # Execution
    filled_amount: float = 0
    average_price: float = 0
    commission: float = 0
    
    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    
    # Validation
    validation_errors: List[str] = field(default_factory=list)
    
    # Tracking
    correlation_id: Optional[str] = None
    strategy_id: Optional[str] = None
    parent_order_id: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Duplicate check
    order_hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "order_type": self.order_type.value,
            "side": self.side.value,
            "amount": self.amount,
            "price": self.price,
            "time_in_force": self.time_in_force.value,
            "status": self.status.value,
            "filled_amount": self.filled_amount,
            "average_price": self.average_price,
            "commission": self.commission,
            "created_at": self.created_at.isoformat(),
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "validation_errors": self.validation_errors,
            "correlation_id": self.correlation_id,
            "strategy_id": self.strategy_id,
            "metadata": self.metadata,
        }


@dataclass
class ExecutionReport:
    """Execution report"""
    order: Order
    success: bool
    message: str
    
    # Timing
    latency_ms: float = 0
    execution_time_ms: float = 0
    
    # Fill details
    fill_price: float = 0
    fill_amount: float = 0
    slippage: float = 0
    
    # Errors
    error_code: Optional[str] = None
    
    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order.id,
            "success": self.success,
            "message": self.message,
            "latency_ms": self.latency_ms,
            "execution_time_ms": self.execution_time_ms,
            "fill_price": self.fill_price,
            "fill_amount": self.fill_amount,
            "slippage": self.slippage,
            "error_code": self.error_code,
            "timestamp": self.timestamp.isoformat(),
        }


class ExecutionEngine:
    """
    Professional execution engine.
    
    Features:
    - Pre-trade validation
    - Duplicate prevention
    - Retry logic
    - Execution journaling
    - Latency monitoring
    - Emergency cancel
    - Simulation mode
    """
    
    def __init__(
        self,
        journal_path: str = "data/execution",
        simulation_mode: bool = False,
    ):
        self._journal_path = journal_path
        self._simulation_mode = simulation_mode
        
        # Order tracking
        self._orders: Dict[str, Order] = {}
        self._order_history: deque = deque(maxlen=10000)
        self._pending_orders: Dict[str, Order] = {}
        
        # Duplicate prevention
        self._recent_hashes: deque = deque(maxlen=1000)
        
        # Pre-trade validators
        self._validators: List[Callable[[Order], tuple[bool, str]]] = []
        
        # Retry configuration
        self._max_retries = 3
        self._retry_delay_ms = 100
        
        # Latency tracking
        self._latency_history: deque = deque(maxlen=1000)
        
        # Execution callbacks
        self._execution_callbacks: List[Callable[[ExecutionReport], None]] = []
        
        # Emergency stop
        self._emergency_stop = False
        
        import os
        os.makedirs(journal_path, exist_ok=True)
        
        self._logger = logging.getLogger(f"{__name__}.Execution")
    
    def add_validator(
        self,
        validator: Callable[[Order], tuple[bool, str]],
    ) -> None:
        """Add a pre-trade validator"""
        self._validators.append(validator)
    
    def set_simulation_mode(self, enabled: bool) -> None:
        """Enable or disable simulation mode"""
        self._simulation_mode = enabled
        self._logger.info(f"Simulation mode: {enabled}")
    
    def emergency_stop(self) -> None:
        """Trigger emergency stop"""
        self._emergency_stop = True
        self._logger.warning("EMERGENCY STOP ACTIVATED")
        
        # Cancel all pending orders
        for order_id in list(self._pending_orders.keys()):
            self.cancel_order(order_id)
    
    def emergency_resume(self) -> None:
        """Resume from emergency stop"""
        self._emergency_stop = False
        self._logger.info("Emergency stop released")
    
    async def execute_order(
        self,
        symbol: str,
        side: OrderSide,
        amount: float,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        strategy_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionReport:
        """
        Execute a trading order.
        
        Args:
            symbol: Trading symbol
            side: Order side (BUY/SELL)
            amount: Order amount
            order_type: Order type
            price: Limit price (for limit orders)
            strategy_id: Strategy that generated the order
            metadata: Additional metadata
            
        Returns:
            ExecutionReport with execution details
        """
        start_time = time.time()
        
        # Create order
        order = Order(
            id=str(uuid.uuid4()),
            symbol=symbol,
            order_type=order_type,
            side=side,
            amount=amount,
            price=price,
            strategy_id=strategy_id,
            metadata=metadata or {},
        )
        
        # Generate order hash for duplicate detection
        order.order_hash = self._generate_order_hash(order)
        
        # Check for duplicate
        if self._is_duplicate(order):
            return ExecutionReport(
                order=order,
                success=False,
                message="Duplicate order detected",
                latency_ms=(time.time() - start_time) * 1000,
                error_code="DUPLICATE",
            )
        
        # Check emergency stop
        if self._emergency_stop:
            order.status = OrderStatus.REJECTED
            order.validation_errors.append("Emergency stop active")
            return ExecutionReport(
                order=order,
                success=False,
                message="Execution blocked by emergency stop",
                latency_ms=(time.time() - start_time) * 1000,
                error_code="EMERGENCY_STOP",
            )
        
        # Pre-trade validation
        order.status = OrderStatus.VALIDATING
        validation_passed, validation_message = await self._validate_order(order)
        
        if not validation_passed:
            order.status = OrderStatus.REJECTED
            order.validation_errors.append(validation_message)
            
            report = ExecutionReport(
                order=order,
                success=False,
                message=f"Validation failed: {validation_message}",
                latency_ms=(time.time() - start_time) * 1000,
                error_code="VALIDATION_FAILED",
            )
            self._record_report(report)
            return report
        
        # Simulation mode
        if self._simulation_mode:
            order.status = OrderStatus.FILLED
            order.filled_amount = order.amount
            order.average_price = order.price or 100  # Simulated price
            
            report = ExecutionReport(
                order=order,
                success=True,
                message="Order executed (simulation)",
                latency_ms=(time.time() - start_time) * 1000,
                execution_time_ms=10,
                fill_price=order.average_price,
                fill_amount=order.amount,
            )
            self._record_report(report)
            return report
        
        # Submit order
        order.status = OrderStatus.SUBMITTED
        order.submitted_at = datetime.now(timezone.utc)
        self._orders[order.id] = order
        self._pending_orders[order.id] = order
        self._recent_hashes.append(order.order_hash)
        
        # Execute with retry
        report = await self._execute_with_retry(order, start_time)
        
        # Remove from pending
        if order.id in self._pending_orders:
            del self._pending_orders[order.id]
        
        self._record_report(report)
        return report
    
    async def _validate_order(self, order: Order) -> tuple[bool, str]:
        """Validate an order"""
        # Run custom validators
        for validator in self._validators:
            passed, message = validator(order)
            if not passed:
                return False, message
        
        # Basic validation
        if order.amount <= 0:
            return False, "Invalid amount"
        
        if order.order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT):
            if not order.price or order.price <= 0:
                return False, "Invalid price for limit order"
        
        return True, "Validation passed"
    
    def _is_duplicate(self, order: Order) -> bool:
        """Check for duplicate orders"""
        return order.order_hash in self._recent_hashes
    
    def _generate_order_hash(self, order: Order) -> str:
        """Generate order hash for duplicate detection"""
        hash_input = f"{order.symbol}:{order.side.value}:{order.amount}:{order.order_type.value}:{order.created_at.isoformat()}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    async def _execute_with_retry(
        self,
        order: Order,
        start_time: float,
    ) -> ExecutionReport:
        """Execute order with retry logic"""
        for attempt in range(self._max_retries):
            try:
                # Execute the order (would call actual API here)
                execution_result = await self._submit_to_exchange(order)
                
                latency_ms = (time.time() - start_time) * 1000
                self._latency_history.append(latency_ms)
                
                return execution_result
                
            except Exception as e:
                self._logger.warning(f"Execution attempt {attempt + 1} failed: {e}")
                
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(self._retry_delay_ms / 1000)
                    continue
                
                order.status = OrderStatus.FAILED
                return ExecutionReport(
                    order=order,
                    success=False,
                    message=f"Execution failed after {self._max_retries} attempts: {str(e)}",
                    latency_ms=(time.time() - start_time) * 1000,
                    error_code="EXECUTION_FAILED",
                )
        
        return ExecutionReport(
            order=order,
            success=False,
            message="Max retries exceeded",
            latency_ms=(time.time() - start_time) * 1000,
            error_code="MAX_RETRIES",
        )
    
    async def _submit_to_exchange(self, order: Order) -> ExecutionReport:
        """Submit order to exchange (placeholder)"""
        # This would integrate with actual exchange API
        await asyncio.sleep(0.01)  # Simulate network latency
        
        # Simulate successful fill
        order.status = OrderStatus.FILLED
        order.filled_amount = order.amount
        order.average_price = order.price or 100
        order.filled_at = datetime.now(timezone.utc)
        
        return ExecutionReport(
            order=order,
            success=True,
            message="Order filled",
            execution_time_ms=10,
            fill_price=order.average_price,
            fill_amount=order.amount,
        )
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order"""
        order = self._orders.get(order_id) or self._pending_orders.get(order_id)
        
        if not order:
            return False
        
        if order.status not in (OrderStatus.PENDING, OrderStatus.SUBMITTED):
            return False
        
        order.status = OrderStatus.CANCELLED
        
        if order_id in self._pending_orders:
            del self._pending_orders[order_id]
        
        self._logger.info(f"Order {order_id} cancelled")
        return True
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get an order by ID"""
        return self._orders.get(order_id)
    
    def get_pending_orders(self) -> List[Order]:
        """Get all pending orders"""
        return list(self._pending_orders.values())
    
    def get_order_history(
        self,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Order]:
        """Get order history"""
        orders = list(self._order_history)
        
        if since:
            orders = [o for o in orders if o.created_at >= since]
        
        return orders[-limit:]
    
    def _record_report(self, report: ExecutionReport) -> None:
        """Record execution report"""
        self._orders[report.order.id] = report.order
        self._order_history.append(report.order)
        
        # Fire callbacks
        for callback in self._execution_callbacks:
            try:
                callback(report)
            except Exception as e:
                self._logger.error(f"Execution callback error: {e}")
    
    def on_execution(self, callback: Callable[[ExecutionReport], None]) -> None:
        """Register an execution callback"""
        self._execution_callbacks.append(callback)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics"""
        orders = list(self._order_history)
        
        if not orders:
            return {"total_orders": 0}
        
        filled = sum(1 for o in orders if o.status == OrderStatus.FILLED)
        cancelled = sum(1 for o in orders if o.status == OrderStatus.CANCELLED)
        rejected = sum(1 for o in orders if o.status == OrderStatus.REJECTED)
        
        avg_latency = (
            sum(self._latency_history) / len(self._latency_history)
            if self._latency_history else 0
        )
        
        return {
            "total_orders": len(orders),
            "filled": filled,
            "cancelled": cancelled,
            "rejected": rejected,
            "fill_rate": filled / len(orders) if orders else 0,
            "pending": len(self._pending_orders),
            "avg_latency_ms": avg_latency,
            "simulation_mode": self._simulation_mode,
            "emergency_stop": self._emergency_stop,
        }
