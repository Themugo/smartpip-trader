"""
Chaos Engineering and Resilience Testing for SmartPip Trading System
Tests system resilience under failure conditions
"""

import asyncio
import random
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import logging
from monitoring.opentelemetry_config import trading_metrics

logger = logging.getLogger(__name__)


class ChaosEngine:
    """Chaos engineering framework for testing resilience"""
    
    def __init__(self):
        self.experiments: Dict[str, Dict[str, Any]] = {}
        self.active_experiments: List[str] = []
        self.results: Dict[str, Dict[str, Any]] = {}
    
    def register_experiment(self, name: str, fault_type: str, 
                          probability: float = 0.1, duration: int = 30,
                          recovery_time: int = 60):
        """
        Register a chaos experiment
        
        Args:
            name: Experiment name
            fault_type: Type of fault (redis_failure, db_failure, api_latency, websocket_disconnect)
            probability: Probability of fault injection (0-1)
            duration: Duration of fault in seconds
            recovery_time: Time to allow recovery after fault
        """
        self.experiments[name] = {
            "fault_type": fault_type,
            "probability": probability,
            "duration": duration,
            "recovery_time": recovery_time,
            "enabled": False,
            "last_run": None
        }
        logger.info(f"Registered chaos experiment: {name}")
    
    def enable_experiment(self, name: str):
        """Enable a chaos experiment"""
        if name in self.experiments:
            self.experiments[name]["enabled"] = True
            logger.info(f"Enabled chaos experiment: {name}")
    
    def disable_experiment(self, name: str):
        """Disable a chaos experiment"""
        if name in self.experiments:
            self.experiments[name]["enabled"] = False
            logger.info(f"Disabled chaos experiment: {name}")
    
    async def run_experiment(self, name: str, target_system: Callable) -> Dict[str, Any]:
        """
        Run a chaos experiment
        
        Args:
            name: Experiment name
            target_system: System to test
            
        Returns:
            Experiment results
        """
        if name not in self.experiments:
            raise ValueError(f"Experiment not registered: {name}")
        
        experiment = self.experiments[name]
        
        if not experiment["enabled"]:
            return {"status": "skipped", "reason": "experiment disabled"}
        
        if random.random() > experiment["probability"]:
            return {"status": "skipped", "reason": "probability not met"}
        
        self.active_experiments.append(name)
        fault_type = experiment["fault_type"]
        
        logger.info(f"Starting chaos experiment: {name} ({fault_type})")
        
        start_time = time.time()
        result = {
            "experiment": name,
            "fault_type": fault_type,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "status": "running"
        }
        
        try:
            # Inject fault based on type
            if fault_type == "redis_failure":
                result.update(await self._inject_redis_failure(target_system, experiment["duration"]))
            elif fault_type == "db_failure":
                result.update(await self._inject_db_failure(target_system, experiment["duration"]))
            elif fault_type == "api_latency":
                result.update(await self._inject_api_latency(target_system, experiment["duration"]))
            elif fault_type == "websocket_disconnect":
                result.update(await self._inject_websocket_disconnect(target_system, experiment["duration"]))
            else:
                result["status"] = "error"
                result["error"] = f"Unknown fault type: {fault_type}"
        
        except Exception as e:
            logger.error(f"Chaos experiment failed: {e}")
            result["status"] = "error"
            result["error"] = str(e)
        
        # Allow recovery
        logger.info(f"Allowing recovery for {experiment['recovery_time']} seconds")
        await asyncio.sleep(experiment["recovery_time"])
        
        # Test recovery
        recovery_result = await self._test_recovery(target_system)
        result["recovery"] = recovery_result
        result["end_time"] = datetime.now(timezone.utc).isoformat()
        result["duration"] = time.time() - start_time
        
        self.results[name] = result
        self.active_experiments.remove(name)
        
        experiment["last_run"] = datetime.now(timezone.utc).isoformat()
        
        logger.info(f"Chaos experiment completed: {name}")
        
        return result
    
    async def _inject_redis_failure(self, target_system: Callable, duration: int) -> Dict[str, Any]:
        """Inject Redis failure"""
        logger.warning("Injecting Redis failure")
        
        # Simulate Redis failure by blocking Redis operations
        # In production, this would actually disconnect Redis
        start_time = time.time()
        
        try:
            # Test system behavior without Redis
            await target_system(redis_available=False)
            
            return {
                "redis_available": False,
                "duration": duration,
                "system_responded": True
            }
        except Exception as e:
            return {
                "redis_available": False,
                "duration": duration,
                "system_responded": False,
                "error": str(e)
            }
    
    async def _inject_db_failure(self, target_system: Callable, duration: int) -> Dict[str, Any]:
        """Inject database failure"""
        logger.warning("Injecting database failure")
        
        try:
            # Test system behavior without database
            await target_system(db_available=False)
            
            return {
                "db_available": False,
                "duration": duration,
                "system_responded": True
            }
        except Exception as e:
            return {
                "db_available": False,
                "duration": duration,
                "system_responded": False,
                "error": str(e)
            }
    
    async def _inject_api_latency(self, target_system: Callable, duration: int) -> Dict[str, Any]:
        """Inject API latency"""
        logger.warning(f"Injecting API latency for {duration} seconds")
        
        # Simulate high latency by adding delay
        async def delayed_call():
            await asyncio.sleep(2.0)  # 2 second delay
            return await target_system()
        
        try:
            start_time = time.time()
            result = await delayed_call()
            actual_duration = time.time() - start_time
            
            return {
                "latency_injected": 2.0,
                "duration": duration,
                "actual_duration": actual_duration,
                "system_responded": True
            }
        except Exception as e:
            return {
                "latency_injected": 2.0,
                "duration": duration,
                "system_responded": False,
                "error": str(e)
            }
    
    async def _inject_websocket_disconnect(self, target_system: Callable, duration: int) -> Dict[str, Any]:
        """Inject WebSocket disconnect storm"""
        logger.warning("Injecting WebSocket disconnect storm")
        
        try:
            # Test system behavior with WebSocket disconnects
            await target_system(websocket_connected=False)
            
            return {
                "websocket_connected": False,
                "duration": duration,
                "system_responded": True
            }
        except Exception as e:
            return {
                "websocket_connected": False,
                "duration": duration,
                "system_responded": False,
                "error": str(e)
            }
    
    async def _test_recovery(self, target_system: Callable) -> Dict[str, Any]:
        """Test system recovery after fault"""
        logger.info("Testing system recovery")
        
        try:
            # Test with all services available
            await target_system(redis_available=True, db_available=True, websocket_connected=True)
            
            return {
                "recovered": True,
                "time_to_recover": 0
            }
        except Exception as e:
            return {
                "recovered": False,
                "error": str(e)
            }
    
    def get_experiment_results(self, name: str = None) -> Dict[str, Any]:
        """Get experiment results"""
        if name:
            return self.results.get(name, {"error": "Experiment not found"})
        return self.results
    
    def get_active_experiments(self) -> List[str]:
        """Get currently active experiments"""
        return self.active_experiments


class ResilienceMetrics:
    """Track resilience metrics during chaos experiments"""
    
    def __init__(self):
        self.metrics = {
            "total_experiments": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "mean_time_to_recover": 0.0,
            "max_time_to_recover": 0.0
        }
    
    def record_experiment(self, result: Dict[str, Any]):
        """Record experiment result"""
        self.metrics["total_experiments"] += 1
        
        if result.get("recovery", {}).get("recovered"):
            self.metrics["successful_recoveries"] += 1
        else:
            self.metrics["failed_recoveries"] += 1
    
    def get_resilience_score(self) -> float:
        """Calculate overall resilience score"""
        if self.metrics["total_experiments"] == 0:
            return 0.0
        
        recovery_rate = self.metrics["successful_recoveries"] / self.metrics["total_experiments"]
        return recovery_rate * 100
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all resilience metrics"""
        return {
            **self.metrics,
            "resilience_score": self.get_resilience_score()
        }


class FailureScenario:
    """Predefined failure scenarios for testing"""
    
    @staticmethod
    def partial_redis_failure():
        """Simulate partial Redis failure (50% of requests fail)"""
        return {
            "name": "partial_redis_failure",
            "description": "50% of Redis requests fail",
            "severity": "medium"
        }
    
    @staticmethod
    def database_timeout():
        """Simulate database timeout"""
        return {
            "name": "database_timeout",
            "description": "Database queries timeout after 5 seconds",
            "severity": "high"
        }
    
    @staticmethod
    def websocket_storm():
        """Simulate WebSocket disconnect storm"""
        return {
            "name": "websocket_storm",
            "description": "Rapid WebSocket connect/disconnect cycles",
            "severity": "high"
        }
    
    @staticmethod
    def api_degradation():
        """Simulate API degradation (high latency)"""
        return {
            "name": "api_degradation",
            "description": "API latency increases to 5 seconds",
            "severity": "medium"
        }
    
    @staticmethod
    def exchange_outage():
        """Simulate exchange API outage"""
        return {
            "name": "exchange_outage",
            "description": "Deriv API returns 500 errors",
            "severity": "critical"
        }
    
    @staticmethod
    def memory_pressure():
        """Simulate memory pressure"""
        return {
            "name": "memory_pressure",
            "description": "System memory usage exceeds 90%",
            "severity": "high"
        }


# Global instances
chaos_engine = ChaosEngine()
resilience_metrics = ResilienceMetrics()

# Register default experiments
chaos_engine.register_experiment("redis_failure_test", "redis_failure", probability=0.05, duration=30, recovery_time=60)
chaos_engine.register_experiment("db_failure_test", "db_failure", probability=0.03, duration=30, recovery_time=60)
chaos_engine.register_experiment("api_latency_test", "api_latency", probability=0.1, duration=20, recovery_time=30)
chaos_engine.register_experiment("websocket_disconnect_test", "websocket_disconnect", probability=0.05, duration=15, recovery_time=30)
