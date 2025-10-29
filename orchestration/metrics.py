"""
Metrics module for monitoring agent performance and system health.

This module defines basic metrics for tracking:
- Latency per agent and workflow
- CPU/GPU usage
- Success rate per task
- Resource utilization
"""

import time
import psutil
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum


class MetricType(Enum):
    """Types of metrics tracked."""
    
    LATENCY = "latency"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    GPU_USAGE = "gpu_usage"
    SUCCESS_RATE = "success_rate"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"


@dataclass
class Metric:
    """Individual metric data point."""
    
    name: str
    type: MetricType
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary for serialization."""
        return {
            "name": self.name,
            "type": self.type.value,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels
        }


@dataclass
class MetricsSnapshot:
    """System metrics snapshot at a point in time."""
    
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    disk_usage_percent: float
    
    @classmethod
    def capture(cls) -> "MetricsSnapshot":
        """Capture current system metrics."""
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return cls(
            timestamp=datetime.now(),
            cpu_percent=psutil.cpu_percent(interval=0.1),
            memory_percent=memory.percent,
            memory_available_mb=memory.available / (1024 * 1024),
            disk_usage_percent=disk.percent
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_available_mb": self.memory_available_mb,
            "disk_usage_percent": self.disk_usage_percent
        }


class MetricsCollector:
    """Collector for agent and workflow metrics."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.metrics: List[Metric] = []
        self.snapshots: List[MetricsSnapshot] = []
        self._execution_starts: Dict[str, float] = {}
        self._execution_counts: Dict[str, int] = {}
        self._execution_successes: Dict[str, int] = {}
        self._execution_failures: Dict[str, int] = {}
    
    def record_metric(self, metric: Metric) -> None:
        """Record a single metric."""
        self.metrics.append(metric)
    
    def record_latency(
        self, 
        component: str, 
        latency_seconds: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Record latency metric for a component.
        
        Args:
            component: Name of the component (agent, task, etc.)
            latency_seconds: Latency in seconds
            labels: Additional labels for the metric
        """
        metric = Metric(
            name=f"{component}_latency",
            type=MetricType.LATENCY,
            value=latency_seconds,
            unit="seconds",
            labels=labels or {}
        )
        self.record_metric(metric)
    
    def start_execution(self, execution_id: str) -> None:
        """
        Mark the start of an execution.
        
        Args:
            execution_id: Unique identifier for the execution
        """
        self._execution_starts[execution_id] = time.time()
        if execution_id not in self._execution_counts:
            self._execution_counts[execution_id] = 0
            self._execution_successes[execution_id] = 0
            self._execution_failures[execution_id] = 0
        self._execution_counts[execution_id] += 1
    
    def end_execution(self, execution_id: str, success: bool = True) -> float:
        """
        Mark the end of an execution and record metrics.
        
        Args:
            execution_id: Unique identifier for the execution
            success: Whether the execution was successful
        
        Returns:
            Execution time in seconds
        """
        if execution_id not in self._execution_starts:
            raise ValueError(f"No start time found for execution: {execution_id}")
        
        latency = time.time() - self._execution_starts[execution_id]
        del self._execution_starts[execution_id]
        
        # Record latency
        self.record_latency(execution_id, latency)
        
        # Update success/failure counts
        if success:
            self._execution_successes[execution_id] += 1
        else:
            self._execution_failures[execution_id] += 1
        
        # Record success rate
        total = self._execution_counts[execution_id]
        success_rate = self._execution_successes[execution_id] / total if total > 0 else 0
        
        self.record_metric(Metric(
            name=f"{execution_id}_success_rate",
            type=MetricType.SUCCESS_RATE,
            value=success_rate * 100,
            unit="percent"
        ))
        
        return latency
    
    def capture_system_snapshot(self) -> MetricsSnapshot:
        """
        Capture current system metrics snapshot.
        
        Returns:
            MetricsSnapshot with current system state
        """
        snapshot = MetricsSnapshot.capture()
        self.snapshots.append(snapshot)
        
        # Record as metrics
        self.record_metric(Metric(
            name="system_cpu",
            type=MetricType.CPU_USAGE,
            value=snapshot.cpu_percent,
            unit="percent"
        ))
        
        self.record_metric(Metric(
            name="system_memory",
            type=MetricType.MEMORY_USAGE,
            value=snapshot.memory_percent,
            unit="percent"
        ))
        
        return snapshot
    
    def get_metrics(
        self,
        metric_type: Optional[MetricType] = None,
        since: Optional[datetime] = None
    ) -> List[Metric]:
        """
        Get collected metrics with optional filtering.
        
        Args:
            metric_type: Filter by metric type
            since: Only return metrics after this timestamp
        
        Returns:
            List of filtered metrics
        """
        filtered = self.metrics
        
        if metric_type:
            filtered = [m for m in filtered if m.type == metric_type]
        
        if since:
            filtered = [m for m in filtered if m.timestamp >= since]
        
        return filtered
    
    def get_summary(self, component: Optional[str] = None) -> Dict[str, Any]:
        """
        Get summary of metrics for a component or all components.
        
        Args:
            component: Optional component name to filter by
        
        Returns:
            Dictionary with metric summaries
        """
        summary = {
            "total_metrics": len(self.metrics),
            "total_snapshots": len(self.snapshots),
            "components": {}
        }
        
        if component:
            components = [component]
        else:
            components = list(self._execution_counts.keys())
        
        for comp in components:
            if comp in self._execution_counts:
                total = self._execution_counts[comp]
                successes = self._execution_successes[comp]
                failures = self._execution_failures[comp]
                
                summary["components"][comp] = {
                    "total_executions": total,
                    "successful": successes,
                    "failed": failures,
                    "success_rate": (successes / total * 100) if total > 0 else 0
                }
        
        # Add latest system snapshot
        if self.snapshots:
            summary["latest_system_state"] = self.snapshots[-1].to_dict()
        
        return summary
    
    def reset(self) -> None:
        """Clear all collected metrics and snapshots."""
        self.metrics.clear()
        self.snapshots.clear()
        self._execution_starts.clear()
        self._execution_counts.clear()
        self._execution_successes.clear()
        self._execution_failures.clear()


# Global metrics collector instance
_global_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return _global_collector
