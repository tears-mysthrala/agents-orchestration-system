# Scaling Configuration Guide

## Overview

This document describes how to scale the agent orchestration system to handle increased workloads, either vertically (more powerful hardware) or horizontally (more instances).

## Current Architecture

The system currently supports:
- **Vertical Scaling**: Running more powerful models, increasing concurrency
- **Horizontal Scaling**: Running multiple agent instances in parallel
- **Hybrid Scaling**: Combination of both approaches

## Vertical Scaling

### Increasing Model Capacity

Edit `config/agents.config.json` to use more capable models:

```json
{
  "models": {
    "ollama": {
      "llama3.2": {
        "context": 16384,  // Increased from 8192
        "temperature": 0.4,
        "parallel": true
      }
    }
  }
}
```

### Increasing Concurrency

Adjust the concurrency settings to run more agents simultaneously:

```json
{
  "runtime": {
    "ollama": {
      "concurrency": 4  // Increased from 2
    }
  }
}
```

**Resource Requirements**:
- Each concurrent agent requires approximately:
  - CPU: 2-4 cores
  - RAM: 4-8 GB (depending on model size)
  - GPU VRAM: 4-8 GB (if using GPU acceleration)

**Hardware Recommendations**:
| Concurrency | CPU Cores | RAM | GPU VRAM |
|------------|-----------|-----|----------|
| 1-2 | 4-8 | 16 GB | 8 GB |
| 3-4 | 8-16 | 32 GB | 12 GB |
| 5-8 | 16-32 | 64 GB | 24 GB |

## Horizontal Scaling

### Multi-Instance Deployment

For horizontal scaling, deploy multiple instances of the orchestration system:

1. **Create Instance Configuration**

Create separate config files for each instance:
- `config/agents.config.instance1.json`
- `config/agents.config.instance2.json`

2. **Assign Work Distribution**

Use different workflow IDs or task queues per instance:

```python
# Instance 1
coordinator1 = AgentCoordinator('config/agents.config.instance1.json')
coordinator1.execute_workflow(workflow_id='instance1_workflow')

# Instance 2
coordinator2 = AgentCoordinator('config/agents.config.instance2.json')
coordinator2.execute_workflow(workflow_id='instance2_workflow')
```

3. **Load Balancing**

Implement a simple round-robin or queue-based distribution:

```python
# Example load balancer
from queue import Queue

task_queue = Queue()
instances = [coordinator1, coordinator2, coordinator3]

def distribute_tasks(tasks):
    for i, task in enumerate(tasks):
        instance = instances[i % len(instances)]
        instance.execute_workflow(task)
```

### Using Task Queues

For production horizontal scaling, consider using a task queue system:

**Option 1: Redis Queue**

```bash
pip install redis rq
```

```python
from rq import Queue
from redis import Redis

redis_conn = Redis(host='localhost', port=6379)
task_queue = Queue('agent_tasks', connection=redis_conn)

# Enqueue tasks
task_queue.enqueue('orchestration.coordinator.run_standard_workflow')

# Worker processes on different machines
# $ rq worker agent_tasks
```

**Option 2: Celery**

```bash
pip install celery
```

```python
from celery import Celery

app = Celery('agent_orchestration',
             broker='redis://localhost:6379/0')

@app.task
def run_agent_workflow(workflow_id):
    return run_standard_workflow()
```

## Container-Based Scaling

### Docker Configuration

Create `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs artifacts

# Run coordinator by default
CMD ["python", "-c", "from orchestration.coordinator import run_standard_workflow; run_standard_workflow()"]
```

Create `docker-compose.yml` for multi-instance deployment:

```yaml
version: '3.8'

services:
  agent-instance-1:
    build: .
    environment:
      - INSTANCE_ID=1
      - OLLAMA_HOST=http://ollama:11434
    volumes:
      - ./logs:/app/logs
      - ./artifacts:/app/artifacts
    depends_on:
      - ollama
      - redis

  agent-instance-2:
    build: .
    environment:
      - INSTANCE_ID=2
      - OLLAMA_HOST=http://ollama:11434
    volumes:
      - ./logs:/app/logs
      - ./artifacts:/app/artifacts
    depends_on:
      - ollama
      - redis

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"

volumes:
  ollama-data:
```

### Kubernetes Deployment

Create `k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-orchestration
spec:
  replicas: 3  # Number of instances
  selector:
    matchLabels:
      app: agent-orchestration
  template:
    metadata:
      labels:
        app: agent-orchestration
    spec:
      containers:
      - name: orchestrator
        image: agent-orchestration:latest
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
        env:
        - name: OLLAMA_HOST
          value: "http://ollama-service:11434"
        volumeMounts:
        - name: config
          mountPath: /app/config
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: agent-config
```

## Monitoring Scaled Deployments

### Metrics to Track

When scaling, monitor these additional metrics:

1. **Per-Instance Metrics**:
   - Instance ID
   - Active workflows
   - CPU/Memory per instance
   - Success rate per instance

2. **Cluster Metrics**:
   - Total throughput
   - Load distribution
   - Queue depth
   - Average latency across all instances

3. **Resource Metrics**:
   - Ollama server load
   - Database connections (if applicable)
   - Network bandwidth
   - Shared storage I/O

### Monitoring Configuration

Update `orchestration/monitoring.py` for multi-instance tracking:

```python
import socket

monitoring_service = get_monitoring_service()

# Add instance identifier
instance_id = os.getenv('INSTANCE_ID', socket.gethostname())

# Tag all metrics with instance
metrics_collector.record_metric(Metric(
    name="workflow_latency",
    type=MetricType.LATENCY,
    value=latency,
    unit="seconds",
    labels={"instance": instance_id}
))
```

## Performance Optimization

### Model Selection

Choose models based on workload:

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| phi3.5 | Small | Fast | Good | High-volume, simple tasks |
| gemma2 | Medium | Medium | Very Good | General purpose |
| llama3.2 | Medium | Medium | Excellent | Complex reasoning |
| deepseek-coder | Large | Slow | Excellent | Code generation |

### Caching Strategies

Implement result caching to reduce redundant work:

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def plan_tasks(backlog_hash):
    # Cache planning results
    return planner.plan_tasks(backlog)
```

### Request Batching

Batch similar requests together:

```python
def batch_execute(tasks, batch_size=10):
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i+batch_size]
        executor.execute_batch(batch)
```

## Capacity Planning

### Calculating Required Capacity

**Formula**:
```
Required Instances = (Tasks per Hour × Avg Task Duration in Hours) / (Agent Concurrency × Efficiency Factor)
```

**Example**:
- Tasks per hour: 100
- Avg task duration: 0.1 hours (6 minutes)
- Agent concurrency: 2
- Efficiency factor: 0.8 (accounting for overhead)

```
Required Instances = (100 × 0.1) / (2 × 0.8) = 6.25 ≈ 7 instances
```

### Growth Planning

Monitor trends and plan capacity:

1. **Current State**: Baseline metrics
2. **Growth Rate**: Track month-over-month increase
3. **Headroom**: Maintain 30% spare capacity
4. **Peak Handling**: Plan for 2x average load

## Cost Optimization

### Local vs. Cloud Models

| Provider | Cost Model | Best For |
|----------|-----------|----------|
| Ollama (Local) | Hardware + Electricity | High volume, privacy |
| GitHub Models | Free (limited) | Development, testing |
| Azure OpenAI | Pay-per-token | Production, low volume |

### Resource Scheduling

Schedule resource-intensive tasks during off-peak hours:

```python
coordinator.schedule_workflow(
    cron_expression="0 2 * * *",  # 2 AM daily
    workflow_id_prefix="batch_processing"
)
```

## Troubleshooting Scaling Issues

### Common Problems

**1. Uneven Load Distribution**
- **Symptom**: Some instances overloaded, others idle
- **Solution**: Implement proper load balancing or task queue

**2. Resource Contention**
- **Symptom**: Performance degrades with more instances
- **Solution**: Increase Ollama server capacity or use multiple Ollama instances

**3. Memory Leaks**
- **Symptom**: Memory usage increases over time
- **Solution**: Implement regular restart schedule, fix memory leaks

**4. Shared State Issues**
- **Symptom**: Inconsistent results across instances
- **Solution**: Use external state store (Redis, database)

## Scaling Checklist

Before scaling to production:

- [ ] Benchmark single instance performance
- [ ] Test with 2-3 instances first
- [ ] Implement proper monitoring
- [ ] Set up centralized logging
- [ ] Configure auto-scaling rules (if cloud)
- [ ] Test failover scenarios
- [ ] Document instance-specific configurations
- [ ] Set up alerting for resource thresholds
- [ ] Implement circuit breakers
- [ ] Plan rollback procedure

## References

- Configuration: `config/agents.config.json`
- Monitoring: `orchestration/monitoring.py`
- Metrics: `orchestration/metrics.py`
- Incident Response: `docs/operations/incident-response-playbook.md`
