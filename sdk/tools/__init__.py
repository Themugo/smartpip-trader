"""
SDK Tools
=========

Developer tools: profilers, analyzers, and utilities.
"""

import time
import cProfile
import pstats
import io
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ProfileResult:
    """Profiling result"""
    function_name: str
    calls: int
    total_time: float
    per_call_time: float
    cumulative_time: float


class PerformanceProfiler:
    """Profile strategy and SDK performance"""
    
    def __init__(self):
        self._profiles: Dict[str, List[ProfileResult]] = {}
        self._profiler: Optional[cProfile.Profile] = None
    
    def start(self) -> None:
        """Start profiling"""
        self._profiler = cProfile.Profile()
        self._profiler.enable()
    
    def stop(self) -> List[ProfileResult]:
        """Stop profiling and return results"""
        if not self._profiler:
            return []
        
        self._profiler.disable()
        
        s = io.StringIO()
        ps = pstats.Stats(self._profiler, stream=s)
        ps.sort_stats("cumulative")
        ps.print_stats(20)
        
        # Parse results
        results = []
        for line in s.getvalue().split("\n"):
            if line.strip() and not line.startswith("ncalls"):
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        results.append(ProfileResult(
                            function_name=parts[2],
                            calls=int(parts[0]),
                            total_time=float(parts[2]),
                            per_call_time=float(parts[3]),
                            cumulative_time=float(parts[3])
                        ))
                    except (ValueError, IndexError):
                        pass
        
        return results
    
    def profile_function(self, func: Callable, *args, **kwargs) -> Any:
        """Profile a specific function"""
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        
        return {
            "function": func.__name__,
            "duration_ms": duration * 1000,
            "result": result
        }


class MemoryProfiler:
    """Profile memory usage"""
    
    def __init__(self):
        self._snapshots: List[Dict[str, Any]] = []
    
    def snapshot(self, label: str = "") -> Dict[str, Any]:
        """Take a memory snapshot"""
        try:
            import tracemalloc
            if not tracemalloc.is_tracing():
                tracemalloc.start()
            
            snapshot = tracemalloc.take_snapshot()
            stats = snapshot.statistics("lineno")
            
            top_stats = [
                {
                    "file": str(stat.traceback[0].filename),
                    "line": stat.traceback[0].lineno,
                    "size": stat.size,
                    "size_str": self._format_size(stat.size)
                }
                for stat in stats[:10]
            ]
            
            snapshot_data = {
                "label": label,
                "timestamp": time.time(),
                "current": tracemalloc.get_traced_memory()[0],
                "peak": tracemalloc.get_traced_memory()[1],
                "top_allocations": top_stats
            }
            
            self._snapshots.append(snapshot_data)
            return snapshot_data
        
        except ImportError:
            return {"error": "tracemalloc not available"}
    
    @staticmethod
    def _format_size(size: int) -> str:
        """Format byte size"""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"
    
    def get_snapshots(self) -> List[Dict[str, Any]]:
        """Get all snapshots"""
        return self._snapshots
    
    def compare(self) -> Dict[str, Any]:
        """Compare first and last snapshots"""
        if len(self._snapshots) < 2:
            return {"error": "Need at least 2 snapshots"}
        
        first = self._snapshots[0]
        last = self._snapshots[-1]
        
        return {
            "first": first,
            "last": last,
            "memory_growth": last["current"] - first["current"],
            "peak_memory": max(s["peak"] for s in self._snapshots)
        }


class StaticAnalyzer:
    """Analyze code statically"""
    
    @staticmethod
    def analyze_file(filepath: str) -> Dict[str, Any]:
        """Analyze a Python file"""
        import ast
        
        results = {
            "file": filepath,
            "lines": 0,
            "classes": [],
            "functions": [],
            "imports": [],
            "complexity": 0
        }
        
        try:
            with open(filepath, "r") as f:
                code = f.read()
            
            tree = ast.parse(code)
            results["lines"] = len(code.split("\n"))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    results["classes"].append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    results["functions"].append(node.name)
                    results["complexity"] += StaticAnalyzer._get_complexity(node)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            results["imports"].append(alias.name)
                    else:
                        results["imports"].append(node.module)
        
        except Exception as e:
            results["error"] = str(e)
        
        return results
    
    @staticmethod
    def _get_complexity(node) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity


class HotReloader:
    """Hot reload for strategies and plugins"""
    
    def __init__(self):
        self._watched_files: Dict[str, float] = {}
        self._callbacks: List[Callable] = []
    
    def watch(self, filepath: str) -> None:
        """Watch a file for changes"""
        try:
            mtime = os.path.getmtime(filepath)
            self._watched_files[filepath] = mtime
        except OSError:
            pass
    
    def check_changes(self) -> List[str]:
        """Check for file changes"""
        import os
        changed = []
        
        for filepath, last_mtime in list(self._watched_files.items()):
            try:
                current_mtime = os.path.getmtime(filepath)
                if current_mtime > last_mtime:
                    changed.append(filepath)
                    self._watched_files[filepath] = current_mtime
            except OSError:
                pass
        
        return changed
    
    def on_change(self, callback: Callable[[str], None]) -> None:
        """Register change callback"""
        self._callbacks.append(callback)
    
    def poll(self, interval: float = 1.0) -> None:
        """Poll for changes"""
        while True:
            changed = self.check_changes()
            for filepath in changed:
                for callback in self._callbacks:
                    try:
                        callback(filepath)
                    except Exception as e:
                        print(f"Hot reload callback error: {e}")
            time.sleep(interval)


# Import os for HotReloader
import os
