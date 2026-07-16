"""
Failure Injection System
=======================

Injects various types of failures for testing.
"""

import time
import random
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class FailureType(Enum):
    """Types of failures that can be injected"""
    NETWORK_TIMEOUT = "network_timeout"
    NETWORK_ERROR = "network_error"
    API_ERROR = "api_error"
    RATE_LIMIT = "rate_limit"
    WEBSOCKET_DISCONNECT = "websocket_disconnect"
    WEBSOCKET_RECONNECT = "websocket_reconnect"
    PARTIAL_FILL = "partial_fill"
    ORDER_REJECTED = "order_rejected"
    ORDER_CANCELLED = "order_cancelled"
    DATA_CORRUPTION = "data_corruption"
    DATA_DELAY = "data_delay"
    CLOCK_DRIFT = "clock_drift"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


@dataclass
class FailureScenario:
    """Predefined failure scenario"""
    scenario_id: str
    name: str
    description: str
    failures: List[Dict[str, Any]]  # List of failures to inject
    probability: float = 1.0  # Probability of scenario occurring


@dataclass
class NetworkConditions:
    """Simulated network conditions"""
    latency_ms: float = 50
    jitter_ms: float = 10
    packet_loss_rate: float = 0.0  # 0.0 - 1.0
    corruption_rate: float = 0.0
    is_online: bool = True
    
    def apply_latency(self) -> float:
        """Apply latency with jitter"""
        jitter = random.uniform(-self.jitter_ms, self.jitter_ms)
        return max(0, self.latency_ms + jitter)
    
    def should_drop_packet(self) -> bool:
        """Check if packet should be dropped"""
        return random.random() < self.packet_loss_rate
    
    def should_corrupt(self) -> bool:
        """Check if data should be corrupted"""
        return random.random() < self.corruption_rate


class FailureInjector:
    """
    Injects failures into the system for testing.
    
    Provides controlled injection of various failure types
    to test system resilience.
    """
    
    def __init__(self):
        self._active = False
        self._lock = threading.Lock()
        self._scenarios: Dict[str, FailureScenario] = {}
        self._injected_failures: List[Dict[str, Any]] = []
        self._failure_callbacks: List[Callable] = []
        self._network_conditions = NetworkConditions()
    
    def start(self) -> None:
        """Start the failure injector"""
        self._active = True
        logger.info("Failure injector started")
    
    def stop(self) -> None:
        """Stop the failure injector"""
        self._active = False
        logger.info("Failure injector stopped")
    
    @property
    def is_active(self) -> bool:
        """Check if injector is active"""
        return self._active
    
    def register_scenario(self, scenario: FailureScenario) -> None:
        """Register a failure scenario"""
        self._scenarios[scenario.scenario_id] = scenario
    
    def unregister_scenario(self, scenario_id: str) -> bool:
        """Unregister a scenario"""
        return self._scenarios.pop(scenario_id, None) is not None
    
    def trigger_scenario(self, scenario_id: str) -> bool:
        """Trigger a specific scenario"""
        scenario = self._scenarios.get(scenario_id)
        if not scenario:
            return False
        
        if random.random() > scenario.probability:
            return False  # Scenario didn't trigger
        
        for failure in scenario.failures:
            self.inject_failure(
                failure_type=FailureType(failure["type"]),
                duration_ms=failure.get("duration_ms", 1000),
                **failure.get("params", {})
            )
        
        return True
    
    def inject_failure(
        self,
        failure_type: FailureType,
        duration_ms: float = 1000,
        **params
    ) -> Dict[str, Any]:
        """
        Inject a specific failure.
        
        Args:
            failure_type: Type of failure to inject
            duration_ms: Duration of failure in milliseconds
            **params: Additional parameters
            
        Returns:
            Failure info dict
        """
        with self._lock:
            failure_info = {
                "type": failure_type.value,
                "start_time": time.time(),
                "duration_ms": duration_ms,
                "params": params,
                "injected": False,
            }
            
            # Handle different failure types
            if failure_type == FailureType.NETWORK_TIMEOUT:
                self._inject_network_timeout(duration_ms, params)
            
            elif failure_type == FailureType.NETWORK_ERROR:
                self._inject_network_error(duration_ms, params)
            
            elif failure_type == FailureType.API_ERROR:
                self._inject_api_error(duration_ms, params)
            
            elif failure_type == FailureType.RATE_LIMIT:
                self._inject_rate_limit(duration_ms, params)
            
            elif failure_type == FailureType.WEBSOCKET_DISCONNECT:
                self._inject_websocket_disconnect(duration_ms, params)
            
            elif failure_type == FailureType.WEBSOCKET_RECONNECT:
                self._inject_websocket_reconnect(duration_ms, params)
            
            elif failure_type == FailureType.PARTIAL_FILL:
                self._inject_partial_fill(duration_ms, params)
            
            elif failure_type == FailureType.ORDER_REJECTED:
                self._inject_order_rejected(duration_ms, params)
            
            elif failure_type == FailureType.DATA_CORRUPTION:
                self._inject_data_corruption(duration_ms, params)
            
            elif failure_type == FailureType.DATA_DELAY:
                self._inject_data_delay(duration_ms, params)
            
            elif failure_type == FailureType.CLOCK_DRIFT:
                self._inject_clock_drift(duration_ms, params)
            
            elif failure_type == FailureType.RESOURCE_EXHAUSTION:
                self._inject_resource_exhaustion(duration_ms, params)
            
            failure_info["injected"] = True
            failure_info["end_time"] = time.time() + duration_ms / 1000
            
            self._injected_failures.append(failure_info)
            
            # Trigger callbacks
            for callback in self._failure_callbacks:
                try:
                    callback(failure_info)
                except Exception as e:
                    logger.error(f"Failure callback error: {e}")
            
            return failure_info
    
    def _inject_network_timeout(self, duration_ms: float, params: Dict) -> None:
        """Simulate network timeout"""
        logger.warning(f"Injecting network timeout for {duration_ms}ms")
        self._network_conditions.latency_ms = 10000  # 10 seconds
        time.sleep(duration_ms / 1000)
        self._network_conditions.latency_ms = 50  # Reset
    
    def _inject_network_error(self, duration_ms: float, params: Dict) -> None:
        """Simulate network error"""
        logger.warning(f"Injecting network error for {duration_ms}ms")
        self._network_conditions.is_online = False
        time.sleep(duration_ms / 1000)
        self._network_conditions.is_online = True
    
    def _inject_api_error(self, duration_ms: float, params: Dict) -> None:
        """Simulate API error"""
        error_code = params.get("error_code", "INTERNAL_ERROR")
        logger.warning(f"Injecting API error: {error_code} for {duration_ms}ms")
        time.sleep(duration_ms / 1000)
    
    def _inject_rate_limit(self, duration_ms: float, params: Dict) -> None:
        """Simulate rate limiting"""
        logger.warning(f"Injecting rate limit for {duration_ms}ms")
        time.sleep(duration_ms / 1000)
    
    def _inject_websocket_disconnect(self, duration_ms: float, params: Dict) -> None:
        """Simulate WebSocket disconnect"""
        logger.warning(f"Injecting WebSocket disconnect for {duration_ms}ms")
        time.sleep(duration_ms / 1000)
    
    def _inject_websocket_reconnect(self, duration_ms: float, params: Dict) -> None:
        """Simulate WebSocket reconnect"""
        logger.warning(f"Injecting WebSocket reconnect delay for {duration_ms}ms")
        time.sleep(duration_ms / 1000)
    
    def _inject_partial_fill(self, duration_ms: float, params: Dict) -> None:
        """Simulate partial fill"""
        fill_percentage = params.get("fill_percentage", 0.5)
        logger.warning(f"Injecting partial fill: {fill_percentage:.0%}")
    
    def _inject_order_rejected(self, duration_ms: float, params: Dict) -> None:
        """Simulate order rejection"""
        reason = params.get("reason", "MANUAL_INJECTION")
        logger.warning(f"Injecting order rejection: {reason}")
    
    def _inject_data_corruption(self, duration_ms: float, params: Dict) -> None:
        """Simulate data corruption"""
        logger.warning(f"Injecting data corruption for {duration_ms}ms")
        self._network_conditions.corruption_rate = 0.5
        time.sleep(duration_ms / 1000)
        self._network_conditions.corruption_rate = 0.0
    
    def _inject_data_delay(self, duration_ms: float, params: Dict) -> None:
        """Simulate data delay"""
        logger.warning(f"Injecting data delay of {duration_ms}ms")
        time.sleep(duration_ms / 1000)
    
    def _inject_clock_drift(self, duration_ms: float, params: Dict) -> None:
        """Simulate clock drift"""
        drift_seconds = params.get("drift_seconds", 5)
        logger.warning(f"Injecting clock drift of {drift_seconds}s")
    
    def _inject_resource_exhaustion(self, duration_ms: float, params: Dict) -> None:
        """Simulate resource exhaustion"""
        logger.warning(f"Injecting resource exhaustion for {duration_ms}ms")
        time.sleep(duration_ms / 1000)
    
    def on_failure(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a failure callback"""
        self._failure_callbacks.append(callback)
    
    def get_network_conditions(self) -> NetworkConditions:
        """Get current network conditions"""
        return self._network_conditions
    
    def set_network_conditions(self, conditions: NetworkConditions) -> None:
        """Set network conditions"""
        self._network_conditions = conditions
    
    def get_injected_failures(self) -> List[Dict[str, Any]]:
        """Get list of injected failures"""
        return self._injected_failures.copy()
    
    def clear_failures(self) -> None:
        """Clear injected failures history"""
        self._injected_failures.clear()
    
    def create_scenario_from_template(
        self,
        scenario_id: str,
        name: str,
        failure_types: List[FailureType],
        interval_ms: float = 1000,
        duration_ms: float = 5000
    ) -> FailureScenario:
        """Create a scenario from failure types"""
        failures = []
        for ftype in failure_types:
            failures.append({
                "type": ftype.value,
                "duration_ms": duration_ms,
                "params": {}
            })
        
        return FailureScenario(
            scenario_id=scenario_id,
            name=name,
            description=f"Custom scenario with {len(failure_types)} failure types",
            failures=failures
        )


# Predefined failure scenarios
class FailureScenarios:
    """Predefined failure scenarios for testing"""
    
    @staticmethod
    def network_instability() -> FailureScenario:
        """Network with intermittent issues"""
        return FailureScenario(
            scenario_id="network_instability",
            name="Network Instability",
            description="Intermittent network issues causing timeouts",
            failures=[
                {"type": "network_timeout", "duration_ms": 2000, "params": {}},
                {"type": "network_error", "duration_ms": 1000, "params": {}},
            ],
            probability=0.3
        )
    
    @staticmethod
    def api_overload() -> FailureScenario:
        """Exchange API overload"""
        return FailureScenario(
            scenario_id="api_overload",
            name="API Overload",
            description="High rate limiting and API errors",
            failures=[
                {"type": "rate_limit", "duration_ms": 5000, "params": {}},
                {"type": "api_error", "duration_ms": 3000, "params": {"error_code": "SERVICE_UNAVAILABLE"}},
            ],
            probability=0.2
        )
    
    @staticmethod
    def websocket_issues() -> FailureScenario:
        """WebSocket connection problems"""
        return FailureScenario(
            scenario_id="websocket_issues",
            name="WebSocket Issues",
            description="Frequent WebSocket disconnections",
            failures=[
                {"type": "websocket_disconnect", "duration_ms": 3000, "params": {}},
                {"type": "websocket_reconnect", "duration_ms": 2000, "params": {}},
            ],
            probability=0.4
        )
    
    @staticmethod
    def market_data_issues() -> FailureScenario:
        """Market data delivery problems"""
        return FailureScenario(
            scenario_id="market_data_issues",
            name="Market Data Issues",
            description="Delays and corruption in market data",
            failures=[
                {"type": "data_delay", "duration_ms": 5000, "params": {}},
                {"type": "data_corruption", "duration_ms": 2000, "params": {}},
            ],
            probability=0.25
        )
    
    @staticmethod
    def complete_outage() -> FailureScenario:
        """Complete system outage"""
        return FailureScenario(
            scenario_id="complete_outage",
            name="Complete Outage",
            description="All systems down for extended period",
            failures=[
                {"type": "network_error", "duration_ms": 10000, "params": {}},
                {"type": "api_error", "duration_ms": 15000, "params": {"error_code": "SERVICE_UNAVAILABLE"}},
            ],
            probability=0.05
        )
