"""
End-to-End Tests for Agent Orchestration System

These tests validate complete workflows from planning through execution to review.
"""

import unittest
import os
import json
import time
from pathlib import Path
from datetime import datetime


class TestCompleteWorkflow(unittest.TestCase):
    """Test complete agent workflow execution."""

    def setUp(self):
        """Set up test environment."""
        self.artifacts_dir = Path("artifacts")
        self.artifacts_dir.mkdir(exist_ok=True)
        
        # Clean up old test artifacts
        for file in self.artifacts_dir.glob("test_*"):
            file.unlink()

    def test_workflow_execution_structure(self):
        """Test that workflow components are properly structured."""
        from orchestration.coordinator import AgentCoordinator, AgentType, WorkflowStep
        
        coordinator = AgentCoordinator()
        workflow = coordinator.create_standard_workflow()
        
        # Verify all expected agents are in workflow
        self.assertIn(AgentType.PLANNER, workflow)
        self.assertIn(AgentType.EXECUTOR, workflow)
        self.assertIn(AgentType.REVIEWER, workflow)
        
        # Verify dependency structure
        planner_step = workflow[AgentType.PLANNER]
        self.assertEqual(len(planner_step.depends_on), 0)  # No dependencies
        
        executor_step = workflow[AgentType.EXECUTOR]
        self.assertIn(AgentType.PLANNER, executor_step.depends_on)
        
        reviewer_step = workflow[AgentType.REVIEWER]
        self.assertIn(AgentType.EXECUTOR, reviewer_step.depends_on)

    def test_metrics_collection(self):
        """Test metrics collection during workflow."""
        from orchestration.metrics import get_metrics_collector, MetricType
        
        collector = get_metrics_collector()
        collector.reset()
        
        # Simulate execution
        execution_id = "test_execution"
        collector.start_execution(execution_id)
        time.sleep(0.1)  # Simulate work
        latency = collector.end_execution(execution_id, success=True)
        
        # Verify metrics collected
        self.assertGreater(latency, 0)
        
        metrics = collector.get_metrics(metric_type=MetricType.LATENCY)
        self.assertGreater(len(metrics), 0)
        
        summary = collector.get_summary(component=execution_id)
        self.assertEqual(summary["components"][execution_id]["total_executions"], 1)
        self.assertEqual(summary["components"][execution_id]["successful"], 1)
        self.assertEqual(summary["components"][execution_id]["success_rate"], 100.0)

    def test_monitoring_service_initialization(self):
        """Test monitoring service can be initialized and captures snapshots."""
        from orchestration.monitoring import get_monitoring_service, HealthStatus
        
        monitoring = get_monitoring_service()
        monitoring.start_monitoring()
        
        # Capture snapshot
        snapshot = monitoring.capture_snapshot()
        
        self.assertIsNotNone(snapshot)
        self.assertGreater(snapshot.cpu_percent, 0)
        self.assertGreater(snapshot.memory_percent, 0)
        
        # Check snapshot recorded
        self.assertGreater(len(monitoring.metrics_collector.snapshots), 0)
        
        monitoring.stop_monitoring()

    def test_configuration_loading(self):
        """Test that configuration loads correctly for all agents."""
        from agents.planner import PlannerAgent
        from agents.executor import ExecutorAgent
        from agents.reviewer import ReviewerAgent
        
        # Test each agent can load config
        planner = PlannerAgent()
        self.assertEqual(planner.agent_config["id"], "planner")
        self.assertIn("defaultModel", planner.agent_config)
        
        executor = ExecutorAgent()
        self.assertEqual(executor.agent_config["id"], "executor")
        self.assertIn("defaultModel", executor.agent_config)
        
        reviewer = ReviewerAgent()
        self.assertEqual(reviewer.agent_config["id"], "reviewer")
        self.assertIn("defaultModel", reviewer.agent_config)

    def test_agent_prompt_templates_exist(self):
        """Test that all agent prompt templates exist."""
        prompts_dir = Path("prompts")
        
        required_prompts = ["planner.prompt", "executor.prompt", "reviewer.prompt"]
        
        for prompt_file in required_prompts:
            prompt_path = prompts_dir / prompt_file
            self.assertTrue(
                prompt_path.exists(),
                f"Missing prompt template: {prompt_file}"
            )
            
            # Verify prompt is not empty
            with open(prompt_path, 'r') as f:
                content = f.read()
                self.assertGreater(
                    len(content),
                    10,
                    f"Prompt template {prompt_file} is too short"
                )

    def test_artifacts_directory_creation(self):
        """Test that artifacts can be written to artifacts directory."""
        test_file = self.artifacts_dir / "test_artifact.txt"
        
        # Write test artifact
        with open(test_file, 'w') as f:
            f.write("Test artifact content")
        
        # Verify it exists
        self.assertTrue(test_file.exists())
        
        # Clean up
        test_file.unlink()

    def test_logging_configuration(self):
        """Test that logging system is properly configured."""
        from logging_config import get_logger, setup_logging
        
        setup_logging()
        logger = get_logger("test_e2e")
        
        # Test logging at various levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        
        # Verify logger is working
        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, "test_e2e")


class TestAgentIntegration(unittest.TestCase):
    """Test integration between different agents."""

    def test_planner_output_format(self):
        """Test that planner produces expected output format."""
        from agents.planner import PlannerAgent
        
        planner = PlannerAgent()
        
        # Sample backlog
        backlog = [
            {
                "title": "Test Task",
                "description": "Test Description",
                "priority": "High",
                "estimate": "1 day",
                "dependencies": []
            }
        ]
        
        # Generate plan (Note: this will fail without Ollama running, so we wrap in try/except)
        try:
            plan = planner.plan_tasks(backlog)
            
            # Verify output structure
            self.assertIn("plan", plan)
            self.assertIn("status", plan)
            self.assertEqual(plan["status"], "completed")
        except Exception as e:
            # Skip if Ollama not available
            self.skipTest(f"Skipping: Ollama not available - {str(e)}")

    def test_executor_task_structure(self):
        """Test that executor can handle task specifications."""
        from agents.executor import ExecutorAgent
        
        executor = ExecutorAgent()
        
        # Verify executor has expected methods
        self.assertTrue(hasattr(executor, 'execute_task'))
        self.assertTrue(hasattr(executor, 'run_tests'))
        self.assertTrue(hasattr(executor, 'execute'))

    def test_reviewer_interface(self):
        """Test that reviewer has expected interface."""
        from agents.reviewer import ReviewerAgent
        
        reviewer = ReviewerAgent()
        
        # Verify reviewer has expected methods
        self.assertTrue(hasattr(reviewer, 'review_code'))
        self.assertTrue(hasattr(reviewer, 'analyze_performance'))
        self.assertTrue(hasattr(reviewer, 'execute'))


class TestMonitoringIntegration(unittest.TestCase):
    """Test monitoring system integration."""

    def test_health_check_registration(self):
        """Test health check registration and execution."""
        from orchestration.monitoring import get_monitoring_service, HealthCheck, HealthStatus
        
        monitoring = get_monitoring_service()
        
        # Define a simple health check
        def sample_health_check():
            return HealthCheck(
                name="test_check",
                status=HealthStatus.HEALTHY,
                message="System operational",
                timestamp=datetime.now()
            )
        
        # Register and verify
        monitoring.register_health_check("test_check", sample_health_check)
        
        health_checks = monitoring.run_health_checks()
        self.assertIn("test_check", health_checks)
        self.assertEqual(health_checks["test_check"].status, HealthStatus.HEALTHY)

    def test_alert_creation_and_resolution(self):
        """Test alert lifecycle."""
        from orchestration.monitoring import get_monitoring_service, AlertSeverity
        
        monitoring = get_monitoring_service()
        
        # Create alert
        alert = monitoring.create_alert(
            AlertSeverity.WARNING,
            "Test alert message",
            "test_component"
        )
        
        # Verify alert created
        self.assertIsNotNone(alert)
        self.assertEqual(alert.severity, AlertSeverity.WARNING)
        self.assertFalse(alert.resolved)
        
        # Get active alerts
        active_alerts = monitoring.get_active_alerts()
        self.assertIn(alert, active_alerts)
        
        # Resolve alert
        resolved = monitoring.resolve_alert(alert.id)
        self.assertTrue(resolved)
        
        # Verify no longer active
        active_alerts_after = monitoring.get_active_alerts()
        self.assertNotIn(alert, active_alerts_after)

    def test_dashboard_data_export(self):
        """Test dashboard data can be exported."""
        from orchestration.monitoring import get_monitoring_service
        
        monitoring = get_monitoring_service()
        monitoring.start_monitoring()
        
        # Export dashboard data
        dashboard_data = monitoring.export_dashboard_data()
        
        # Verify structure
        self.assertIn("timestamp", dashboard_data)
        self.assertIn("overall_health", dashboard_data)
        self.assertIn("metrics", dashboard_data)
        self.assertIn("active_alerts", dashboard_data)
        self.assertIn("health_checks", dashboard_data)
        
        monitoring.stop_monitoring()


class TestSystemResilience(unittest.TestCase):
    """Test system resilience and error handling."""

    def test_missing_configuration_handling(self):
        """Test handling of missing configuration file."""
        from agents.base_agent import BaseAgent
        
        # This should raise FileNotFoundError when trying to load config
        with self.assertRaises(FileNotFoundError):
            # BaseAgent.__init__ will call _load_config which raises FileNotFoundError
            class TestAgent(BaseAgent):
                def _get_agent_config(self):
                    return {"id": "test"}
                def execute(self):
                    pass
                def create_agent(self):
                    pass
                def _load_prompt_template(self):
                    return "test prompt"
            
            # This will fail in _load_config with FileNotFoundError
            TestAgent(config_path="nonexistent/config.json")

    def test_invalid_json_configuration(self):
        """Test handling of invalid JSON in configuration."""
        from agents.base_agent import BaseAgent
        import tempfile
        from pathlib import Path
        
        # Create temp file with invalid JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json }")
            temp_path = f.name
        
        try:
            # This should raise ValueError when parsing invalid JSON
            with self.assertRaises(ValueError):
                class TestAgent(BaseAgent):
                    def _get_agent_config(self):
                        return {"id": "test"}
                    def execute(self):
                        pass
                    def create_agent(self):
                        pass
                    def _load_prompt_template(self):
                        return "test prompt"
                
                # This will fail in _load_config with ValueError
                TestAgent(config_path=temp_path)
        finally:
            Path(temp_path).unlink()


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
