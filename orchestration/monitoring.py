"""
Monitoring module for agent orchestration system.

Provides real-time monitoring capabilities including:
- Metrics collection and reporting
- Health checks
- Alert generation
- Dashboard data export
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from orchestration.metrics import get_metrics_collector, MetricType, MetricsSnapshot
from logging_config import get_logger


class HealthStatus(Enum):
    """Health check status values."""
    
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AlertSeverity(Enum):
    """Alert severity levels."""
    
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthCheck:
    """Health check result."""
    
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    details: Dict[str, Any] = None  # type: ignore
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details
        }


@dataclass
class Alert:
    """Monitoring alert."""
    
    id: str
    severity: AlertSeverity
    message: str
    component: str
    timestamp: datetime
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "severity": self.severity.value,
            "message": self.message,
            "component": self.component,
            "timestamp": self.timestamp.isoformat(),
            "resolved": self.resolved,
            "resolution_time": self.resolution_time.isoformat() if self.resolution_time else None
        }


class MonitoringService:
    """Central monitoring service for the orchestration system."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize monitoring service.
        
        Args:
            config: Optional monitoring configuration
        """
        self.logger = get_logger("monitoring")
        self.metrics_collector = get_metrics_collector()
        self.config = config or self._default_config()
        
        # Alert state
        self.alerts: List[Alert] = []
        self.alert_handlers: List[Callable[[Alert], None]] = []
        
        # Health check state
        self.health_checks: Dict[str, HealthCheck] = {}
        
        # Monitoring state
        self._monitoring_active = False
        self._last_snapshot_time = None
    
    @staticmethod
    def _default_config() -> Dict[str, Any]:
        """Get default monitoring configuration."""
        return {
            "snapshot_interval_seconds": 60,
            "metrics_retention_hours": 24,
            "alert_retention_hours": 168,  # 7 days
            "health_check_interval_seconds": 30,
            "thresholds": {
                "cpu_warning": 70.0,
                "cpu_critical": 90.0,
                "memory_warning": 80.0,
                "memory_critical": 95.0,
                "disk_warning": 85.0,
                "disk_critical": 95.0,
                "latency_warning_seconds": 60.0,
                "latency_critical_seconds": 180.0,
                "error_rate_warning": 10.0,
                "error_rate_critical": 25.0
            }
        }
    
    def start_monitoring(self) -> None:
        """Start monitoring activities."""
        self._monitoring_active = True
        self.logger.info("Monitoring service started")
        
        # Capture initial snapshot
        self.capture_snapshot()
    
    def stop_monitoring(self) -> None:
        """Stop monitoring activities."""
        self._monitoring_active = False
        self.logger.info("Monitoring service stopped")
    
    def capture_snapshot(self) -> MetricsSnapshot:
        """
        Capture system metrics snapshot and check thresholds.
        
        Returns:
            MetricsSnapshot captured
        """
        snapshot = self.metrics_collector.capture_system_snapshot()
        self._last_snapshot_time = datetime.now()
        
        # Check thresholds and generate alerts
        self._check_system_thresholds(snapshot)
        
        self.logger.debug(f"System snapshot captured: CPU={snapshot.cpu_percent}%, "
                         f"Memory={snapshot.memory_percent}%")
        
        return snapshot
    
    def _check_system_thresholds(self, snapshot: MetricsSnapshot) -> None:
        """Check system metrics against configured thresholds."""
        thresholds = self.config["thresholds"]
        
        # CPU checks
        if snapshot.cpu_percent >= thresholds["cpu_critical"]:
            self.create_alert(
                AlertSeverity.CRITICAL,
                f"CPU usage critical: {snapshot.cpu_percent:.1f}%",
                "system_cpu"
            )
        elif snapshot.cpu_percent >= thresholds["cpu_warning"]:
            self.create_alert(
                AlertSeverity.WARNING,
                f"CPU usage high: {snapshot.cpu_percent:.1f}%",
                "system_cpu"
            )
        
        # Memory checks
        if snapshot.memory_percent >= thresholds["memory_critical"]:
            self.create_alert(
                AlertSeverity.CRITICAL,
                f"Memory usage critical: {snapshot.memory_percent:.1f}%",
                "system_memory"
            )
        elif snapshot.memory_percent >= thresholds["memory_warning"]:
            self.create_alert(
                AlertSeverity.WARNING,
                f"Memory usage high: {snapshot.memory_percent:.1f}%",
                "system_memory"
            )
        
        # Disk checks
        if snapshot.disk_usage_percent >= thresholds["disk_critical"]:
            self.create_alert(
                AlertSeverity.CRITICAL,
                f"Disk usage critical: {snapshot.disk_usage_percent:.1f}%",
                "system_disk"
            )
        elif snapshot.disk_usage_percent >= thresholds["disk_warning"]:
            self.create_alert(
                AlertSeverity.WARNING,
                f"Disk usage high: {snapshot.disk_usage_percent:.1f}%",
                "system_disk"
            )
    
    def create_alert(
        self,
        severity: AlertSeverity,
        message: str,
        component: str
    ) -> Alert:
        """
        Create and record a new alert.
        
        Args:
            severity: Alert severity level
            message: Alert message
            component: Component that generated the alert
        
        Returns:
            Created Alert
        """
        alert = Alert(
            id=f"{component}_{int(time.time())}",
            severity=severity,
            message=message,
            component=component,
            timestamp=datetime.now()
        )
        
        self.alerts.append(alert)
        self.logger.warning(f"Alert created: [{severity.value}] {component}: {message}")
        
        # Notify handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                self.logger.error(f"Error in alert handler: {e}")
        
        return alert
    
    def resolve_alert(self, alert_id: str) -> bool:
        """
        Mark an alert as resolved.
        
        Args:
            alert_id: ID of the alert to resolve
        
        Returns:
            True if alert was found and resolved
        """
        for alert in self.alerts:
            if alert.id == alert_id and not alert.resolved:
                alert.resolved = True
                alert.resolution_time = datetime.now()
                self.logger.info(f"Alert resolved: {alert_id}")
                return True
        
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all unresolved alerts."""
        return [a for a in self.alerts if not a.resolved]
    
    def register_health_check(
        self,
        name: str,
        check_func: Callable[[], HealthCheck]
    ) -> None:
        """
        Register a health check function.
        
        Args:
            name: Name of the health check
            check_func: Function that performs the check and returns HealthCheck
        """
        # Execute the check immediately
        try:
            result = check_func()
            self.health_checks[name] = result
            self.logger.debug(f"Health check registered: {name}")
        except Exception as e:
            self.logger.error(f"Error in health check {name}: {e}")
            self.health_checks[name] = HealthCheck(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Health check failed: {str(e)}",
                timestamp=datetime.now()
            )
    
    def run_health_checks(self) -> Dict[str, HealthCheck]:
        """
        Run all registered health checks.
        
        Returns:
            Dictionary of health check results
        """
        # For now, return stored health checks
        # In production, this would re-run checks
        return self.health_checks.copy()
    
    def get_overall_health(self) -> HealthStatus:
        """
        Get overall system health status.
        
        Returns:
            Overall health status based on all checks
        """
        if not self.health_checks:
            return HealthStatus.UNKNOWN
        
        statuses = [check.status for check in self.health_checks.values()]
        
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        elif HealthStatus.UNKNOWN in statuses:
            return HealthStatus.UNKNOWN
        else:
            return HealthStatus.HEALTHY
    
    def export_dashboard_data(self, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Export monitoring data for dashboard display.
        
        Args:
            output_path: Optional path to save JSON export
        
        Returns:
            Dictionary with dashboard data
        """
        metrics_summary = self.metrics_collector.get_summary()
        active_alerts = self.get_active_alerts()
        
        dashboard_data = {
            "timestamp": datetime.now().isoformat(),
            "overall_health": self.get_overall_health().value,
            "metrics": metrics_summary,
            "active_alerts": [alert.to_dict() for alert in active_alerts],
            "health_checks": {
                name: check.to_dict() 
                for name, check in self.health_checks.items()
            },
            "system_snapshot": (
                self.metrics_collector.snapshots[-1].to_dict()
                if self.metrics_collector.snapshots else None
            )
        }
        
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(dashboard_data, f, indent=2)
            
            self.logger.info(f"Dashboard data exported to: {output_path}")
        
        return dashboard_data
    
    def cleanup_old_data(self) -> None:
        """Remove old metrics and alerts based on retention policy."""
        now = datetime.now()
        
        # Clean old metrics
        metrics_cutoff = now - timedelta(
            hours=self.config["metrics_retention_hours"]
        )
        initial_count = len(self.metrics_collector.metrics)
        self.metrics_collector.metrics = [
            m for m in self.metrics_collector.metrics 
            if m.timestamp >= metrics_cutoff
        ]
        removed_metrics = initial_count - len(self.metrics_collector.metrics)
        
        # Clean old alerts
        alerts_cutoff = now - timedelta(
            hours=self.config["alert_retention_hours"]
        )
        initial_alert_count = len(self.alerts)
        self.alerts = [
            a for a in self.alerts 
            if a.timestamp >= alerts_cutoff
        ]
        removed_alerts = initial_alert_count - len(self.alerts)
        
        if removed_metrics > 0 or removed_alerts > 0:
            self.logger.info(
                f"Cleanup: removed {removed_metrics} old metrics, "
                f"{removed_alerts} old alerts"
            )


# Global monitoring service instance
_global_monitoring_service: Optional[MonitoringService] = None


def get_monitoring_service(config: Optional[Dict[str, Any]] = None) -> MonitoringService:
    """
    Get the global monitoring service instance.
    
    Args:
        config: Optional configuration (only used on first call)
    
    Returns:
        Global MonitoringService instance
    """
    global _global_monitoring_service
    
    if _global_monitoring_service is None:
        _global_monitoring_service = MonitoringService(config)
    
    return _global_monitoring_service
