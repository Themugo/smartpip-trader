"""
Dependency Map
==============

Maps and validates service dependencies.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Callable, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class DependencyType(Enum):
    """Types of dependencies"""
    HARD = "hard"           # Required, service can't function without it
    SOFT = "soft"           # Optional, service can degrade gracefully
    CIRCUIT_BREAKER = "circuit_breaker"  # Protected by circuit breaker


@dataclass
class Dependency:
    """A dependency relationship"""
    source: str              # Service that has the dependency
    target: str              # Service being depended on
    dependency_type: DependencyType
    timeout_seconds: float = 5.0
    required_availability: float = 99.0  # Required uptime percentage
    
    # State
    last_check: Optional[float] = None
    last_successful_call: Optional[float] = None
    last_failed_call: Optional[float] = None
    consecutive_failures: int = 0
    total_calls: int = 0
    failed_calls: int = 0
    mean_latency_ms: float = 0.0
    
    # Validation
    is_healthy: bool = True
    health_check_enabled: bool = True
    auto_validate: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "source": self.source,
            "target": self.target,
            "dependency_type": self.dependency_type.value,
            "timeout_seconds": self.timeout_seconds,
            "required_availability": self.required_availability,
            "last_check": self.last_check,
            "last_successful_call": self.last_successful_call,
            "last_failed_call": self.last_failed_call,
            "consecutive_failures": self.consecutive_failures,
            "total_calls": self.total_calls,
            "failed_calls": self.failed_calls,
            "mean_latency_ms": self.mean_latency_ms,
            "is_healthy": self.is_healthy,
            "health_check_enabled": self.health_check_enabled,
            "availability": (
                (self.total_calls - self.failed_calls) / max(1, self.total_calls) * 100
            )
        }


@dataclass
class DependencyGraph:
    """Complete dependency graph"""
    nodes: List[str] = field(default_factory=list)
    edges: List[Tuple[str, str]] = field(default_factory=list)
    adjacency: Dict[str, List[str]] = field(default_factory=dict)


class DependencyMap:
    """
    Maps and manages service dependencies.
    
    Features:
    - Dependency registration
    - Circular dependency detection
    - Dependency validation
    - Impact analysis
    - Cascading failure detection
    - Health tracking per dependency
    """
    
    def __init__(self):
        self._dependencies: Dict[str, List[Dependency]] = {}  # source -> dependencies
        self._dependents: Dict[str, List[str]] = {}  # target -> sources
        self._all_services: Set[str] = set()
        self._lock = asyncio.Lock()
        
        # Callbacks
        self._on_dependency_unhealthy: List[Callable[[Dependency], None]] = []
        self._on_dependency_healthy: List[Callable[[Dependency], None]] = []
        self._on_cascading_failure_risk: List[Callable[[str, List[str]], None]] = []
    
    def register_dependency(
        self,
        source: str,
        target: str,
        dependency_type: DependencyType = DependencyType.HARD,
        timeout_seconds: float = 5.0,
        required_availability: float = 99.0
    ) -> Dependency:
        """
        Register a dependency between services.
        
        Args:
            source: Service that depends on another
            target: Service being depended on
            dependency_type: Type of dependency
            timeout_seconds: Call timeout
            required_availability: Required uptime percentage
            
        Returns:
            Created Dependency object
        """
        # Check for circular dependency
        if self._would_create_cycle(source, target):
            raise CircularDependencyError(
                f"Registering {source} -> {target} would create circular dependency"
            )
        
        dependency = Dependency(
            source=source,
            target=target,
            dependency_type=dependency_type,
            timeout_seconds=timeout_seconds,
            required_availability=required_availability
        )
        
        # Add to dependencies
        if source not in self._dependencies:
            self._dependencies[source] = []
        self._dependencies[source].append(dependency)
        
        # Add to dependents
        if target not in self._dependents:
            self._dependents[target] = []
        if source not in self._dependents[target]:
            self._dependents[target].append(source)
        
        # Track all services
        self._all_services.add(source)
        self._all_services.add(target)
        
        logger.info(
            f"Registered dependency: {source} -> {target} "
            f"({dependency_type.value})"
        )
        
        return dependency
    
    def _would_create_cycle(self, source: str, target: str) -> bool:
        """Check if adding an edge would create a cycle"""
        # If target already has a path to source, adding source->target creates cycle
        return self._has_path(target, source)
    
    def _has_path(self, start: str, end: str) -> bool:
        """Check if there's a path from start to end"""
        visited = set()
        stack = [start]
        
        while stack:
            current = stack.pop()
            
            if current == end:
                return True
            
            if current in visited:
                continue
            
            visited.add(current)
            
            # Add dependents as neighbors (reversed direction)
            if current in self._dependents:
                stack.extend(self._dependents[current])
        
        return False
    
    def get_dependencies(self, service: str) -> List[Dependency]:
        """Get dependencies for a service"""
        return self._dependencies.get(service, []).copy()
    
    def get_dependents(self, service: str) -> List[str]:
        """Get services that depend on this service"""
        return self._dependents.get(service, []).copy()
    
    def get_dependency_chain(self, service: str) -> List[List[str]]:
        """
        Get all dependency chains starting from a service.
        
        Returns list of paths from service to terminal dependencies.
        """
        chains = []
        
        def dfs(current: str, path: List[str], visited: Set[str]):
            if current not in self._dependencies or not self._dependencies[current]:
                chains.append(path.copy())
                return
            
            for dep in self._dependencies[current]:
                if dep.target in visited:
                    continue
                path.append(dep.target)
                visited.add(dep.target)
                dfs(dep.target, path, visited)
                path.pop()
                visited.remove(dep.target)
        
        dfs(service, [service], {service})
        return chains
    
    def get_impacted_services(self, service: str) -> List[str]:
        """
        Get all services that would be impacted if this service fails.
        
        Includes the service itself and all its dependents (transitively).
        """
        impacted = [service]
        stack = [service]
        
        while stack:
            current = stack.pop()
            
            for dependent in self._dependents.get(current, []):
                if dependent not in impacted:
                    impacted.append(dependent)
                    stack.append(dependent)
        
        return impacted
    
    def get_cascading_failure_risk(self, service: str) -> Dict[str, Any]:
        """
        Analyze cascading failure risk for a service.
        
        Returns risk assessment including:
        - Number of impacted services
        - Critical path depth
        - Whether it's a single point of failure
        """
        impacted = self.get_impacted_services(service)
        
        # Calculate dependency depth
        def get_depth(svc: str, visited: Set[str]) -> int:
            if svc not in self._dependencies or not self._dependencies[svc]:
                return 0
            
            max_depth = 0
            for dep in self._dependencies[svc]:
                if dep.target not in visited:
                    visited.add(dep.target)
                    max_depth = max(max_depth, 1 + get_depth(dep.target, visited))
                    visited.remove(dep.target)
            
            return max_depth
        
        depth = get_depth(service, {service})
        
        # Check for single point of failure
        # A service is a SPOF if removing it would break all paths to terminal deps
        is_spof = len(self._dependents.get(service, [])) > 0 and depth == 1
        
        # Count hard dependencies
        hard_deps = sum(
            1 for dep in self._dependencies.get(service, [])
            if dep.dependency_type == DependencyType.HARD
        )
        
        return {
            "service": service,
            "impacted_services": impacted,
            "impacted_count": len(impacted),
            "dependency_depth": depth,
            "is_single_point_of_failure": is_spof,
            "hard_dependencies": hard_deps,
            "risk_level": self._calculate_risk_level(
                len(impacted), depth, is_spof, hard_deps
            )
        }
    
    def _calculate_risk_level(
        self,
        impacted_count: int,
        depth: int,
        is_spof: bool,
        hard_deps: int
    ) -> str:
        """Calculate risk level string"""
        score = impacted_count + depth * 2
        
        if is_spof:
            score += 5
        score += hard_deps * 2
        
        if score >= 10:
            return "critical"
        elif score >= 5:
            return "high"
        elif score >= 2:
            return "medium"
        else:
            return "low"
    
    async def record_call(
        self,
        source: str,
        target: str,
        success: bool,
        latency_ms: float
    ) -> None:
        """Record a dependency call result"""
        async with self._lock:
            dependencies = self._dependencies.get(source, [])
            
            for dep in dependencies:
                if dep.target == target:
                    dep.total_calls += 1
                    dep.last_check = time.time()
                    
                    if success:
                        dep.last_successful_call = time.time()
                        dep.consecutive_failures = 0
                    else:
                        dep.last_failed_call = time.time()
                        dep.consecutive_failures += 1
                    
                    # Update mean latency
                    alpha = 0.1
                    dep.mean_latency_ms = (
                        alpha * latency_ms + (1 - alpha) * dep.mean_latency_ms
                    )
                    
                    # Check health
                    old_health = dep.is_healthy
                    
                    if dep.consecutive_failures >= 3:
                        dep.is_healthy = False
                    elif success and dep.consecutive_failures == 0:
                        dep.is_healthy = True
                    
                    # Trigger callbacks
                    if not old_health and not dep.is_healthy:
                        for callback in self._on_dependency_unhealthy:
                            try:
                                callback(dep)
                            except Exception as e:
                                logger.error(f"Dependency unhealthy callback failed: {e}")
                    
                    if old_health and dep.is_healthy:
                        for callback in self._on_dependency_unhealthy:
                            try:
                                callback(dep)
                            except Exception as e:
                                logger.error(f"Dependency unhealthy callback failed: {e}")
                    
                    break
    
    def get_dependency_graph(self) -> DependencyGraph:
        """Get the complete dependency graph"""
        nodes = list(self._all_services)
        
        edges = []
        for source, deps in self._dependencies.items():
            for dep in deps:
                edges.append((source, dep.target))
        
        return DependencyGraph(
            nodes=nodes,
            edges=edges,
            adjacency=self._dependents.copy()
        )
    
    def validate_dependencies(self) -> Dict[str, Any]:
        """
        Validate all dependencies and return validation report.
        
        Checks:
        - Circular dependencies
        - Unreachable dependencies
        - Health violations
        """
        issues = []
        
        # Check for unhealthy dependencies
        for source, deps in self._dependencies.items():
            for dep in deps:
                if not dep.is_healthy:
                    issues.append({
                        "type": "unhealthy",
                        "source": source,
                        "target": dep.target,
                        "consecutive_failures": dep.consecutive_failures,
                        "message": f"Dependency {source} -> {dep.target} is unhealthy"
                    })
        
        # Check for hard dependency violations
        for source, deps in self._dependencies.items():
            for dep in deps:
                if dep.dependency_type == DependencyType.HARD:
                    if dep.target not in self._all_services:
                        issues.append({
                            "type": "missing",
                            "source": source,
                            "target": dep.target,
                            "message": f"Hard dependency {source} -> {dep.target} has missing target"
                        })
        
        # Check availability requirements
        for source, deps in self._dependencies.items():
            for dep in deps:
                if dep.total_calls > 0:
                    availability = (
                        (dep.total_calls - dep.failed_calls) / dep.total_calls * 100
                    )
                    if availability < dep.required_availability:
                        issues.append({
                            "type": "availability_violation",
                            "source": source,
                            "target": dep.target,
                            "current_availability": round(availability, 2),
                            "required_availability": dep.required_availability,
                            "message": f"Availability {availability:.1f}% below required {dep.required_availability}%"
                        })
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "summary": {
                "total_dependencies": sum(len(d) for d in self._dependencies.values()),
                "healthy_dependencies": sum(
                    1 for deps in self._dependencies.values()
                    for d in deps if d.is_healthy
                ),
                "unhealthy_dependencies": sum(
                    1 for deps in self._dependencies.values()
                    for d in deps if not d.is_healthy
                ),
            }
        }
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report"""
        validation = self.validate_dependencies()
        
        return {
            "validation": validation,
            "services": list(self._all_services),
            "dependencies": {
                source: [dep.to_dict() for dep in deps]
                for source, deps in self._dependencies.items()
            },
            "dependents": self._dependents.copy(),
            "graphs": {
                "nodes": list(self._all_services),
                "edges": [
                    {"from": source, "to": dep.target}
                    for source, deps in self._dependencies.items()
                    for dep in deps
                ]
            },
            "spof_analysis": {
                svc: self.get_cascading_failure_risk(svc)
                for svc in self._all_services
                if self._dependents.get(svc)
            }
        }


class CircularDependencyError(Exception):
    """Raised when a circular dependency would be created"""
    pass
