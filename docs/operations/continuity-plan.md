# Model Failure Continuity Plan

## Purpose

This document outlines the continuity plan for handling failures of the local Ollama provider and temporary overload scenarios requiring fallback to remote model providers (GitHub Models, Azure AI Foundry).

## Provider Architecture

The system uses a **local-first with remote fallback** architecture:

1. **Primary (Default)**: Ollama (local models) - For normal operations and local development
2. **Fallback 1**: GitHub Models (remote) - Used only when Ollama is down or overloaded
3. **Fallback 2**: Azure AI Foundry (remote) - Used only when both Ollama and GitHub Models fail

This ensures cost-effective local development while maintaining availability during overload or failure scenarios.

## Automatic Failover

The system automatically attempts fallback providers when the primary fails:

```python
# From agents/base_agent.py
def _try_fallback_providers(self, model_name, failed_provider, original_error):
    fallback_providers = self.config["runtime"]["fallbackProviders"]
    
    for provider in fallback_providers:
        if provider == failed_provider:
            continue
        
        try:
            print(f"Attempting fallback: {provider}")
            return self._initialize_llm(provider, model_name)
        except Exception as e:
            print(f"Fallback {provider} failed: {e}")
            continue
    
    raise Exception(f"All providers failed")
```

## Failure Scenarios and Response

### Scenario 1: Ollama Service Down

**Detection**:
- Connection timeout to `http://localhost:11434`
- "Connection refused" errors in logs

**Automatic Response**:
1. System attempts GitHub Models fallback
2. If GitHub Models unavailable, tries Azure
3. Logs provider switch event

**Manual Response**:
```bash
# Restart Ollama service
ollama serve

# Verify Ollama is running
curl http://localhost:11434/api/tags

# Check which model is loaded
ollama list
```

**Prevention**:
- Run Ollama as system service with auto-restart
- Monitor Ollama health with automated checks
- Keep backup of Ollama models

### Scenario 2: GitHub Models Rate Limited

**Detection**:
- HTTP 429 (Too Many Requests) responses
- "Rate limit exceeded" in error messages

**Automatic Response**:
1. Exponential backoff retry (2, 4, 8 seconds)
2. Switch to Azure if retries exhausted
3. Fall back to Ollama if Azure unavailable

**Manual Response**:
```bash
# Check rate limit status
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/rate_limit

# Wait for rate limit reset or switch provider manually
```

**Prevention**:
- Monitor API usage against quotas
- Implement request caching
- Distribute load across multiple accounts (if permitted)
- Use Ollama for high-volume tasks

### Scenario 3: Azure Service Outage

**Detection**:
- Connection timeouts to Azure endpoint
- Azure service health alerts
- Authentication failures

**Automatic Response**:
1. Fall back to Ollama
2. If Ollama unavailable, try GitHub Models
3. Alert operations team

**Manual Response**:
```bash
# Check Azure service health
az account show
az account get-access-token

# Verify endpoint configuration
echo $AZURE_OPENAI_ENDPOINT
echo $AZURE_OPENAI_CHAT_DEPLOYMENT_NAME

# Switch to alternate provider
# Edit config/agents.config.json
{
  "runtime": {
    "defaultProvider": "ollama"  # Changed from "azure-ai-foundry"
  }
}
```

**Prevention**:
- Monitor Azure service health dashboard
- Maintain Azure credits/quota buffer
- Keep Ollama models synced with Azure models

### Scenario 4: Authentication Failure

**Detection**:
- HTTP 401/403 responses
- "Invalid credentials" errors
- "Token expired" messages

**Automatic Response**:
1. Log authentication error
2. Attempt next provider in fallback chain
3. Generate alert for manual intervention

**Manual Response**:
```bash
# Verify credentials
echo $GITHUB_TOKEN
echo $AZURE_OPENAI_API_KEY

# Rotate credentials
# Update .env file with new credentials
# Restart affected services
```

**Prevention**:
- Set up credential expiration alerts
- Rotate credentials proactively
- Use managed identities where possible

## Manual Provider Override

### Temporary Override (Emergency Use Only)

Use this only when local Ollama is unavailable or overloaded:

```python
from agents.planner import PlannerAgent

planner = PlannerAgent()

# Override to remote provider temporarily (for overload cases)
planner.switch_provider("github-models", "gpt-4o-mini")

# Execute with override
plan = planner.execute()
```

### Configuration Override (Not Recommended)

**Note**: The default configuration already uses Ollama (local) as primary with remote providers as fallback. This is the recommended setup for local development.

Current recommended configuration in `config/agents.config.json`:

```json
{
  "runtime": {
    "defaultProvider": "ollama",  // Local development (RECOMMENDED)
    "fallbackProviders": ["github-models", "azure-ai-foundry"]  // Remote fallbacks for overload
  }
}
```

Only change this if you need to force remote providers (not recommended for normal operation).

## Capacity Planning

### Ollama (Local)
- **Capacity**: Limited by hardware (CPU, RAM, GPU)
- **Scaling**: Upgrade hardware or add instances
- **Cost**: One-time hardware investment
- **Availability**: High (under your control)

### GitHub Models (Remote)
- **Capacity**: Free tier with rate limits
- **Scaling**: Upgrade to paid tier (when available)
- **Cost**: Currently free
- **Availability**: Depends on GitHub service health

### Azure AI Foundry (Remote)
- **Capacity**: Pay-per-token, high limits
- **Scaling**: Automatic (within quota)
- **Cost**: Variable, monitor usage
- **Availability**: 99.9% SLA

## Monitoring and Alerts

### Provider Health Checks

```python
from orchestration.monitoring import get_monitoring_service, HealthCheck, HealthStatus

def check_ollama_health():
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            return HealthCheck(
                name="ollama_provider",
                status=HealthStatus.HEALTHY,
                message="Ollama responding normally",
                timestamp=datetime.now()
            )
    except Exception as e:
        return HealthCheck(
            name="ollama_provider",
            status=HealthStatus.UNHEALTHY,
            message=f"Ollama unavailable: {e}",
            timestamp=datetime.now()
        )

monitoring = get_monitoring_service()
monitoring.register_health_check("ollama_provider", check_ollama_health)
```

### Alert Thresholds

- **Critical**: All providers unavailable
- **High**: Primary provider down, using fallback
- **Medium**: Increased error rate on any provider
- **Low**: Provider switch detected

## Testing Continuity

### Regular Drills

**Monthly**:
```bash
# Test 1: Stop Ollama and verify fallback
sudo systemctl stop ollama
invoke run-parallel
# Should automatically use GitHub Models

# Test 2: Simulate rate limit
# Temporarily reduce rate limits in config
# Verify exponential backoff works

# Test 3: Invalid credentials
# Use wrong API key
# Verify graceful degradation
```

### Automated Tests

```python
# tests/test_provider_failover.py
def test_provider_failover():
    planner = PlannerAgent()
    
    # Mock Ollama failure
    with patch('requests.get', side_effect=ConnectionError):
        # Should fall back to next provider
        plan = planner.execute()
        assert plan is not None
        assert planner.get_current_provider() != "ollama"
```

## Recovery Procedures

### After Ollama Outage

1. Restart Ollama service
2. Verify models loaded: `ollama list`
3. Run test workflow: `invoke run-parallel`
4. Monitor for stability
5. Document outage cause and duration

### After Remote Provider Outage

1. Verify provider status restored
2. Rotate credentials if needed
3. Test connectivity
4. Review error logs for impact
5. Update runbook if new issue discovered

## Communication Plan

### Internal Notification

When provider failure detected:
```
[ALERT] Model Provider Failure
Status: DEGRADED - Using fallback provider
Primary: Ollama (OFFLINE)
Current: GitHub Models (ACTIVE)
Impact: Reduced capacity, possible latency increase
Action: Investigating Ollama restart
ETA: 15 minutes
```

### User Notification

If degraded service affects users:
```
System Status: Degraded Performance
We're experiencing issues with our primary AI model provider.
The system is operating with backup providers.
You may notice slower response times.
We're working to restore full capacity.
```

## References

- Base Agent Implementation: `agents/base_agent.py`
- Monitoring Service: `orchestration/monitoring.py`
- Provider Configuration: `config/agents.config.json`
- Incident Response: `docs/operations/incident-response-playbook.md`
