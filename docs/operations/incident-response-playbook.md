# Incident Response Playbook

## Purpose

This playbook provides step-by-step procedures for responding to incidents in the agent orchestration system. It ensures quick, consistent, and effective resolution of operational issues.

## Incident Severity Levels

### Critical (P0)
- **Definition**: Complete system outage or data loss
- **Examples**: All agents down, database corruption, security breach
- **Response Time**: Immediate (< 15 minutes)
- **Escalation**: Immediate notification to all stakeholders

### High (P1)
- **Definition**: Major functionality impaired, multiple agents failing
- **Examples**: 50%+ agent failure rate, external API outage, performance degradation
- **Response Time**: < 1 hour
- **Escalation**: Notification to team lead and on-call engineer

### Medium (P2)
- **Definition**: Partial functionality impaired, single agent issues
- **Examples**: Single agent failure, elevated error rates, slow response times
- **Response Time**: < 4 hours
- **Escalation**: Notification to on-call engineer

### Low (P3)
- **Definition**: Minor issues with workaround available
- **Examples**: Non-critical warnings, cosmetic issues, documentation gaps
- **Response Time**: Next business day
- **Escalation**: Standard ticket assignment

## Common Incident Scenarios

### 1. Agent Execution Failure

**Symptoms:**
- Agent fails to start or complete execution
- Error messages in logs
- Workflow stuck or incomplete

**Response Steps:**
1. **Identify**: Check logs in `logs/` directory for error messages
   ```bash
   tail -f logs/orchestrator.log | grep ERROR
   ```

2. **Diagnose**:
   - Verify agent configuration in `config/agents.config.json`
   - Check if model provider is accessible (Ollama, GitHub Models, Azure)
   - Review recent code changes that might affect the agent

3. **Mitigate**:
   - Restart the specific agent:
     ```bash
     invoke run-planner  # or run-executor, run-reviewer
     ```
   - Switch to fallback provider if primary is down:
     - Edit `config/agents.config.json` and change `defaultProvider`
   - Rollback recent changes if identified as cause

4. **Recover**:
   - Monitor agent execution for stability
   - Verify workflow completes successfully
   - Check metrics in monitoring dashboard

5. **Document**:
   - Record incident details, root cause, and resolution
   - Update relevant documentation if procedure gaps identified

### 2. Model Provider Unavailable

**Symptoms:**
- Connection timeouts to Ollama/GitHub Models/Azure
- Authentication errors
- API rate limit exceeded

**Response Steps:**
1. **Identify**:
   - Check provider status pages:
     - Ollama: Verify service running on `http://localhost:11434`
     - GitHub Models: Check https://github.status.com
     - Azure: Check Azure Service Health dashboard

2. **Diagnose**:
   - Test provider connectivity:
     ```bash
     # For Ollama
     curl http://localhost:11434/api/tags
     
     # For GitHub Models
     curl -H "Authorization: Bearer $GITHUB_TOKEN" https://models.github.com/health
     ```
   - Verify credentials in `.env` file
   - Check rate limits and quotas

3. **Mitigate**:
   - Start Ollama if stopped:
     ```bash
     ollama serve
     ```
   - Switch to fallback provider in configuration
   - Request quota increase if needed
   - Implement exponential backoff for retries

4. **Recover**:
   - Resume failed workflows
   - Monitor provider connectivity
   - Update provider health status

5. **Follow-up**:
   - Review SLA compliance
   - Consider implementing circuit breaker pattern
   - Update continuity plan if needed

### 3. High Resource Usage

**Symptoms:**
- CPU usage > 90%
- Memory usage > 95%
- Disk space < 10% free
- System becomes unresponsive

**Response Steps:**
1. **Identify**:
   - Check system metrics:
     ```bash
     top -n 1
     df -h
     free -h
     ```
   - Review monitoring dashboard for resource trends
   - Identify resource-intensive processes

2. **Diagnose**:
   - Determine if load is expected (e.g., parallel agent execution)
   - Check for memory leaks or runaway processes
   - Review recent configuration changes (e.g., increased concurrency)

3. **Mitigate**:
   - Reduce agent concurrency in `config/agents.config.json`:
     ```json
     "runtime": {
       "ollama": {
         "concurrency": 1
       }
     }
     ```
   - Stop non-critical workflows
   - Clean up old logs and artifacts:
     ```bash
     find logs/ -mtime +7 -delete
     find artifacts/ -mtime +7 -delete
     ```
   - Kill stuck processes if identified

4. **Recover**:
   - Resume workflows with lower concurrency
   - Monitor resource usage trends
   - Verify system stability

5. **Long-term**:
   - Review scaling configuration
   - Implement resource limits per agent
   - Consider horizontal scaling if needed

### 4. Workflow Stuck or Hanging

**Symptoms:**
- Workflow execution exceeds expected time
- No progress logs for extended period
- Agent appears running but not producing output

**Response Steps:**
1. **Identify**:
   - Check workflow status:
     ```bash
     invoke coordinator-run  # Check execution state
     ```
   - Review logs for last activity
   - Identify which agent/step is stuck

2. **Diagnose**:
   - Check if waiting for external dependency
   - Verify no deadlock between agents
   - Review timeout configurations

3. **Mitigate**:
   - Cancel stuck workflow if timeout exceeded
   - Restart workflow from last successful checkpoint
   - Increase timeout if legitimate long-running operation

4. **Recover**:
   - Monitor new execution
   - Verify completion
   - Update workflow status

5. **Prevention**:
   - Implement heartbeat monitoring
   - Add circuit breakers for external calls
   - Review and adjust timeout configurations

### 5. Security Alert

**Symptoms:**
- Exposed credentials detected
- Unauthorized access attempt
- Malicious activity detected
- Dependency vulnerability identified

**Response Steps:**
1. **Immediate Actions** (< 5 minutes):
   - Isolate affected system if breach suspected
   - Revoke exposed credentials immediately
   - Enable additional logging and monitoring

2. **Assessment**:
   - Determine scope of exposure
   - Identify affected systems and data
   - Check for signs of unauthorized access

3. **Containment**:
   - Rotate all potentially exposed credentials
   - Update `.env` with new credentials
   - Apply security patches for vulnerabilities
   - Update dependencies:
     ```bash
     pip install --upgrade -r requirements.txt
     ```

4. **Recovery**:
   - Verify system integrity
   - Restore from backup if necessary
   - Re-enable services with new credentials

5. **Post-Incident**:
   - Conduct security review
   - Update security policies
   - Implement additional controls
   - Document lessons learned

## Escalation Procedures

### When to Escalate
- Incident persists after initial mitigation attempts
- Severity level increases during investigation
- Multiple systems affected
- Potential data loss or security implications
- Estimated resolution time exceeds SLA

### Escalation Contacts
1. **Level 1**: On-call Engineer
   - Initial response and troubleshooting
   - Available 24/7

2. **Level 2**: Technical Lead
   - Complex technical issues
   - Architecture or design decisions needed

3. **Level 3**: Project Manager
   - Business impact assessment
   - Stakeholder communication
   - Resource allocation

4. **Level 4**: Security Team
   - Security incidents
   - Compliance issues
   - Data breach concerns

## Post-Incident Activities

### Immediate Post-Resolution (< 24 hours)
1. Update incident ticket with resolution details
2. Notify stakeholders of resolution
3. Monitor system for recurrence
4. Document temporary workarounds if applied

### Post-Incident Review (< 1 week)
1. Conduct root cause analysis
2. Document timeline of events
3. Identify improvement opportunities
4. Create action items for prevention
5. Update playbook based on lessons learned
6. Share findings with team

### Metrics to Track
- **MTTR** (Mean Time To Resolve): Average time to resolve incidents
- **MTTD** (Mean Time To Detect): Average time to detect incidents
- **Incident Count**: Number of incidents by severity
- **Recurrence Rate**: Percentage of incidents that recur
- **SLA Compliance**: Percentage of incidents resolved within SLA

## Communication Templates

### Initial Notification
```
[INCIDENT] [Severity: P{0-3}] {Brief Description}

Status: INVESTIGATING
Impact: {Description of user/system impact}
Started: {Timestamp}
ETA: {Estimated resolution time or "Unknown"}

Details:
{More detailed description}

Next Update: {When next update will be provided}
```

### Resolution Notification
```
[RESOLVED] [Severity: P{0-3}] {Brief Description}

Status: RESOLVED
Duration: {Total incident duration}
Root Cause: {Brief root cause}
Resolution: {What was done to resolve}

Post-Incident Review: {When/where PIR will be conducted}
```

## Useful Commands

### System Health Check
```bash
# Check system resources
top -n 1
df -h
free -h

# Check agent processes
ps aux | grep python | grep agents

# View recent logs
tail -100 logs/orchestrator.log

# Check Ollama status
curl http://localhost:11434/api/tags
```

### Recovery Commands
```bash
# Restart all agents
invoke run-parallel

# Run specific agent
invoke run-planner
invoke run-executor
invoke run-reviewer

# Run coordinator workflow
invoke coordinator-run

# Clean old data
find logs/ -mtime +7 -delete
find artifacts/ -mtime +7 -delete
```

### Diagnostic Commands
```bash
# Check Python environment
which python
python --version
pip list | grep crewai

# Verify configuration
invoke validate-config

# Run tests
invoke test
```

## Regular Maintenance

### Daily
- Review overnight logs for errors
- Check monitoring dashboard
- Verify backup completion

### Weekly
- Clean old logs and artifacts
- Review active alerts
- Update dependencies if security patches available
- Review incident metrics

### Monthly
- Conduct playbook review and update
- Review and update escalation contacts
- Test disaster recovery procedures
- Analyze incident trends

## References

- Configuration: `config/agents.config.json`
- Logs: `logs/` directory
- Monitoring: `orchestration/monitoring.py`
- Metrics: `orchestration/metrics.py`
- Tasks: `docs/tasks/03-orchestration-and-automation.md`
